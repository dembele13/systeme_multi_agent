import asyncio
import json
import math
from types import SimpleNamespace

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

from api.services.db_services import DatabaseService

# --- Paramètres ---
POSITION_PAR_DEFAUT = (5.3600, -4.0083)   # centre d'Abidjan, utilisée si le livreur n'a pas de position en base
VITESSE_MOY_KMH = 25.0                    # vitesse moyenne en ville, pour estimer le temps (cout_s en secondes)
STATUTS_OCCUPES = ["attribuee", "en_cours"]


def _to_float(valeur):
    """Convertit Decimal / str / int en float, en conservant None."""
    if valeur is None:
        return None
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None


def distance_km(lat1, lon1, lat2, lon2):
    """Distance à vol d'oiseau (haversine) en km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def temps_trajet_s(km):
    """Temps estimé en secondes pour parcourir `km` à la vitesse moyenne."""
    return km / VITESSE_MOY_KMH * 3600.0


# --- Accès base de données (synchrones, appelés via asyncio.to_thread) ---
def _lire_infos_livreur(utilisateur_id):
    conn = DatabaseService.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT lat, lon, capacite_kg FROM livreur WHERE utilisateur_id = %s;",
                (utilisateur_id,),
            )
            row = cursor.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    # Compatible curseur dict (RealDictCursor) ou tuple
    if isinstance(row, dict):
        return {"lat": _to_float(row["lat"]), "lon": _to_float(row["lon"]), "capacite": _to_float(row["capacite_kg"])}
    return {"lat": _to_float(row[0]), "lon": _to_float(row[1]), "capacite": _to_float(row[2])}


def _est_occupe(utilisateur_id):
    conn = DatabaseService.get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM commande WHERE livreur_id = %s AND statut = ANY(%s) LIMIT 1;",
                (utilisateur_id, STATUTS_OCCUPES),
            )
            return cursor.fetchone() is not None
    finally:
        conn.close()


def _offre_existe(commande_id, utilisateur_id):
    offres = DatabaseService.get_offres_commande(commande_id)
    return any(o["livreur_id"] == utilisateur_id for o in offres)


def _enregistrer_offre(commande_id, utilisateur_id, cout_s, motif_refus):
    """Enregistre l'offre (ou le refus) en base, une seule fois par livreur et par commande."""
    if _offre_existe(commande_id, utilisateur_id):
        return
    DatabaseService.creer_offre(SimpleNamespace(
        commande_id=commande_id,
        livreur_id=utilisateur_id,
        cout_s=cout_s,
        motif_refus=motif_refus,
        retenue=False,
    ))


