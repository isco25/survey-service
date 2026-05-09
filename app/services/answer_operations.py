from __future__ import annotations

import hashlib
import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Answer, IdempotencyRecord, OperationStatus, Survey
from app.schemas import AnswerCreate, AnswerItem, AnswerRead, SurveyQuestion

ANSWER_OPERATION = "submit_answer"
DEFAULT_SOURCE_SERVICE = "api-gateway"


def build_business_key(survey_id: int, respondent_id: int) -> str:
    return f"survey:{survey_id}:respondent:{respondent_id}"


def build_idempotency_key(payload: AnswerCreate, idempotency_key: str | None) -> str:
    if idempotency_key:
        return idempotency_key.strip()
    return build_business_key(payload.survey_id, payload.respondent_id)


def build_request_hash(payload: AnswerCreate, source_service: str) -> str:
    normalized_payload = {
        "survey_id": payload.survey_id,
        "respondent_id": payload.respondent_id,
        "source_service": source_service,
        "answers": [answer.model_dump(mode="json") for answer in payload.answers],
    }
    serialized = json.dumps(
        normalized_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def serialize_answer(answer: Answer) -> dict[str, object]:
    return AnswerRead.model_validate(answer).model_dump(mode="json")


def build_question_map(survey: Survey) -> dict[str, SurveyQuestion]:
    return {
        question.name: question
        for question in [SurveyQuestion.model_validate(item) for item in survey.questions]
    }


def validate_answers_against_survey(survey: Survey, submitted_answers: list[AnswerItem]) -> None:
    if survey.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Answers can only be submitted to active surveys",
        )

    question_map = build_question_map(survey)
    submitted_map = {answer.name: answer.value for answer in submitted_answers}

    unknown_questions = [name for name in submitted_map if name not in question_map]
    if unknown_questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown question(s): {', '.join(sorted(unknown_questions))}",
        )

    missing_required = [
        question.name
        for question in question_map.values()
        if question.required and question.name not in submitted_map
    ]
    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required answer(s): {', '.join(sorted(missing_required))}",
        )

    for question_name, value in submitted_map.items():
        question = question_map[question_name]
        if question.type == "text":
            if not isinstance(value, str) or not value.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Question '{question_name}' expects a non-empty text value",
                )
            continue

        if question.type == "single_choice":
            if not isinstance(value, str) or value not in question.options:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Question '{question_name}' expects one of: {', '.join(question.options)}",
                )
            continue

        if not isinstance(value, list) or not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Question '{question_name}' expects a non-empty list of options",
            )
        if any(not isinstance(option, str) for option in value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Question '{question_name}' expects string options only",
            )
        if len(set(value)) != len(value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Question '{question_name}' contains duplicate options",
            )
        invalid_options = [option for option in value if option not in question.options]
        if invalid_options:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Question '{question_name}' contains invalid option(s): "
                    f"{', '.join(invalid_options)}"
                ),
            )


def get_idempotency_record(
    db: Session,
    source_service: str,
    idempotency_key: str,
) -> IdempotencyRecord | None:
    query = select(IdempotencyRecord).where(
        IdempotencyRecord.source_service == source_service,
        IdempotencyRecord.operation == ANSWER_OPERATION,
        IdempotencyRecord.idempotency_key == idempotency_key,
    )
    return db.scalar(query)


def complete_record(
    record: IdempotencyRecord,
    answer: Answer,
    response_code: int,
) -> None:
    record.status = OperationStatus.COMPLETED.value
    record.resource_id = answer.id
    record.response_code = response_code
    record.response_body = serialize_answer(answer)
    record.error_message = None


def fail_record(record: IdempotencyRecord, detail: str, response_code: int) -> None:
    record.status = OperationStatus.FAILED.value
    record.error_message = detail
    record.response_code = response_code
    record.response_body = None


def save_answer(
    db: Session,
    payload: AnswerCreate,
    idempotency_key: str | None,
    source_service: str | None,
) -> tuple[Answer | AnswerRead, int]:
    normalized_source_service = (
        source_service or DEFAULT_SOURCE_SERVICE
    ).strip() or DEFAULT_SOURCE_SERVICE
    normalized_key = build_idempotency_key(payload, idempotency_key)
    request_hash = build_request_hash(payload, normalized_source_service)
    business_key = build_business_key(payload.survey_id, payload.respondent_id)
    normalized_answers = [answer.model_dump(mode="json") for answer in payload.answers]

    record = get_idempotency_record(db, normalized_source_service, normalized_key)
    if record is not None:
        if record.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key has already been used for another request payload",
            )
        if record.status == OperationStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operation with this idempotency key is already in progress",
            )
        if record.status == OperationStatus.COMPLETED.value:
            answer = db.get(Answer, record.resource_id) if record.resource_id is not None else None
            if answer is not None:
                return answer, status.HTTP_200_OK
            if record.response_body is not None:
                return AnswerRead.model_validate(record.response_body), status.HTTP_200_OK

        record.status = OperationStatus.IN_PROGRESS.value
        record.error_message = None
        record.response_code = None
        record.response_body = None
        record.business_key = business_key
    else:
        record = IdempotencyRecord(
            source_service=normalized_source_service,
            operation=ANSWER_OPERATION,
            idempotency_key=normalized_key,
            business_key=business_key,
            request_hash=request_hash,
            status=OperationStatus.IN_PROGRESS.value,
        )
        db.add(record)
        db.flush()

    survey = db.get(Survey, payload.survey_id)
    if survey is None:
        fail_record(record, "Survey not found", status.HTTP_404_NOT_FOUND)
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")

    validate_answers_against_survey(survey, payload.answers)

    existing_answer = db.scalar(select(Answer).where(Answer.business_key == business_key))
    if existing_answer is not None:
        if existing_answer.answers == normalized_answers:
            complete_record(record, existing_answer, status.HTTP_200_OK)
            db.commit()
            return existing_answer, status.HTTP_200_OK

        fail_record(
            record,
            "Respondent has already submitted an answer for this survey",
            status.HTTP_409_CONFLICT,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Respondent has already submitted an answer for this survey",
        )

    answer = Answer(
        survey_id=payload.survey_id,
        respondent_id=payload.respondent_id,
        business_key=business_key,
        source_service=normalized_source_service,
        answers=normalized_answers,
    )
    db.add(answer)
    db.flush()

    complete_record(record, answer, status.HTTP_201_CREATED)
    db.commit()
    db.refresh(answer)
    return answer, status.HTTP_201_CREATED
