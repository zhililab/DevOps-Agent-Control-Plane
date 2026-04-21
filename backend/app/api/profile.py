from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserProfileCreate, UserProfileRead, UserProfileUpdate
from app.services.profile_service import create_profile, get_profile, update_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=UserProfileRead)
def create_profile_endpoint(payload: UserProfileCreate, db: Session = Depends(get_db)) -> UserProfileRead:
    return create_profile(db, payload)


@router.get("/{profile_id}", response_model=UserProfileRead)
def get_profile_endpoint(profile_id: int, db: Session = Depends(get_db)) -> UserProfileRead:
    profile = get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=UserProfileRead)
def update_profile_endpoint(
    profile_id: int, payload: UserProfileUpdate, db: Session = Depends(get_db)
) -> UserProfileRead:
    profile = update_profile(db, profile_id, payload)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
