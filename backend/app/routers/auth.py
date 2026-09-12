from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from .. import models, schemas
from ..auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    store_refresh_token, rotate_refresh_token,
    revoke_all_refresh_tokens, get_current_user,
)
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(
    payload: schemas.UserCreate, 
    request: Request, 
    db: Session = Depends(get_db)
):
    user_count = db.query(models.User).count()
    if user_count > 0:
        # Require superadmin if users already exist
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
        token = auth_header.split(" ")[1]
        try:
            from ..config import settings
            import jwt
            decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = decoded.get("sub")
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            current_user = db.query(models.User).filter(models.User.id == int(user_id)).first()
            if not current_user or not current_user.is_superuser:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superadmins can register users")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if payload.email and db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    is_first_user = (user_count == 0)
    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_superuser=is_first_user,  # First user is superuser
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenPair)
@limiter.limit("10/minute")
def login(request: Request, payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access = create_access_token(user.id)
    refresh = create_refresh_token()
    store_refresh_token(db, user.id, refresh)

    return schemas.TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(payload: schemas.RefreshRequest, db: Session = Depends(get_db)):
    # We need to decode which user this token belongs to — we store token hash in DB
    # Brute-force approach: look for matching un-revoked token across all users
    import hashlib
    token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    rt = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.token_hash == token_hash,
            models.RefreshToken.is_revoked == False,
        )
        .first()
    )
    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    from datetime import timezone
    from datetime import datetime
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Rotate
    new_refresh = rotate_refresh_token(db, payload.refresh_token, rt.user_id)
    if not new_refresh:
        raise HTTPException(status_code=401, detail="Token rotation failed")

    new_access = create_access_token(rt.user_id)
    return schemas.TokenPair(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
def logout(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_all_refresh_tokens(db, current_user.id)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
