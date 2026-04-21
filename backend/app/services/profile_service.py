import json

from sqlalchemy.orm import Session

from app.models import UserProfile
from app.schemas import UserProfileCreate, UserProfileRead, UserProfileUpdate


def create_profile(db: Session, payload: UserProfileCreate) -> UserProfileRead:
    profile = UserProfile(
        name=payload.name,
        role=payload.role,
        language=payload.language,
        preferences_json=json.dumps(payload.preferences),
        goals_json=json.dumps(payload.goals),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_read_model(profile)


def update_profile(db: Session, profile_id: int, payload: UserProfileUpdate) -> UserProfileRead | None:
    profile = db.get(UserProfile, profile_id)
    if profile is None:
        return None

    if payload.name is not None:
        profile.name = payload.name
    if payload.role is not None:
        profile.role = payload.role
    if payload.language is not None:
        profile.language = payload.language
    if payload.preferences is not None:
        profile.preferences_json = json.dumps(payload.preferences)
    if payload.goals is not None:
        profile.goals_json = json.dumps(payload.goals)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_read_model(profile)


def get_profile(db: Session, profile_id: int) -> UserProfileRead | None:
    profile = db.get(UserProfile, profile_id)
    if profile is None:
        return None
    return _to_read_model(profile)


def _to_read_model(profile: UserProfile) -> UserProfileRead:
    return UserProfileRead(
        id=profile.id,
        name=profile.name,
        role=profile.role,
        language=profile.language,
        preferences=json.loads(profile.preferences_json or "{}"),
        goals=json.loads(profile.goals_json or "[]"),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
