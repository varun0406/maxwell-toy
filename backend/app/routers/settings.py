from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/")
def get_settings(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    settings = db.query(models.SystemSetting).all()
    return {s.key: s.value for s in settings}

@router.post("/")
def update_settings(
    settings: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only superusers or specific roles might be allowed, but keeping it open for now
    for k, v in settings.items():
        if v is None:
            continue
        s = db.query(models.SystemSetting).filter(models.SystemSetting.key == k).first()
        if not s:
            s = models.SystemSetting(key=k, value=str(v), updated_by=current_user.id)
            db.add(s)
        else:
            s.value = str(v)
            s.updated_by = current_user.id
            s.updated_at = datetime.now()
    db.commit()
    return {"status": "success"}

def get_period_lock_date(db: Session) -> Optional[datetime]:
    lock = db.query(models.SystemSetting).filter(models.SystemSetting.key == 'period_lock_date').first()
    if lock and lock.value:
        try:
            return datetime.strptime(lock.value, '%Y-%m-%d')
        except ValueError:
            pass
    return None
