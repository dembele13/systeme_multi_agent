import asyncio
import json
import math

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from api.services.db_services import DatabaseService

# --- Paramètres de sélection des livreurs ---
RAYON_MAX_KM = 5.0       # distance max livreur -> point de ramassage de la commande
NB_MAX_CANDIDATS = 5     # nombre max de livreurs sollicités par CFP


def _to_float(valeur):
    """Convertit Decimal / str / int en float, en conservant None."""
    if valeur is None:
        return None
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def distance_km(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau (haversine) entre deux points GPS, en km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def normaliser_livreur(l):
    """
    Accepte un livreur renvoyé par l'Annuaire sous forme de dictionnaire
    {"id", "capacite_kg", "lat", "lon"} ou de liste
    [utilisateur_id, vehicule, capacite_kg, lat, lon], et renvoie un dict uniforme
    avec des valeurs numériques en float.
    """
    if isinstance(l, dict):
        return {
            "id": l.get("id", l.get("utilisateur_id")),
            "capacite": _to_float(l.get("capacite_kg")),
            "lat": _to_float(l.get("lat")),
            "lon": _to_float(l.get("lon")),
        }
    return {
        "id": l[0],
        "capacite": _to_float(l[2]) if len(l) > 2 else None,
        "lat": _to_float(l[3]) if len(l) > 3 else None,
        "lon": _to_float(l[4]) if len(l) > 4 else None,
    }


def selectionner_livreurs_eligibles(livreurs, cmd):
    """
    Filtre les livreurs selon :
      1. capacité >= poids de la commande
      2. position connue et distance au point de ramassage <= RAYON_MAX_KM
    Puis trie par distance croissante et limite à NB_MAX_CANDIDATS.
    """
    poids = _to_float(cmd["poids_kg"])
    c_lat = _to_float(cmd["emplacement_lat"])
    c_lon = _to_float(cmd["emplacement_lon"])

    if poids is None or c_lat is None or c_lon is None:
        return []

    eligibles = []
    for brut in livreurs:
        l = normaliser_livreur(brut)

        if l["capacite"] is None or l["capacite"] < poids:
            continue
        if l["lat"] is None or l["lon"] is None:
            continue

        dist = distance_km(l["lat"], l["lon"], c_lat, c_lon)
        if dist > RAYON_MAX_KM:
            continue

        l["distance_km"] = dist
        eligibles.append(l)

    eligibles.sort(key=lambda x: x["distance_km"])
    return eligibles[:NB_MAX_CANDIDATS]


class DispatcherAgent(Agent):
    async def setup(self):
        print(f"[DISPATCHER] Agent Dispatcher démarré : {self.jid}")

        # Ajout du comportement de supervision et de dispatch
        b = self.ContractNetDispatcherBehaviour()
        self.add_behaviour(b)

    class ContractNetDispatcherBehaviour(CyclicBehaviour):
        async def run(self):
            # 1. Vérifier s'il y a des commandes en attente dans la base de données
            commandes = DatabaseService.get_commandes_en_attente()

            if not commandes:
                # Si aucune commande, on attend un peu avant de revérifier
                await asyncio.sleep(5)
                return

            for cmd in commandes:
                cmd_id = cmd['id']
                print(f"[DISPATCHER] Traitement de la commande #{cmd_id} (Poids: {cmd['poids_kg']}kg)")

                # 2. Demander à l'Annuaire la liste des livreurs connectés et disponibles
                annuaire_msg = Message(to="annuaire@localhost")
                annuaire_msg.set_metadata("performative", "QUERY_REF")
                annuaire_msg.thread = f"annuaire-{cmd_id}"  # permet d'identifier la réponse
                annuaire_msg.body = json.dumps({"commande_id": cmd_id})

                await self.send(annuaire_msg)

                # Attente de la réponse de l'Annuaire (on ignore les messages qui n'en sont pas)
                reply = None
                for _ in range(5):
                    msg = await self.receive(timeout=3)
                    if msg is None:
                        break
                    if str(msg.sender).split("/")[0] == "annuaire@localhost":
                        reply = msg
                        break

                if not reply:
                    print(f"[DISPATCHER] Pas de réponse de l'Annuaire pour la commande #{cmd_id}")
                    continue

                try:
                    response_data = json.loads(reply.body)
                except (json.JSONDecodeError, TypeError):
                    print(f"[DISPATCHER] Réponse invalide de l'Annuaire pour la commande #{cmd_id}")
                    continue

                livreurs = response_data.get("livreurs", [])

                # Filtrer : capacité suffisante ET proximité de la commande
                livreurs_eligibles = selectionner_livreurs_eligibles(livreurs, cmd)

                if not livreurs_eligibles:
                    print(
                        f"[DISPATCHER] Aucun livreur éligible (capacité >= {cmd['poids_kg']}kg "
                        f"et à moins de {RAYON_MAX_KM}km) pour la commande #{cmd_id}"
                    )
                    continue

                print(
                    f"[DISPATCHER] Envoi d'un CFP (Call For Proposals) à "
                    f"{len(livreurs_eligibles)} livreur(s) : "
                    + ", ".join(f"#{l['id']} ({l['distance_km']:.1f}km)" for l in livreurs_eligibles)
                )

                # 3. Envoyer un CFP (Contract Net Protocol) à chaque livreur éligible
                for liv in livreurs_eligibles:
                    # Construction du JID du livreur (convention: livreur_ID@localhost)
                    livreur_jid = f"livreur_{liv['id']}@localhost"

                    cfp_msg = Message(to=livreur_jid)
                    cfp_msg.set_metadata("performative", "CFP")
                    cfp_msg.body = json.dumps({
                        "commande_id": cmd_id,
                        "poids_kg": _to_float(cmd['poids_kg']),
                        "emplacement_lat": _to_float(cmd['emplacement_lat']),
                        "emplacement_lon": _to_float(cmd['emplacement_lon']),
                        "livr_lat": _to_float(cmd['livr_lat']),
                        "livr_lon": _to_float(cmd['livr_lon'])
                    })
                    await self.send(cfp_msg)

                # 4. Collecter les offres (PROPOSE / REFUSE) pendant une fenêtre de temps limitée
                await asyncio.sleep(3)

                # Récupérer les offres enregistrées en base pour cette commande
                offres_recues = DatabaseService.get_offres_commande(cmd_id)
                offres_valides = [o for o in offres_recues if o['cout_s'] is not None]

                if not offres_valides:
                    print(f"[DISPATCHER] Aucune offre valide reçue pour la commande #{cmd_id}")
                    continue

                # 5. Désigner le meilleur offreur (coût minimal)
                meilleure_offre = min(offres_valides, key=lambda x: float(x['cout_s']))
                gagnant_id = meilleure_offre['livreur_id']
                offre_gagnante_id = meilleure_offre['id']

                print(
                    f"[DISPATCHER] Gagnant de la commande #{cmd_id} : "
                    f"Livreur #{gagnant_id} (Coût: {meilleure_offre['cout_s']})"
                )

                # 6. Mettre à jour la base de données (attribuer la commande et retenir l'offre)
                attribue = await asyncio.to_thread(
                    DatabaseService.attribuer_commande, cmd_id, gagnant_id, offre_gagnante_id
                )
                if not attribue:
                    print(f"[DISPATCHER] Commande #{cmd_id} déjà attribuée ou annulée, abandon.")
                    continue

                # Notifier le livreur gagnant par message XMPP ACCEPT_PROPOSAL
                accept_msg = Message(to=f"livreur_{gagnant_id}@localhost")
                accept_msg.set_metadata("performative", "ACCEPT_PROPOSAL")
                accept_msg.body = json.dumps({"commande_id": cmd_id, "status": "attribuee"})
                await self.send(accept_msg)

                # Informer les livreurs non retenus (fin propre du Contract Net)
                for liv in livreurs_eligibles:
                    if liv['id'] == gagnant_id:
                        continue
                    reject_msg = Message(to=f"livreur_{liv['id']}@localhost")
                    reject_msg.set_metadata("performative", "REJECT_PROPOSAL")
                    reject_msg.body = json.dumps({"commande_id": cmd_id})
                    await self.send(reject_msg)

            # Pause avant la prochaine vérification globale
            await asyncio.sleep(5)