from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import ApiResponse, success_response
from app.db import get_db
from app.models import Survey
from app.schemas import SurveyRead, SurveySearchRequest

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post(
    "/{user_id}/surveys:search",
    response_model=ApiResponse[list[SurveyRead]],
    summary="Search surveys authored by a user",
)
def list_user_surveys(
    user_id: int,
    payload: SurveySearchRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Survey).where(Survey.author_id == user_id).order_by(Survey.id)
    if payload.filter.status is not None:
        query = query.where(Survey.status == payload.filter.status)
    if payload.filter.category is not None:
        query = query.where(Survey.category == payload.filter.category)
    query = query.offset(payload.pagination.offset).limit(payload.pagination.limit)
    surveys = list(db.scalars(query).all())
    return success_response(
        [SurveyRead.model_validate(item) for item in surveys],
        meta={
            "pagination": {
                "limit": payload.pagination.limit,
                "offset": payload.pagination.offset,
            }
        },
    )
