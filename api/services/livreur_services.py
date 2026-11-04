from api.database import get_db_connection


class LivreurService:

    @staticmethod
    def maj_disponibilite(utilisateur_id: int, en_ligne: bool):
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE livreur SET en_ligne = %s WHERE utilisateur_id = %s "
                    "RETURNING utilisateur_id, en_ligne;",
                    (en_ligne, utilisateur_id),
                )
                res = cursor.fetchone()
            conn.commit()
            return res
        finally:
            conn.close()

    @staticmethod
    def obtenir_profil(utilisateur_id: int):
          conn = get_db_connection()
          try:
                with conn.cursor() as cursor:  # DictCursor déjà configuré
                    cursor.execute(
                        """SELECT l.utilisateur_id, l.en_ligne,
                           c.lat, c.lon,
                            c.nom AS commune
                          FROM livreur l
                          LEFT JOIN commune c ON c.id = l.commune_id
                          WHERE l.utilisateur_id = %s;
                        """,
                        (utilisateur_id,),
                   )
                    row = cursor.fetchone()

                    if not row:
                      return None

                    return {
                       "utilisateur_id": row["utilisateur_id"],
                       "en_ligne": bool(row["en_ligne"]),
                       "lat": float(row["lat"]),
                       "lon": float(row["lon"]) ,
                       "commune": row["commune"]
                }
          finally:
           conn.close()
    
    @staticmethod
    async def obtenir_evaluation_livreur(livreur_id: int):
       conn = get_db_connection()
       try:
          with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 
                       livreur_id,
                       ROUND(AVG(note)::numeric, 2) AS note_moyenne,
                       COUNT(*) AS nombre_evaluations
                    FROM evaluation
                    WHERE livreur_id = %s
                    GROUP BY livreur_id;
                    """,
                   (livreur_id,),
                )
                res = cursor.fetchone()

                if not res:
                # Aucune évaluation pour ce livreur
                  return {
                    "livreur_id": livreur_id,
                    "note_moyenne": None,
                    "nombre_evaluations": 0
                }

                return {
                   "livreur_id": res["livreur_id"],
                   "note_moyenne": float(res["note_moyenne"]),
                   "nombre_evaluations": res["nombre_evaluations"]
            }
       finally:
          conn.close()