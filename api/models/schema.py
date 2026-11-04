
from typing import Optional, Literal
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Union
from pydantic import BaseModel, EmailStr, Field, model_validator

class Role(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"
    LIVREUR = "livreur"


# --- UTILISATEUR ---
# ---------- Auth ----------
class UtilisateurCreate(BaseModel):
    nom: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)
    telephone: str = Field(min_length=8)
    role: Literal["client", "livreur", "admin"]          # 'admin' impossible à l'inscription
    vehicule: Optional[Literal["moto", "voiture", "velo"]] = None
    capacite_kg: Optional[float] = Field(default=50.0, gt=0)
    commune_id: Optional[int] = None

    @model_validator(mode="after")
    def verifier_livreur(self):
        if self.role == "livreur":
            if not self.vehicule:
                raise ValueError("Le véhicule est obligatoire pour un livreur")
            if not self.commune_id:
                raise ValueError("La commune est obligatoire pour un livreur")
        return self
class UtilisateurOut(BaseModel):
    id: int
    nom: str
    telephone: str
    email: EmailStr
    role: str
    date_creation: Optional[datetime] = None

    class Config:
        from_attributes = True  # Permet de convertir facilement un résultat de base de données (ou SQLAlchemy) en objet Pydantic
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    utilisateur_id: int
    nom: Optional[str] = None


# ---------- Communes ----------
class CommuneOut(BaseModel):
    id: int
    nom: str
    lat: float
    lon: float



# ---------- Livreurs ----------
class LivreurDisponibiliteUpdate(BaseModel):
    en_ligne: bool


class LivreurProfilOut(BaseModel):
    utilisateur_id: int
    commune: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    en_ligne: bool


class LivreurEvaluationOut(BaseModel):
    livreur_id: int
    note_moyenne: float
    nombre_evaluations: int


# ---------- Évaluations (création, pour plus tard) ----------
class EvaluationCreate(BaseModel):
    commande_id: int
    livreur_id: int
    note: int = Field(ge=0, le=5)
    commentaire: Optional[str] = None

class EvaluationResponse(BaseModel):
    livreur_id: int
    note_moyenne: Optional[float] = None
    nombre_evaluations: int = 0


class StatutCommande(str, Enum):
    """Valeurs autorisées par le CHECK de la table commande."""
    creee = "creee"
    attribuee = "attribuee"
    livree = "livree"
    annulee = "annulee"
    echec = "echec"


class CommandeCreate(BaseModel):
    """Ce que le client envoie. Le client_id vient du token et le prix est calculé par le serveur."""
    commune_depart_id: int
    commune_arrivee_id: int
    poids_kg: float = Field(gt=0, le=1000)


class CommandeResponse(BaseModel):
    """Ce que l'API renvoie : correspond exactement aux colonnes de la table commande."""
    id: int
    client_id: int
    livreur_id: Optional[int] = None
    statut: StatutCommande

    commune_depart_id: int
    commune_arrivee_id: int

    poids_kg: float
    prix: int

    cree_le: datetime


class OffreCreate(BaseModel):
    commande_id: int
    livreur_id: int
    cout_s: Optional[float] = None  # None si refus
    motif_refus: Optional[str] = None
    retenue: bool = False  # False par défaut selon votre DEFAULT false

    class Config:
        from_attributes = True  # Permet la compatibilité avec les objets SQLAlchemy/Row si besoin