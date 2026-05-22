from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import ApiResponse, empty_response, success_response
from app.db import get_db
from app.models import Answer, Survey
from app.schemas import (
    AnswerCountRead,
    PopularSurveysRequest,
    PopularSurveyRead,
    RecommendedSurveyRead,
    SurveyCreate,
    SurveyQuestion,
    SurveyRead,
    SurveyRecommendationsRequest,
    SurveySearchRequest,
    SurveyUpdate,
)

router = APIRouter(prefix="/api/v1/surveys", tags=["Surveys"])


def get_survey_or_404(db: Session, survey_id: int) -> Survey:
    survey = db.get(Survey, survey_id)
    if survey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    return survey


@router.post(
    "",
    response_model=ApiResponse[SurveyRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create survey",
)
def create_survey(payload: SurveyCreate, db: Session = Depends(get_db)) -> dict[str, object]:
    survey = Survey(**payload.model_dump(mode="json"))
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return success_response(SurveyRead.model_validate(survey))


@router.post(
    ":search",
    response_model=ApiResponse[list[SurveyRead]],
    summary="Search surveys",
)
def list_surveys(
    payload: SurveySearchRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = select(Survey).order_by(Survey.id)
    if payload.filter.category is not None:
        query = query.where(Survey.category == payload.filter.category)
    if payload.filter.status is not None:
        query = query.where(Survey.status == payload.filter.status)
    if payload.filter.author_id is not None:
        query = query.where(Survey.author_id == payload.filter.author_id)
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


@router.post(
    ":popular",
    response_model=ApiResponse[list[PopularSurveyRead]],
    summary="List popular surveys",
)
def list_popular_surveys(
    payload: PopularSurveysRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rows = db.execute(
        select(Survey.id, Survey.title, func.count(Answer.id).label("answers_count"))
        .outerjoin(Answer, Answer.survey_id == Survey.id)
        .group_by(Survey.id)
        .order_by(func.count(Answer.id).desc(), Survey.id.asc())
        .limit(payload.limit)
    ).all()
    return success_response(
        [
            PopularSurveyRead(
                survey_id=int(row.id),
                title=str(row.title),
                answers_count=int(row.answers_count),
            )
            for row in rows
        ]
    )


@router.post(
    ":recommendations",
    response_model=ApiResponse[list[RecommendedSurveyRead]],
    summary="List survey recommendations",
)
def list_recommendations(
    payload: SurveyRecommendationsRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    query = (
        select(Survey)
        .where(Survey.status == "active")
        .order_by(Survey.id.desc())
        .limit(payload.limit)
    )
    if payload.category is not None:
        query = query.where(Survey.category == payload.category)
    surveys = list(db.scalars(query).all())
    return success_response([RecommendedSurveyRead.model_validate(item) for item in surveys])


@router.get(
    "/{survey_id}",
    response_model=ApiResponse[SurveyRead],
    responses={404: {"description": "Survey not found"}},
    summary="Get survey",
)
def get_survey(survey_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    return success_response(SurveyRead.model_validate(get_survey_or_404(db, survey_id)))


@router.put(
    "/{survey_id}",
    response_model=ApiResponse[SurveyRead],
    responses={404: {"description": "Survey not found"}},
    summary="Update survey",
)
def update_survey(
    survey_id: int,
    payload: SurveyUpdate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    survey = get_survey_or_404(db, survey_id)
    for field_name, value in payload.model_dump(mode="json", exclude_unset=True).items():
        setattr(survey, field_name, value)
    db.commit()
    db.refresh(survey)
    return success_response(SurveyRead.model_validate(survey))


@router.post(
    "/{survey_id}/questions",
    response_model=ApiResponse[SurveyRead],
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Survey not found"}},
    summary="Add question to survey",
)
def add_question(
    survey_id: int,
    payload: SurveyQuestion,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    survey = get_survey_or_404(db, survey_id)
    questions = list(survey.questions)
    if any(question["name"] == payload.name for question in questions):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question with this name already exists",
        )

    survey.questions = [*questions, payload.model_dump(mode="json")]
    db.commit()
    db.refresh(survey)
    return success_response(SurveyRead.model_validate(survey))


@router.delete(
    "/{survey_id}",
    response_model=ApiResponse[None],
    responses={404: {"description": "Survey not found"}},
    summary="Delete survey",
)
def delete_survey(survey_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    survey = get_survey_or_404(db, survey_id)
    db.delete(survey)
    db.commit()
    return empty_response()


@router.get(
    "/{survey_id}/answer-stats",
    response_model=ApiResponse[AnswerCountRead],
    responses={404: {"description": "Survey not found"}},
    summary="Get survey answer statistics",
)
def get_answer_count(survey_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    get_survey_or_404(db, survey_id)
    answers_count = db.scalar(select(func.count(Answer.id)).where(Answer.survey_id == survey_id))
    return success_response(
        AnswerCountRead(survey_id=survey_id, answers_count=answers_count or 0)
    )
