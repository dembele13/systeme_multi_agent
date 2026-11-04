import sys
import os

# Permet d'importer les modules du projet correctement
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.services.db_services import get_db_connection
from api.core.security import hasher_mot_de_passe

def creer_compte_admin():
    # Identifiants par défaut de l'administrateur (tu pourras les modifier)
    nom = "admin"
    email = "admin@example.com"
    password = "password123"  # Changez ce mot de passe après la première connexion
    role = "admin"
    telephone = "010325885465" # Optionnel, peut être None ou un numéro valide

    print(f"🚀 Tentative de création du compte administrateur ({email})...")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Vérifier si l'administrateur existe déjà
            cursor.execute("SELECT id FROM utilisateur WHERE email = %s;", (email,))
            if cursor.fetchone():
                print("⚠️ Un utilisateur avec cet email existe déjà dans la base de données.")
                return

            # 2. Hacher le mot de passe (exactement comme le fait AuthService)
            password_hache = hasher_mot_de_passe(password)

            # 3. Insérer l'admin dans la table utilisateur
            cursor.execute(
                """
                INSERT INTO utilisateur (nom, email, password, telephone, role)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nom, email, password, telephone , role
                """,
                (nom, email, password, telephone, role)
            )
            admin_cree = cursor.fetchone()
            conn.commit()
            
            print("✅ Compte administrateur créé avec succès !")
            print(f"   ---------------------------------------")
            print(f"   ID en base : {admin_cree['id']}")
            print(f"   Nom        : {admin_cree['nom']}")
            print(f"   Email      : {admin_cree['email']}")
            print(f"   Mot de passe : {password}")
            print(f"   Rôle       : {admin_cree['role']}")
            print(f"   telephone : {admin_cree['telephone']}")
            print(f"   ---------------------------------------")
            
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'admin : {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    creer_compte_admin()