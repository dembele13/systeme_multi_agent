from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_current_user
from api.models.schema import EvaluationCreate
from api.services import client_services
from api.core.security import verifier_proprietaire

router = APIRouter(prefix="/clients", tags=["Espace Client"])

@router.get("/{client_id}/commandes", response_model=dict)
def historique_commandes_client(client_id: int, user: dict = Depends(get_current_user)):
    # Vérifie que l'utilisateur connecté accède bien à ses propres commandes
    verifier_proprietaire(user, client_id)
    try:
        commandes = client_services.get_commandes_client(client_id)
        return {"success": True, "data": commandes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluations", response_model=dict, status_code=201)
def evaluer_livraison(evaluation: EvaluationCreate, user: dict = Depends(get_current_user)):
    """Permet au client de noter et commenter la prestation du livreur après la course."""
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Réservé aux clients")
        
    try:
        eval_creee = client_services.creer_evaluation(evaluation)
        return {"success": True, "data": eval_creee}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))