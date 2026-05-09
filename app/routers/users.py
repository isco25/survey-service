from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Survey
from app.schemas import SurveyRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/{user_id}/surveys",
    response_model=list[SurveyRead],
    summary="List surveys authored by a user",
)
def list_user_surveys(user_id: int, db: Session = Depends(get_db)) -> list[Survey]:
    query = select(Survey).where(Survey.author_id == user_id).order_by(Survey.id)
    return list(db.scalars(query).all())
