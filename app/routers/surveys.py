from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Answer, Survey
from app.schemas import (
    AnswerCountRead,
    SurveyCreate,
    SurveyRead,
    SurveyUpdate,
    normalize_category,
)

router = APIRouter(prefix="/surveys", tags=["Опросы"])


def get_survey_or_404(db: Session, survey_id: int) -> Survey:
    survey = db.get(Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    return survey


@router.post(
    "",
    response_model=SurveyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать опрос",
    description="Создает новый опрос с категорией и вопросами.",
)
def create_survey(payload: SurveyCreate, db: Session = Depends(get_db)) -> Survey:
    survey = Survey(**payload.model_dump(mode="json"))
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


@router.get(
    "",
    response_model=list[SurveyRead],
    summary="Список опросов",
    description="Возвращает список всех опросов или фильтрует их по категории.",
)
def list_surveys(
    category: str | None = Query(default=None, description="Фильтр по категории"),
    db: Session = Depends(get_db),
) -> list[Survey]:
    query = select(Survey).order_by(Survey.id)
    if category is not None:
        query = query.where(Survey.category == normalize_category(category))
    return list(db.scalars(query).all())


@router.get(
    "/{survey_id}",
    response_model=SurveyRead,
    responses={404: {"description": "Survey not found"}},
    summary="Получить опрос",
    description="Возвращает опрос по его идентификатору.",
)
def get_survey(survey_id: int, db: Session = Depends(get_db)) -> Survey:
    return get_survey_or_404(db, survey_id)


@router.put(
    "/{survey_id}",
    response_model=SurveyRead,
    responses={404: {"description": "Survey not found"}},
    summary="Обновить опрос",
    description="Обновляет поля опроса.",
)
def update_survey(
    survey_id: int,
    payload: SurveyUpdate,
    db: Session = Depends(get_db),
) -> Survey:
    survey = get_survey_or_404(db, survey_id)
    for field_name, value in payload.model_dump(mode="json", exclude_unset=True).items():
        setattr(survey, field_name, value)
    db.commit()
    db.refresh(survey)
    return survey


@router.delete(
    "/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Survey not found"}},
    summary="Удалить опрос",
    description="Удаляет опрос по идентификатору.",
)
def delete_survey(survey_id: int, db: Session = Depends(get_db)) -> Response:
    survey = get_survey_or_404(db, survey_id)
    db.delete(survey)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{survey_id}/answers/count",
    response_model=AnswerCountRead,
    responses={404: {"description": "Survey not found"}},
    summary="Количество ответов",
    description="Возвращает количество ответов для опроса.",
)
def get_answer_count(survey_id: int, db: Session = Depends(get_db)) -> AnswerCountRead:
    get_survey_or_404(db, survey_id)
    answers_count = db.scalar(select(func.count(Answer.id)).where(Answer.survey_id == survey_id))
    return AnswerCountRead(survey_id=survey_id, answers_count=answers_count or 0)
