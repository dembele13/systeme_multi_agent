from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from api.core.security import decoder_access_token
from api.models.schema import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Décode le token JWT et retourne les informations de l'utilisateur connecté.
    """
    exception_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decoder_access_token(token)
    if payload is None:
        raise exception_auth

    # On récupère l'ID (peu importe la clé utilisée lors de la création du token)
    user_id = payload.get("id") or payload.get("id_utilisateur")
    
    # On récupère l'identifiant (email, username ou sub)
    identifiant = payload.get("email") or payload.get("username") or payload.get("sub")
    
    # On récupère le rôle
    role = payload.get("role")

    if user_id is None or role is None:
        raise exception_auth

    return {
        "id": int(user_id),
        "identifiant": identifiant,
        "role": role
    }


def exiger_role(*roles_autorises: Role):
    """
    Dépendance paramétrable : exiger_role(Role.livreur, Role.admin) 
    restreint l'accès aux rôles spécifiés.
    """
    async def verifier(utilisateur: dict = Depends(get_current_user)) -> dict:
        role_utilisateur = utilisateur["role"]
        
        # Convertit l'Enum en string si nécessaire pour la comparaison
        roles_valides = [r.value if isinstance(r, Role) else r for r in roles_autorises]
        
        if role_utilisateur not in roles_valides:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôles autorisés : {', '.join(roles_valides)}"
            )
        return utilisateur
        
    return verifier