from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import NoteEntryCreate, NoteEntryRead, NoteEntryUpdate
from app.services.knowledge_service import (
    create_note_entry,
    delete_note_entry,
    get_note_entry,
    list_note_entries,
    update_note_entry,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=NoteEntryRead)
def create_note_entry_endpoint(
    payload: NoteEntryCreate,
    db: Session = Depends(get_db),
) -> NoteEntryRead:
    return create_note_entry(db, payload)


@router.get("", response_model=list[NoteEntryRead])
def list_note_entries_endpoint(
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[NoteEntryRead]:
    return list_note_entries(db, q=q, tag=tag)


@router.get("/{note_id}", response_model=NoteEntryRead)
def get_note_entry_endpoint(note_id: int, db: Session = Depends(get_db)) -> NoteEntryRead:
    note = get_note_entry(db, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return note


@router.put("/{note_id}", response_model=NoteEntryRead)
def update_note_entry_endpoint(
    note_id: int,
    payload: NoteEntryUpdate,
    db: Session = Depends(get_db),
) -> NoteEntryRead:
    note = update_note_entry(db, note_id, payload)
    if note is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note_entry_endpoint(note_id: int, db: Session = Depends(get_db)) -> Response:
    deleted = delete_note_entry(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return Response(status_code=204)
