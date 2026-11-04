import psycopg2
from psycopg2.extras import RealDictCursor
import math
from fastapi import HTTPException

DB_CONFIG = {
    "dbname": "livraison",
    "user": "livraison",
    "password": "2003",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)



def calculer_distance_haversine(lat1, lon1, lat2, lon2):
    """Calcule la distance en kilomètres entre deux points GPS"""
    R = 6371  # Rayon de la terre en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculer_prix_commande(lat_depart, lon_depart, lat_arrivee, lon_arrivee, poids_kg) -> int:
    """
    Calcule automatiquement le prix en fonction de la distance (Haversine) et du poids.
    """
    distance_km = calculer_distance_haversine(lat_depart, lon_depart, lat_arrivee, lon_arrivee)
    
    tarif_base = 500
    prix_par_km = 150
    prix_par_kg = 100
    
    prix_calcule = tarif_base + (distance_km * prix_par_km) + (poids_kg * prix_par_kg)
    return int(prix_calcule)


def creer_commande(data , utilisateur_id: int):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Récupérer les coordonnées de la commune de départ
            cursor.execute("SELECT lat, lon FROM commune WHERE id = %s;", (data.commune_depart_id,))
            depart = cursor.fetchone()
            if not depart:
                raise HTTPException(status_code=400, detail="Commune de départ inconnue")

            # 2. Récupérer les coordonnées de la commune d'arrivée
            cursor.execute("SELECT lat, lon FROM commune WHERE id = %s;", (data.commune_arrivee_id,))
            arrivee = cursor.fetchone()
            if not arrivee:
                raise HTTPException(status_code=400, detail="Commune d'arrivée inconnue")

            # 3. Calculer automatiquement le prix avec les lat/lon récupérées de la base
            prix_automatique = calculer_prix_commande(
                depart["lat"], 
                depart["lon"], 
                arrivee["lat"], 
                arrivee["lon"], 
                data.poids_kg
            )

            # 4. Insertion en base de données avec les identifiants de communes et le prix calculé
            cursor.execute(
                """
                INSERT INTO commande (
                    utilisateur_id, 
                    commune_depart_id, 
                    commune_arrivee_id, 
                    poids_kg, 
                    prix, 
                    statut
                )
                VALUES (%s, %s, %s, %s, %s, 'creee') 
                RETURNING *;
                """,
                (
                    utilisateur_id, 
                    data.commune_depart_id, 
                    data.commune_arrivee_id, 
                    data.poids_kg, 
                    prix_automatique
                )
            )
            cmd = cursor.fetchone()
            conn.commit()
            return cmd
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la création de la commande : {str(e)}"
        )
    finally:
        conn.close()
@staticmethod
def get_commandes_en_attente():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM commande WHERE statut = 'creee';")
                return cursor.fetchall()
    finally:
        conn.close()
@staticmethod
def get_commandes_client(client_id: int):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM commande WHERE client_id = %s ORDER BY cree_le DESC;", (client_id,))
                return cursor.fetchall()
        finally:
            conn.close()

@staticmethod
def creer_evaluation(data):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO evaluation (commande_id, livreur_id, note, commentaire)
                    VALUES (%s, %s, %s, %s) RETURNING *;
                    """,
                    (data.commande_id, data.livreur_id, data.note, data.commentaire)
                )
                eval_res = cursor.fetchone()
                conn.commit()
                return eval_res
        finally:
            conn.close()


    

   