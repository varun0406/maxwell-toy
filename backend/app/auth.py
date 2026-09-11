from datetime import datetime, timezone, timedelta
from typing import Optional
import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int) -> str:
    expire = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token() -> str:
    """Returns a cryptographically random opaque token string."""
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    """SHA-256 hash for storing refresh tokens in DB without keeping plaintext."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Refresh token DB management
# ---------------------------------------------------------------------------

def store_refresh_token(db: Session, user_id: int, token: str) -> models.RefreshToken:
    rt = models.RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def rotate_refresh_token(
    db: Session, old_token: str, user_id: int
) -> Optional[str]:
    """Validates old token, revokes it, returns new token. Returns None if invalid."""
    token_hash = _hash_token(old_token)
    rt = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.user_id == user_id,
            models.RefreshToken.is_revoked == False,
        )
        .first()
    )
    if not rt:
        return None
    if rt.expires_at.replace(tzinfo=timezone.utc) < _utcnow():
        return None

    # Revoke old
    rt.is_revoked = True
    db.commit()

    # Issue new
    new_token = create_refresh_token()
    store_refresh_token(db, user_id, new_token)
    return new_token


def revoke_all_refresh_tokens(db: Session, user_id: int):
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user_id
    ).update({"is_revoked": True})
    db.commit()


# ---------------------------------------------------------------------------
# Dependency: get current user from Bearer token
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
