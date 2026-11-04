from typing import List
from fastapi import APIRouter
from api.models.schema import CommuneOut
from api.services.commune_services import CommuneService

router = APIRouter(prefix="/communes", tags=["Communes"])


@router.get("", response_model=List[CommuneOut])
def lister_communes():
    """Route publique : utilisée par le formulaire d'inscription."""
    return CommuneService.lister()