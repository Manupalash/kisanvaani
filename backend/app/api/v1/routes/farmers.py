from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Farmer
from app.schemas.resources import FarmerCreate, FarmerRead, FarmerUpdate

router = APIRouter()


@router.post("/", response_model=FarmerRead, status_code=status.HTTP_201_CREATED)
def create_farmer(data: FarmerCreate, db: Session = Depends(get_db)):
    farmer = Farmer(**data.model_dump())
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.get("/", response_model=list[FarmerRead])
def list_farmers(db: Session = Depends(get_db)):
    return db.scalars(select(Farmer).order_by(Farmer.id)).all()


@router.get("/{farmer_id}", response_model=FarmerRead)
def get_farmer(farmer_id: int, db: Session = Depends(get_db)):
    farmer = db.get(Farmer, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer


@router.patch("/{farmer_id}", response_model=FarmerRead)
def update_farmer(farmer_id: int, data: FarmerUpdate, db: Session = Depends(get_db)):
    farmer = db.get(Farmer, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(farmer, key, value)
    db.commit()
    db.refresh(farmer)
    return farmer


@router.delete("/{farmer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farmer(farmer_id: int, db: Session = Depends(get_db)):
    farmer = db.get(Farmer, farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    db.delete(farmer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
