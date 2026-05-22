# Survey Service

`survey-service` отвечает за создание и хранение опросов, приём ответов, валидацию, бонусные вопросы, изображения у опросов и сервисные рекомендации.

## Возможности

- создание, обновление, удаление и получение опросов
- поиск опросов через `POST /api/v1/surveys:search`
- изображения у опросов через поле `image_url`
- бонусные вопросы через флаг `is_bonus` с дополнительным `+2 XP`
- валидация текстовых ответов по regex для `email` и `phone`
- идемпотентная отправка ответов
- частичное дозаполнение ответов после добавления новых вопросов
- аналитические endpoints для популярных опросов и рекомендаций

## API

Сервис приведён к `API Design Guide`: https://docs.ensi.tech/guidelines/api

- базовый префикс: `/api/v1`
- формат JSON-ответов: `data`, `errors`, `meta`

Основные маршруты:

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/health` | healthcheck |
| `POST` | `/api/v1/surveys` | создать опрос |
| `POST` | `/api/v1/surveys:search` | поиск опросов |
| `GET` | `/api/v1/surveys/{survey_id}` | получить опрос |
| `PUT` | `/api/v1/surveys/{survey_id}` | обновить опрос |
| `DELETE` | `/api/v1/surveys/{survey_id}` | удалить опрос |
| `POST` | `/api/v1/surveys/{survey_id}/questions` | добавить вопрос в опрос |
| `GET` | `/api/v1/surveys/{survey_id}/answer-stats` | статистика по числу ответов |
| `POST` | `/api/v1/surveys:popular` | популярные опросы |
| `POST` | `/api/v1/surveys:recommendations` | рекомендации опросов |
| `POST` | `/api/v1/answers` | отправить ответ |
| `POST` | `/api/v1/users/{user_id}/surveys:search` | список опросов автора |

Пример создания опроса:

```json
{
  "author_id": 7,
  "title": "Python Survey",
  "description": "Basic questionnaire",
  "image_url": "https://example.com/survey.png",
  "category": "tech",
  "status": "active",
  "questions": [
    {
      "name": "experience",
      "text": "How was your experience?",
      "type": "text",
      "required": true,
      "is_bonus": true
    },
    {
      "name": "email",
      "text": "Email",
      "type": "text",
      "required": true,
      "validation": "email"
    }
  ]
}
```

## Интеграции

- отправляет XP-события в `user-service` по `POST /api/v1/internal-events:answer-created`
- отправляет аналитические события в `analytics-service` по:
  - `POST /api/v1/internal-events:answer-created`
  - `POST /api/v1/internal-events:submission-created`
- отдаёт `analytics-service` список опросов автора и статистику по ответам

## Запуск

Через Docker:

```powershell
docker build -t survey-service .
docker run --rm -p 8001:8001 `
  -e DATABASE_URL=sqlite:///./data/survey.db `
  -e USER_SERVICE_URL=http://host.docker.internal:8080 `
  -e ANALYTICS_SERVICE_URL=http://host.docker.internal:8082 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  survey-service
```

Локально:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Переменные окружения:

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/survey.db` | SQLite база данных |
| `USER_SERVICE_URL` | `http://localhost:8080` | адрес `user-service` |
| `ANALYTICS_SERVICE_URL` | `http://localhost:8082` | адрес `analytics-service` |
| `INTERNAL_API_KEY` | `change-me` | ключ внутренних API |
| `HTTP_TIMEOUT_SECONDS` | `5.0` | timeout исходящих HTTP-запросов |

## Тесты

```powershell
python -m pytest
```

## Git hooks

В репозиторий добавлен `pre-push` hook, который запускает тесты.

Установка внутри `survey-service`:

```powershell
git config core.hooksPath .githooks
```

Либо из корня монорепозитория:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\..\scripts\install-git-hooks.ps1
```
