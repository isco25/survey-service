from __future__ import annotations

from fastapi.testclient import TestClient

from app.schemas import AnswerRead

API_PREFIX = "/api/v1"


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
    response = client.post(f"{API_PREFIX}/surveys", json=payload)
    assert response.status_code == 201
    return response.json()["data"]["id"]


def unwrap(response):
    return response.json()["data"]


def error_message(response) -> str:
    return response.json()["errors"][0]["message"]


def test_create_and_get_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    response = client.get(f"{API_PREFIX}/surveys/{survey_id}")

    assert response.status_code == 200
    body = unwrap(response)
    assert body["id"] == survey_id
    assert body["title"] == "Python Survey"
    assert body["category"] == "tech"
    assert body["author_id"] == 7
    assert len(body["questions"]) == 3


def test_create_survey_with_image_url(client: TestClient) -> None:
    payload = build_survey_payload()
    payload["image_url"] = "https://example.com/survey.png"

    response = client.post(f"{API_PREFIX}/surveys", json=payload)

    assert response.status_code == 201
    assert unwrap(response)["image_url"] == "https://example.com/survey.png"


def test_list_surveys_can_filter_by_category(client: TestClient) -> None:
    create_sample_survey(client, category="tech")
    create_sample_survey(client, category="marketing", title="Marketing Survey")

    response = client.post(f"{API_PREFIX}/surveys:search", json={"filter": {"category": "TECH"}})

    assert response.status_code == 200
    body = unwrap(response)
    assert len(body) == 1
    assert body[0]["category"] == "tech"
    assert body[0]["title"] == "Python Survey"


def test_list_user_surveys_returns_only_authored_surveys(client: TestClient) -> None:
    create_sample_survey(client, title="Author Seven Survey")
    create_sample_survey(client, title="Another Author Seven Survey")
    create_sample_survey(client, title="Author Eight Survey", author_id=8)

    response = client.post(f"{API_PREFIX}/users/7/surveys:search", json={})

    assert response.status_code == 200
    assert [survey["title"] for survey in unwrap(response)] == [
        "Author Seven Survey",
        "Another Author Seven Survey",
    ]


def test_update_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client, status="draft")

    response = client.put(
        f"{API_PREFIX}/surveys/{survey_id}",
        json={"title": "Updated Survey", "status": "closed", "category": "backend"},
    )

    assert response.status_code == 200
    body = unwrap(response)
    assert body["title"] == "Updated Survey"
    assert body["status"] == "closed"
    assert body["category"] == "backend"


def test_delete_survey(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    delete_response = client.delete(f"{API_PREFIX}/surveys/{survey_id}")
    get_response = client.get(f"{API_PREFIX}/surveys/{survey_id}")

    assert delete_response.status_code == 200
    assert unwrap(delete_response) is None
    assert get_response.status_code == 404


def test_get_missing_survey_returns_404(client: TestClient) -> None:
    response = client.get(f"{API_PREFIX}/surveys/999")

    assert response.status_code == 404
    assert error_message(response) == "Survey not found"


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

    first_response = client.post(f"{API_PREFIX}/answers", json=payload, headers=headers)
    second_response = client.post(f"{API_PREFIX}/answers", json=payload, headers=headers)
    count_response = client.get(f"{API_PREFIX}/surveys/{survey_id}/answer-stats")

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert unwrap(first_response)["id"] == unwrap(second_response)["id"]
    assert unwrap(first_response)["business_key"] == unwrap(second_response)["business_key"]
    assert count_response.status_code == 200
    assert unwrap(count_response)["answers_count"] == 1


def test_create_answer_notifies_downstream_services(
    client: TestClient,
    monkeypatch,
) -> None:
    survey_id = create_sample_survey(client)
    captured: dict[str, object] = {}

    def fake_notify(
        *,
        answer: AnswerRead,
        survey,
        answer_names: list[str] | None = None,
        xp_amount: float = 5.0,
        duration_seconds: float | None = None,
    ) -> None:
        captured["answer"] = answer
        captured["survey_id"] = survey.id
        captured["answer_names"] = answer_names
        captured["xp_amount"] = xp_amount

    monkeypatch.setattr("app.routers.answers.notify_downstream_services", fake_notify)

    response = client.post(
        f"{API_PREFIX}/answers",
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
    assert captured["answer_names"] == ["experience", "language"]
    assert captured["xp_amount"] == 5.0


def test_add_question_allows_existing_respondent_to_answer_new_question(
    client: TestClient,
    monkeypatch,
) -> None:
    survey_id = create_sample_survey(client)
    captured_notifications: list[dict[str, object]] = []

    def fake_notify(
        *,
        answer: AnswerRead,
        survey,
        answer_names: list[str] | None = None,
        xp_amount: float = 5.0,
        duration_seconds: float | None = None,
    ) -> None:
        captured_notifications.append(
            {
                "survey_id": survey.id,
                "answer_id": answer.id,
                "answer_names": answer_names,
                "xp_amount": xp_amount,
            }
        )

    monkeypatch.setattr("app.routers.answers.notify_downstream_services", fake_notify)

    first_response = client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 77,
            "answers": [
                {"name": "experience", "value": "Great"},
                {"name": "language", "value": "python"},
            ],
        },
    )
    add_question_response = client.post(
        f"{API_PREFIX}/surveys/{survey_id}/questions",
        json={
            "name": "extra",
            "text": "What should we add?",
            "type": "text",
            "required": True,
        },
    )
    second_response = client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 77,
            "answers": [{"name": "extra", "value": "More practice"}],
        },
    )
    count_response = client.get(f"{API_PREFIX}/surveys/{survey_id}/answer-stats")

    assert first_response.status_code == 201
    assert add_question_response.status_code == 201
    assert len(unwrap(add_question_response)["questions"]) == 4
    assert second_response.status_code == 200
    assert unwrap(count_response)["answers_count"] == 1
    assert unwrap(second_response)["answers"][-1] == {
        "name": "extra",
        "value": "More practice",
    }
    assert captured_notifications == [
        {
            "survey_id": survey_id,
            "answer_id": unwrap(first_response)["id"],
            "answer_names": ["experience", "language"],
            "xp_amount": 5.0,
        },
        {
            "survey_id": survey_id,
            "answer_id": unwrap(first_response)["id"],
            "answer_names": ["extra"],
            "xp_amount": 2.5,
        },
    ]


