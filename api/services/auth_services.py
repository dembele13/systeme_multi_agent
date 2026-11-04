from typing import Optional

import psycopg2.errors
from fastapi import HTTPException

from api.core.security import hacher_mot_de_passe, verifier_mot_de_passe
from api.database import get_db_connection
from api.models.schema import UtilisateurCreate


class AuthService:

    @staticmethod
    async def obtenir_utilisateur_par_email(email: str) -> Optional[dict]:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nom, email, password, role "
                    "FROM utilisateur WHERE email = %s;",
                    (email.strip().lower(),),
                )
                return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    async def authentifier(email: str, password: str) -> Optional[dict]:
        utilisateur = await AuthService.obtenir_utilisateur_par_email(email)
        if not utilisateur :
            return None
        if not verifier_mot_de_passe(password, utilisateur["password"]):
            return None
        return utilisateur

    @staticmethod
    def creer_utilisateur(data: UtilisateurCreate) -> dict:
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
             # 1. Insertion de l'utilisateur
                cursor.execute(
                   """INSERT INTO utilisateur (nom, email, telephone, password, role)
                      VALUES (%s, %s, %s, %s, %s)
                      RETURNING id, nom, email, role;
                    """,
                    (data.nom.strip(), data.email.strip().lower(), data.telephone.strip(),
                      hacher_mot_de_passe(data.password), data.role),
                )
                utilisateur = cursor.fetchone()

               # 2. Si c'est un livreur, on récupère la commune et on l'associe
                if data.role == "livreur":
                    cursor.execute(
                      "SELECT nom, lat, lon FROM commune WHERE id = %s;", (data.commune_id,)
                    )
                    commune = cursor.fetchone()
                    if commune is None:
                       raise HTTPException(status_code=400, detail="Commune inconnue")

                  # CORRECTION ICI : on utilise utilisateur["id"] au lieu de nouvel_utilisateur_id
                    cursor.execute(
                      """
                         INSERT INTO livreur (utilisateur_id, commune_id, vehicule, capacite_kg)
                         VALUES (%s, %s, %s, %s)
                       """,
                    (
                        utilisateur["id"], 
                        data.commune_id,
                        data.vehicule,
                        data.capacite_kg, 
                    )
                )
            conn.commit()                    # Validation des deux insertions
            return utilisateur

        except psycopg2.errors.UniqueViolation:
          conn.rollback()
          raise HTTPException(status_code=409, detail="Email ou téléphone déjà utilisé")
        except Exception:
          conn.rollback()
          raise
        finally:
          conn.close()
    