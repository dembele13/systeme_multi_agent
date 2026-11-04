import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-MOI-en-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hacher_mot_de_passe(password: str) -> str:
    return pwd_context.hash(password)


def verifier_mot_de_passe(password: str, hash_: str) -> bool:
    return pwd_context.verify(password, hash_)


def creer_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_access_token(token: str) -> dict:
    """Décode un JWT et retourne le payload. Lève une HTTPException si le token est invalide ou expiré."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decoder_access_token(token)  # réutilisation de la nouvelle fonction
        user_id = payload.get("utilisateur_id")
        role = payload.get("role")
        if user_id is None or role is None:
            raise erreur
        return {"id": int(user_id), "email": payload.get("sub"), "role": role}
    except (HTTPException, ValueError):
        raise erreur


def verifier_proprietaire(user: dict, utilisateur_id: int):
    """Un livreur ne peut agir que sur son propre compte (l'admin peut tout)."""
    if user["id"] != utilisateur_id and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Accès refusé")