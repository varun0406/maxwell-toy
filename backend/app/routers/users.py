from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


def check_superuser(current_user: models.User):
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can perform this action"
        )


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    skip: int = 0,
    limit: int = 1000000,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_superuser(current_user)
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_superuser(current_user)
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot update your own status here")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/pin", response_model=schemas.UserOut)
def reset_user_pin(
    user_id: int,
    payload: schemas.PinReset,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_superuser(current_user)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from ..auth import hash_password
    user.hashed_password = hash_password(payload.new_pin)
    db.commit()
    db.refresh(user)
    
    # Also revoke their refresh tokens so they have to log in with new PIN
    from ..auth import revoke_all_refresh_tokens
    revoke_all_refresh_tokens(db, user_id)
    
    return user
