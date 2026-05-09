# Survey Service

FastAPI service for survey CRUD, survey answer storage, idempotent answer creation,
and downstream notifications to user and analytics services.

## Port

- HTTP: `8081`

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./survey.db` | SQLite database URL |
| `USER_SERVICE_URL` | `http://localhost:8080` | Base URL for user-service |
| `ANALYTICS_SERVICE_URL` | `http://localhost:8082` | Base URL for analytics-service |
| `INTERNAL_API_KEY` | `change-me` | Token for internal service calls |
| `HTTP_TIMEOUT_SECONDS` | `5.0` | Outgoing HTTP timeout |

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Healthcheck |
| `POST` | `/surveys` | Create a survey |
| `GET` | `/surveys` | List surveys, optionally filtered by category |
| `GET` | `/surveys/{survey_id}` | Read a survey |
| `PUT` | `/surveys/{survey_id}` | Update a survey |
| `DELETE` | `/surveys/{survey_id}` | Delete a survey |
| `POST` | `/answers` | Store an answer and notify downstream services |
| `GET` | `/surveys/{survey_id}/answers/count` | Count answers for a survey |
| `GET` | `/users/{user_id}/surveys` | List surveys created by a user |

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## Docker

```powershell
docker build -t survey-service .
docker run --rm -p 8081:8081 `
  -e DATABASE_URL=sqlite:///./data/survey.db `
  -e USER_SERVICE_URL=http://host.docker.internal:8080 `
  -e ANALYTICS_SERVICE_URL=http://host.docker.internal:8082 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  survey-service
```

## Example `POST /answers`

```json
{
  "survey_id": 1,
  "respondent_id": 42,
  "answers": [
    {"name": "experience", "value": "Great"},
    {"name": "language", "value": "python"}
  ]
}
```

## Tests

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest
```
