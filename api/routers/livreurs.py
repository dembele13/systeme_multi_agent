from fastapi import APIRouter, Depends, HTTPException

from api.core.security import get_current_user, verifier_proprietaire
from api.models.schema import (
    LivreurDisponibiliteUpdate,
    LivreurEvaluationOut,
    LivreurProfilOut,
    EvaluationResponse,
)
from api.services.livreur_services import LivreurService

router = APIRouter(prefix="/livreurs", tags=["Livreurs"])


@router.get("/{utilisateur_id}/profil", response_model=LivreurProfilOut)
def profil_livreur(utilisateur_id: int, user: dict = Depends(get_current_user)):
    verifier_proprietaire(user, utilisateur_id)
    res = LivreurService.obtenir_profil(utilisateur_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Livreur non trouvé")
    return res


@router.patch("/{utilisateur_id}/disponibilite")
def changer_disponibilite(
    utilisateur_id: int,
    data: LivreurDisponibiliteUpdate,
    user: dict = Depends(get_current_user),
):
    verifier_proprietaire(user, utilisateur_id)
    res = LivreurService.maj_disponibilite(utilisateur_id, data.en_ligne)
    if res is None:
        raise HTTPException(status_code=404, detail="Livreur non trouvé")
    return {"success": True, "data": res}


@router.get("/{livreur_id}/evaluation", response_model=EvaluationResponse)
async def afficher_evaluation_livreur(livreur_id: int, user: dict = Depends(get_current_user)):
    evaluation = await LivreurService.obtenir_evaluation_livreur(livreur_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail=f"Livreur {livreur_id} introuvable.")
    return evaluation