class LivreurAgent(Agent):
    def __init__(self, jid, password, utilisateur_id: int):
        super().__init__(jid, password)
        self.utilisateur_id = utilisateur_id

    async def setup(self):
        print(f"[LIVREUR #{self.utilisateur_id}] Agent Livreur démarré : {self.jid}")

        # 1. S'enregistrer auprès de l'Annuaire à la connexion
        self.add_behaviour(self.EnregistrerLivreurBehaviour())

        # 2. Écouter les CFP (Contract Net) et les décisions du Dispatcher
        self.add_behaviour(self.ContractNetLivreurBehaviour())

    async def stop(self):
        # Le livreur disparaît de l'Annuaire quand son agent s'arrête
        try:
            await asyncio.to_thread(DatabaseService.set_livreur_hors_ligne, self.utilisateur_id)
        except Exception as e:
            print(f"[LIVREUR #{self.utilisateur_id}] Impossible de passer hors ligne : {e}")
        await super().stop()

    class EnregistrerLivreurBehaviour(OneShotBehaviour):
        async def run(self):
            # Dernière position connue en base (mise à jour par l'application du livreur)
            infos = await asyncio.to_thread(_lire_infos_livreur, self.agent.utilisateur_id)
            if infos and infos["lat"] is not None and infos["lon"] is not None:
                lat, lon = infos["lat"], infos["lon"]
            else:
                lat, lon = POSITION_PAR_DEFAUT

            # L'Annuaire se charge de la mise à jour en base (pas de double écriture)
            msg = Message(to="annuaire@localhost")
            msg.set_metadata("performative", "REGISTER")
            msg.body = json.dumps({
                "utilisateur_id": self.agent.utilisateur_id,
                "lat": lat,
                "lon": lon,
                "en_ligne": True,
            })
            await self.send(msg)
            print(f"[LIVREUR #{self.agent.utilisateur_id}] Enregistré auprès de l'Annuaire en ({lat:.4f}, {lon:.4f}).")

    class ContractNetLivreurBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            performative = msg.get_metadata("performative")
            try:
                data = json.loads(msg.body) if msg.body else {}
            except json.JSONDecodeError:
                data = {}

            uid = self.agent.utilisateur_id
            print(f"[LIVREUR #{uid}] Message reçu de {msg.sender} - Performative : {performative}")

            if performative == "CFP":
                await self._traiter_cfp(msg, data)

            elif performative == "ACCEPT_PROPOSAL":
                commande_id = data.get("commande_id")
                print(f"[LIVREUR #{uid}] Mission acceptée ! Course #{commande_id} attribuée.")
                confirmation = msg.make_reply()
                confirmation.set_metadata("performative", "INFORM")
                confirmation.body = json.dumps({"commande_id": commande_id, "livreur_id": uid, "status": "confirmee"})
                await self.send(confirmation)

            elif performative == "REJECT_PROPOSAL":
                print(f"[LIVREUR #{uid}] Offre non retenue pour la course #{data.get('commande_id')}.")

        async def _refuser(self, msg, commande_id, motif):
            uid = self.agent.utilisateur_id
            await asyncio.to_thread(_enregistrer_offre, commande_id, uid, None, motif)

            reply = msg.make_reply()
            reply.set_metadata("performative", "REFUSE")
            reply.body = json.dumps({"commande_id": commande_id, "livreur_id": uid, "motif_refus": motif})
            await self.send(reply)
            print(f"[LIVREUR #{uid}] Refus pour la commande #{commande_id} : {motif}")

        async def _traiter_cfp(self, msg, data):
            uid = self.agent.utilisateur_id
            commande_id = data.get("commande_id")

            pick_lat = _to_float(data.get("emplacement_lat"))
            pick_lon = _to_float(data.get("emplacement_lon"))
            liv_lat = _to_float(data.get("livr_lat"))
            liv_lon = _to_float(data.get("livr_lon"))
            poids = _to_float(data.get("poids_kg"))

            if commande_id is None or pick_lat is None or pick_lon is None:
                print(f"[LIVREUR #{uid}] CFP invalide ignoré : {data}")
                return

            # État actuel du livreur (position et capacité en base)
            infos = await asyncio.to_thread(_lire_infos_livreur, uid)
            if not infos or infos["lat"] is None or infos["lon"] is None:
                await self._refuser(msg, commande_id, "position_inconnue")
                return

            # Refus si la capacité est insuffisante
            if poids is not None and infos["capacite"] is not None and infos["capacite"] < poids:
                await self._refuser(msg, commande_id, "capacite_insuffisante")
                return

            # Refus si déjà en course
            if await asyncio.to_thread(_est_occupe, uid):
                await self._refuser(msg, commande_id, "deja_en_course")
                return

            # Coût = temps estimé (secondes) : trajet jusqu'au ramassage + trajet de livraison
            km = distance_km(infos["lat"], infos["lon"], pick_lat, pick_lon)
            if liv_lat is not None and liv_lon is not None:
                km += distance_km(pick_lat, pick_lon, liv_lat, liv_lon)
            cout_s = round(temps_trajet_s(km), 1)

            # Enregistrer l'offre en base pour que le Dispatcher puisse l'analyser
            await asyncio.to_thread(_enregistrer_offre, commande_id, uid, cout_s, None)

            reply = msg.make_reply()
            reply.set_metadata("performative", "PROPOSE")
            reply.body = json.dumps({
                "commande_id": commande_id,
                "livreur_id": uid,
                "cout_s": cout_s,
                "distance_km": round(km, 2),
            })
            await self.send(reply)
            print(f"[LIVREUR #{uid}] Offre pour la commande #{commande_id} : {cout_s}s ({km:.1f} km)")