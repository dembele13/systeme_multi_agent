import json

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from api.services.client_services import DatabaseService

# Si True, les livreurs ayant déjà une commande attribuée / en cours ne sont pas renvoyés.
# Adaptez les noms de table/colonnes/statuts à votre schéma si besoin.
EXCLURE_LIVREURS_OCCUPES = True
STATUTS_OCCUPES = ("attribuee", "en_cours")


def _to_float(valeur):
    """Convertit Decimal / str / int en float, en conservant None."""
    if valeur is None:
        return None
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def ligne_vers_livreur(row):
    """
    Transforme une ligne SQL (tuple/liste ou dict selon le curseur) en dictionnaire
    JSON-sérialisable avec des types numériques natifs (float).
    Ordre attendu des colonnes : utilisateur_id, vehicule, capacite_kg, lat, lon
    """
    if isinstance(row, dict):
        return {
            "id": row.get("utilisateur_id"),
            "vehicule": row.get("vehicule"),
            "capacite_kg": _to_float(row.get("capacite_kg")),
            "lat": _to_float(row.get("lat")),
            "lon": _to_float(row.get("lon")),
        }
    return {
        "id": row[0],
        "vehicule": row[1],
        "capacite_kg": _to_float(row[2]),
        "lat": _to_float(row[3]),
        "lon": _to_float(row[4]),
    }


class AnnuaireAgent(Agent):
    async def setup(self):
        print(f"[ANNUAIRE] Agent Annuaire démarré avec succès : {self.jid}")

        # Ajout du comportement principal pour écouter les requêtes
        b = self.GererAnnuaireBehaviour()
        self.add_behaviour(b)

    class GererAnnuaireBehaviour(CyclicBehaviour):
        async def run(self):
            # Attente de messages entrants (avec un timeout pour ne pas bloquer indéfiniment)
            msg = await self.receive(timeout=5)
            if not msg:
                return

            performative = msg.get_metadata("performative")
            sender = str(msg.sender)
            print(f"[ANNUAIRE] Message reçu de {sender} - Performative : {performative}")

            try:
                data = json.loads(msg.body) if msg.body else {}
            except json.JSONDecodeError:
                data = {}

            reply = msg.make_reply()

            # Cas 1 : Un livreur s'enregistre ou actualise son statut / sa position
            if performative == "REGISTER":
                utilisateur_id = data.get("utilisateur_id")
                lat = data.get("lat")
                lon = data.get("lon")
                en_ligne = data.get("en_ligne", True)

                if utilisateur_id is None or lat is None or lon is None:
                    reply.set_metadata("performative", "REFUSE")
                    reply.body = json.dumps({"error": "utilisateur_id, lat et lon sont obligatoires"})
                else:
                    # Mise à jour dans la base PostgreSQL via notre service
                    DatabaseService.maj_position_livreur(utilisateur_id, lat, lon, en_ligne)

                    reply.set_metadata("performative", "AGREE")
                    reply.body = json.dumps({"status": "success", "message": "Enregistré dans l'annuaire"})
                    print(f"[ANNUAIRE] Livreur ID {utilisateur_id} mis à jour (en_ligne={en_ligne}).")

            # Cas 2 : Le Dispatcher demande la liste des livreurs disponibles
            elif performative == "QUERY_REF":
                requete = (
                    "SELECT l.utilisateur_id, l.vehicule, l.capacite_kg, l.lat, l.lon "
                    "FROM livreur l "
                    "WHERE l.en_ligne = true "
                    "AND l.lat IS NOT NULL AND l.lon IS NOT NULL"
                )
                params = ()

                if EXCLURE_LIVREURS_OCCUPES:
                    requete += (
                        " AND NOT EXISTS ("
                        "SELECT 1 FROM commande c "
                        "WHERE c.livreur_id = l.utilisateur_id AND c.statut = ANY(%s)"
                        ")"
                    )
                    params = (list(STATUTS_OCCUPES),)

                conn = DatabaseService.get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(requete + ";", params)
                        lignes = cursor.fetchall()
                finally:
                    conn.close()

                livreurs_actifs = [ligne_vers_livreur(r) for r in lignes]

                reply.set_metadata("performative", "INFORM")
                reply.body = json.dumps({"livreurs": livreurs_actifs})
                print(f"[ANNUAIRE] Transmission de {len(livreurs_actifs)} livreur(s) actif(s) au Dispatcher.")

            else:
                reply.set_metadata("performative", "REFUSE")
                reply.body = json.dumps({"error": "Action non reconnue"})

            await self.send(reply)