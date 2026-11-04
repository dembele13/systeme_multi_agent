from alembic.util import status
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from api.models.schema import UtilisateurCreate, UtilisateurOut, Token, Role
from api.services.auth_services import AuthService
from api.core.security import creer_access_token
from api.dependencies import exiger_role, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentification"])



import logging
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

@router.post("/register", status_code=201)
def register(utilisateur: UtilisateurCreate):
    """
    Inscription d'un nouvel utilisateur (client ou livreur).
    La création d'un compte admin est interdite via cette route.
    """
    # 1. Sécurité : interdire la création d'admin
    if utilisateur.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="La création d'un compte administrateur n'est pas autorisée."
        )

    # 2. Validation supplémentaire pour les livreurs
    if utilisateur.role == "livreur":
        if not utilisateur.commune_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La commune est obligatoire pour un livreur."
            )
        if not utilisateur.vehicule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le type de véhicule est obligatoire pour un livreur."
            )

    try:
        # 3. Appel du service
        nouvel_utilisateur = AuthService.creer_utilisateur(utilisateur)
        return {
            "message": "Compte créé avec succès",
            "utilisateur": nouvel_utilisateur
        }

    except HTTPException as he:
        # On laisse passer les HTTPException déjà levées proprement par le service ou le routeur
        raise he

    except Exception as e:
        # 4. Affichage explicite de l'erreur dans les logs du serveur (avec la trace complète)
        logger.error(f"Erreur inattendue lors de l'inscription : {str(e)}", exc_info=True)
        
        # 5. Retour de l'erreur explicite dans la réponse HTTP (utile en développement)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne : {str(e)}"
        )


@router.post("/register-privilegie", response_model=UtilisateurOut, status_code=201)
async def register_privilegie(
    utilisateur: UtilisateurCreate,
    _: object = Depends(exiger_role(Role.ADMIN)),
):
    """Réservé aux admins : création de n’importe quel rôle (y compris admin)."""
    role_value = utilisateur.role.value if hasattr(utilisateur.role, "value") else utilisateur.role
    try:
        return await AuthService.creer_utilisateur(
            nom=utilisateur.nom,
            email=utilisateur.email,
            password=utilisateur.password,
            role=role_value,
            telephone=utilisateur.telephone,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    utilisateur = await AuthService.authentifier(form_data.username, form_data.password)
    if not utilisateur:
        raise HTTPException(
            status_code=401,
            detail="Email/Nom d'utilisateur ou mot de passe incorrect"
        )

    user_id = utilisateur.get("id") or utilisateur.get("_id")
    role = getattr(utilisateur.get("role"), "value", utilisateur.get("role"))      # gère le cas d'un Enum

    token = creer_access_token({
        "sub": utilisateur["email"],
        "role": role,
        "utilisateur_id": user_id,
    })

    return Token(
        access_token=token,
        token_type="bearer",
        role=role,
        utilisateur_id=user_id,
        nom=utilisateur.get("nom"),
    )


@router.get("/moi", response_model=dict)
async def moi(utilisateur=Depends(get_current_user)):
    """Informations de l’utilisateur connecté."""
    if hasattr(utilisateur, "model_dump"):
        return utilisateur.model_dump()
    return utilisateur