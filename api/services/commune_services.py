from api.database import get_db_connection



class CommuneService:

    @staticmethod
    def lister():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, nom, lat, lon FROM commune ORDER BY nom;")
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def obtenir(commune_id: int):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nom, lat, lon FROM commune WHERE id = %s;",
                    (commune_id,),
                )
                return cursor.fetchone()
        finally:
            conn.close()