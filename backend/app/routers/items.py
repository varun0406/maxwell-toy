from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=List[schemas.ItemOut])
def list_items(
    search: str = "",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.ItemMaster)
    if search:
        query = query.filter(models.ItemMaster.item_name.like(f"%{search}%"))
    return query.order_by(models.ItemMaster.item_name).all()


@router.post("/upsert", response_model=schemas.ItemOut, status_code=status.HTTP_200_OK)
def upsert_item(
    payload: schemas.ItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find existing by name (case-insensitive)
    existing = (
        db.query(models.ItemMaster)
        .filter(func.lower(models.ItemMaster.item_name) == func.lower(payload.item_name))
        .first()
    )

    if existing:
        if payload.default_rate is not None and payload.default_rate > 0:
            existing.default_rate = payload.default_rate
        db.commit()
        db.refresh(existing)
        return existing

    # Create new
    new_item = models.ItemMaster(
        item_name=payload.item_name,
        default_rate=payload.default_rate or 0,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(models.ItemMaster).filter(models.ItemMaster.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return None
