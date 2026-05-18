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

    question_index_map = {}
    for idx, raw_q in enumerate(survey.questions, start=1):
        q = SurveyQuestion.model_validate(raw_q)
        question_index_map[q.name] = idx

    for answer_item in answer.answers:
        question_id = question_index_map.get(answer_item.name)
        if question_id is None:
            logger.warning(f"Unknown question {answer_item.name} in answer {answer.id}")
            continue

        payload = {
            "user_id": answer.respondent_id,
            "answer_id": answer.id, 
            "question_id": question_id,
            "survey_id": answer.survey_id,
        }
        idem_key = f"survey-answer:{answer.id}:{answer_item.name}"

        # user‑service
        _post_internal_event(
            base_url=settings.user_service_url,
            path="/internal/events/answer-created",
            payload=payload,
            idempotency_key=f"{idem_key}:user-xp",
        )
        # analytics‑service
        _post_internal_event(
            base_url=settings.analytics_service_url,
            path="/internal/events/answer-created",
            payload={
                "user_id": answer.respondent_id,
                "answer_id": str(answer.id),
                "question_id": question_id,
                "survey_id": answer.survey_id,
            },
            idempotency_key=f"survey-answer:{answer.id}:{answer_item.name}:analytics-answer",
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
