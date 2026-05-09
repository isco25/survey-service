from __future__ import annotations

from app.schemas import AnswerRead
from fastapi.testclient import TestClient


def build_survey_payload(
    *,
    category: str = "tech",
    status: str = "active",
    title: str = "Python Survey",
    author_id: int = 7,
) -> dict[str, object]:
    return {
        "author_id": author_id,
        "title": title,
        "description": "Basic questionnaire",
        "category": category,
        "status": status,
        "questions": [
            {
                "name": "experience",
                "text": "How was your experience?",
                "type": "text",
                "required": True,
            },
            {
                "name": "language",
                "text": "Pick one language",
                "type": "single_choice",
                "options": ["python", "go", "java"],
                "required": True,
            },
            {
                "name": "topics",
                "text": "Pick topics",
                "type": "multiple_choice",
                "options": ["api", "db", "testing"],
                "required": False,
            },
        ],
    }


def create_sample_survey(client: TestClient, **overrides: object) -> int:
    payload = build_survey_payload(**overrides)
    response = client.post("/surveys", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_get_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    response = client.get(f"/surveys/{survey_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == survey_id
    assert body["title"] == "Python Survey"
    assert body["category"] == "tech"
    assert body["author_id"] == 7
    assert len(body["questions"]) == 3


def test_list_surveys_can_filter_by_category(client: TestClient) -> None:
    create_sample_survey(client, category="tech")
    create_sample_survey(client, category="marketing", title="Marketing Survey")

    response = client.get("/surveys", params={"category": "TECH"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["category"] == "tech"
    assert body[0]["title"] == "Python Survey"


def test_list_user_surveys_returns_only_authored_surveys(client: TestClient) -> None:
    create_sample_survey(client, title="Author Seven Survey")
    create_sample_survey(client, title="Another Author Seven Survey")
    create_sample_survey(client, title="Author Eight Survey", author_id=8)

    response = client.get("/users/7/surveys")

    assert response.status_code == 200
    assert [survey["title"] for survey in response.json()] == [
        "Author Seven Survey",
        "Another Author Seven Survey",
    ]


def test_update_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client, status="draft")

    response = client.put(
        f"/surveys/{survey_id}",
        json={"title": "Updated Survey", "status": "closed", "category": "backend"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated Survey"
    assert body["status"] == "closed"
    assert body["category"] == "backend"


def test_delete_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    delete_response = client.delete(f"/surveys/{survey_id}")
    get_response = client.get(f"/surveys/{survey_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_get_missing_survey_returns_404(client: TestClient) -> None:
    response = client.get("/surveys/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Survey not found"


def test_create_answer_is_idempotent_for_same_request(client: TestClient) -> None:
    survey_id = create_sample_survey(client)
    payload = {
        "survey_id": survey_id,
        "respondent_id": 42,
        "answers": [
            {"name": "experience", "value": "Great"},
            {"name": "language", "value": "python"},
            {"name": "topics", "value": ["api", "testing"]},
        ],
    }
    headers = {
        "Idempotency-Key": "answer-42-1",
        "X-Source-Service": "users-service",
    }

    first_response = client.post("/answers", json=payload, headers=headers)
    second_response = client.post("/answers", json=payload, headers=headers)
    count_response = client.get(f"/surveys/{survey_id}/answers/count")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]
    assert first_response.json()["business_key"] == second_response.json()["business_key"]
    assert count_response.status_code == 200
    assert count_response.json()["answers_count"] == 1


def test_create_answer_notifies_downstream_services(
    client: TestClient,
    monkeypatch,
) -> None:
    survey_id = create_sample_survey(client)
    captured: dict[str, object] = {}

    def fake_notify(*, answer: AnswerRead, survey) -> None:
        captured["answer"] = answer
        captured["survey_id"] = survey.id

    monkeypatch.setattr("app.routers.answers.notify_downstream_services", fake_notify)

    response = client.post(
        "/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 77,
            "answers": [
                {"name": "experience", "value": "Great"},
                {"name": "language", "value": "python"},
            ],
        },
    )

    assert response.status_code == 201
    assert captured["survey_id"] == survey_id
    assert isinstance(captured["answer"], AnswerRead)
    assert captured["answer"].respondent_id == 77


def test_duplicate_business_key_is_rejected_for_different_payload(client: TestClient) -> None:
    survey_id = create_sample_survey(client)
    first_payload = {
        "survey_id": survey_id,
        "respondent_id": 99,
        "answers": [
            {"name": "experience", "value": "Great"},
            {"name": "language", "value": "python"},
        ],
    }
    second_payload = {
        "survey_id": survey_id,
        "respondent_id": 99,
        "answers": [
            {"name": "experience", "value": "Changed"},
            {"name": "language", "value": "go"},
        ],
    }

    first_response = client.post("/answers", json=first_payload)
    second_response = client.post(
        "/answers",
        json=second_payload,
        headers={"Idempotency-Key": "new-key-for-same-user"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "Respondent has already submitted an answer for this survey"
    )


def test_reused_idempotency_key_with_another_payload_is_rejected(client: TestClient) -> None:
    survey_id = create_sample_survey(client)
    headers = {"Idempotency-Key": "shared-key", "X-Source-Service": "api-gateway"}
    first_payload = {
        "survey_id": survey_id,
        "respondent_id": 11,
        "answers": [
            {"name": "experience", "value": "Great"},
            {"name": "language", "value": "python"},
        ],
    }
    second_payload = {
        "survey_id": survey_id,
        "respondent_id": 11,
        "answers": [
            {"name": "experience", "value": "Not great"},
            {"name": "language", "value": "go"},
        ],
    }

    first_response = client.post("/answers", json=first_payload, headers=headers)
    second_response = client.post("/answers", json=second_payload, headers=headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "Idempotency key has already been used for another request payload"
    )


def test_answer_validation_rejects_invalid_option(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    response = client.post(
        "/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 55,
            "answers": [
                {"name": "experience", "value": "Okay"},
                {"name": "language", "value": "rust"},
            ],
        },
    )

    assert response.status_code == 422
    assert "expects one of" in response.json()["detail"]


def test_draft_survey_rejects_answers(client: TestClient) -> None:
    survey_id = create_sample_survey(client, status="draft")

    response = client.post(
        "/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 12,
            "answers": [
                {"name": "experience", "value": "Okay"},
                {"name": "language", "value": "python"},
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Answers can only be submitted to active surveys"
