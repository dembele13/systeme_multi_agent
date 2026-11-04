from fastapi import APIRouter, HTTPException, Depends
from api.dependencies import get_current_user
from api.models.schema import CommandeCreate
from api.services import client_services 


router = APIRouter(prefix="/commandes", tags=["Commandes"])

@router.post("/", response_model=dict, status_code=201)
def nouvelle_commande(cmd: CommandeCreate):
    # Vérification du rôle
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Réservé aux clients")
    
    # Sécurité : Forcer le utilisateur_id à correspondre à l'utilisateur connecté
    cmd.utilisateur_id = user["id"]
    
    try:
        resultat = client_services.creer_commande(cmd)
        return {"success": True, "data": resultat}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/en-attente", response_model=dict)
def lister_commandes_en_attente():
    # Optionnel : Sécuriser aussi cette route si elle est réservée aux livreurs/admins
    try:
        commandes = client_services.get_commandes_en_attente()
        return {"success": True, "data": commandes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))