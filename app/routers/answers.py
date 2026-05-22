from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.orm import Session

from app.api import ApiResponse, success_response
from app.db import get_db
from app.models import Survey
from app.schemas import AnswerCreate, AnswerRead
from app.services.answer_operations import save_answer
from app.services.downstream_notifications import notify_downstream_services

router = APIRouter(prefix="/api/v1/answers", tags=["Answers"])


@router.post(
    "",
    response_model=ApiResponse[AnswerRead],
    responses={
        404: {"description": "Survey not found"},
        409: {"description": "Duplicate or conflicting answer request"},
    },
    status_code=status.HTTP_201_CREATED,
    summary="Create answer submission",
)
def create_answer(
    payload: AnswerCreate,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    source_service: str | None = Header(default=None, alias="X-Source-Service"),
) -> dict[str, object]:
    result, status_code, xp_amount, notify_answer_names = save_answer(
        db=db,
        payload=payload,
        idempotency_key=idempotency_key,
        source_service=source_service,
    )
    response.status_code = status_code
    answer = AnswerRead.model_validate(result)
    survey = db.get(Survey, answer.survey_id)
    if survey is not None and notify_answer_names:
        notify_downstream_services(
            answer=answer,
            survey=survey,
            answer_names=notify_answer_names,
            xp_amount=xp_amount,
            duration_seconds=payload.duration_seconds,
        )
    return success_response(answer)