def test_add_question_rejects_duplicate_name(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    response = client.post(
        f"{API_PREFIX}/surveys/{survey_id}/questions",
        json={
            "name": "experience",
            "text": "Duplicate question",
            "type": "text",
            "required": True,
        },
    )

    assert response.status_code == 409
    assert error_message(response) == "Question with this name already exists"


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

    first_response = client.post(f"{API_PREFIX}/answers", json=first_payload)
    second_response = client.post(
        f"{API_PREFIX}/answers",
        json=second_payload,
        headers={"Idempotency-Key": "new-key-for-same-user"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert error_message(second_response) == "Respondent has already submitted an answer for this survey"


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

    first_response = client.post(f"{API_PREFIX}/answers", json=first_payload, headers=headers)
    second_response = client.post(f"{API_PREFIX}/answers", json=second_payload, headers=headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert error_message(second_response) == "Idempotency key has already been used for another request payload"


def test_answer_validation_rejects_invalid_option(client: TestClient) -> None:
    survey_id = create_sample_survey(client)

    response = client.post(
        f"{API_PREFIX}/answers",
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
    assert "expects one of" in error_message(response)


def test_draft_survey_rejects_answers(client: TestClient) -> None:
    survey_id = create_sample_survey(client, status="draft")

    response = client.post(
        f"{API_PREFIX}/answers",
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
    assert error_message(response) == "Answers can only be submitted to active surveys"


def test_bonus_question_adds_two_extra_xp_for_user_event(
    client: TestClient,
    monkeypatch,
) -> None:
    payload = build_survey_payload()
    payload["questions"][0]["is_bonus"] = True
    survey_response = client.post(f"{API_PREFIX}/surveys", json=payload)
    survey_id = unwrap(survey_response)["id"]
    captured_user_payloads: list[dict[str, object]] = []

    def fake_post_internal_event(
        *,
        base_url: str,
        path: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> None:
        if path == "/api/v1/internal-events:answer-created" and "xp_amount" in payload:
            captured_user_payloads.append(payload)

    monkeypatch.setattr(
        "app.services.downstream_notifications._post_internal_event",
        fake_post_internal_event,
    )

    response = client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 88,
            "answers": [
                {"name": "experience", "value": "Great"},
                {"name": "language", "value": "python"},
            ],
        },
    )

    assert response.status_code == 201
    assert captured_user_payloads[0]["xp_amount"] == 7.0
    assert captured_user_payloads[1]["xp_amount"] == 5.0


def test_text_answer_can_validate_email_and_phone(client: TestClient) -> None:
    payload = build_survey_payload()
    payload["questions"] = [
        {
            "name": "email",
            "text": "Email",
            "type": "text",
            "required": True,
            "validation": "email",
        },
        {
            "name": "phone",
            "text": "Phone",
            "type": "text",
            "required": True,
            "validation": "phone",
        },
    ]
    survey_id = unwrap(client.post(f"{API_PREFIX}/surveys", json=payload))["id"]

    invalid_response = client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 89,
            "answers": [
                {"name": "email", "value": "bad-email"},
                {"name": "phone", "value": "+7 999 111-22-33"},
            ],
        },
    )
    valid_response = client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": survey_id,
            "respondent_id": 90,
            "answers": [
                {"name": "email", "value": "user@example.com"},
                {"name": "phone", "value": "+7 999 111-22-33"},
            ],
        },
    )

    assert invalid_response.status_code == 422
    assert "valid email" in error_message(invalid_response)
    assert valid_response.status_code == 201


def test_popular_surveys_and_recommendations(client: TestClient) -> None:
    first_id = create_sample_survey(client, title="First", category="tech")
    second_id = create_sample_survey(client, title="Second", category="tech")
    create_sample_survey(client, title="Draft", category="tech", status="draft")

    client.post(
        f"{API_PREFIX}/answers",
        json={
            "survey_id": second_id,
            "respondent_id": 1,
            "answers": [
                {"name": "experience", "value": "Great"},
                {"name": "language", "value": "python"},
            ],
        },
    )

    popular_response = client.post(f"{API_PREFIX}/surveys:popular", json={})
    recommendations_response = client.post(
        f"{API_PREFIX}/surveys:recommendations",
        json={"category": "tech"},
    )

    assert popular_response.status_code == 200
    assert unwrap(popular_response)[0]["survey_id"] == second_id
    assert recommendations_response.status_code == 200
    assert [survey["id"] for survey in unwrap(recommendations_response)] == [second_id, first_id]
