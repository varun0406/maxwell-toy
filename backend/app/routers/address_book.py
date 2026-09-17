from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/address-book", tags=["address-book"])

@router.get("/", response_model=List[schemas.AddressBookOut])
def list_addresses(
    search: str = "",
    skip: int = 0,
    limit: int = 1000000,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(models.AddressBook)
    if search:
        query = query.filter(models.AddressBook.name.ilike(f"%{search}%"))
    return query.order_by(models.AddressBook.name).offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.AddressBookOut, status_code=201)
def create_address(
    payload: schemas.AddressBookCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = models.AddressBook(**payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

@router.put("/{address_id}", response_model=schemas.AddressBookOut)
def update_address(
    address_id: int,
    payload: schemas.AddressBookUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = db.query(models.AddressBook).filter(models.AddressBook.id == address_id).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
        
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(address, field, value)
        
    db.commit()
    db.refresh(address)
    return address

@router.delete("/{address_id}", status_code=204)
def delete_address(
    address_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = db.query(models.AddressBook).filter(models.AddressBook.id == address_id).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
        
    db.delete(address)
    db.commit()
