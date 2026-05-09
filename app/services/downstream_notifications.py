from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.models import Survey
from app.schemas import AnswerRead, SurveyQuestion

logger = logging.getLogger(__name__)


def notify_downstream_services(answer: AnswerRead, survey: Survey) -> None:
    settings = get_settings()
    question_ids = _extract_question_ids(answer=answer, survey=survey)

    _post_internal_event(
        base_url=settings.user_service_url,
        path="/internal/events/answer-created",
        payload={
            "user_id": answer.respondent_id,
            "answer_id": answer.id,
            "question_id": 0,
            "survey_id": answer.survey_id,
        },
        idempotency_key=f"survey-answer:{answer.id}:user-xp",
    )
    _post_internal_event(
        base_url=settings.analytics_service_url,
        path="/internal/events/submission-created",
        payload={
            "user_id": answer.respondent_id,
            "submission_id": str(answer.id),
            "survey_id": answer.survey_id,
            "question_ids": question_ids,
        },
        idempotency_key=f"survey-answer:{answer.id}:analytics-submission",
    )


def _extract_question_ids(answer: AnswerRead, survey: Survey) -> list[int]:
    answered_question_names = {item.name for item in answer.answers}
    question_ids: list[int] = []

    for index, raw_question in enumerate(survey.questions, start=1):
        question = SurveyQuestion.model_validate(raw_question)
        if question.name in answered_question_names:
            question_ids.append(index)

    return question_ids


def _post_internal_event(
    *,
    base_url: str,
    path: str,
    payload: dict[str, object],
    idempotency_key: str,
) -> None:
    settings = get_settings()
    url = f"{base_url.rstrip('/')}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Token": settings.internal_api_key,
        "Idempotency-Key": idempotency_key,
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            headers=headers,
            timeout=settings.http_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Failed to notify downstream service at %s: %s", url, error)
