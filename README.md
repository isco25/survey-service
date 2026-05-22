# survey-service

## 1. Название и назначение сервиса

`survey-service` — микросервис для создания, хранения и обработки опросов в системе.

Сервис отвечает за:
- создание, обновление, удаление и получение опросов;
- хранение вопросов и ответов пользователей;
- поиск и рекомендации опросов;
- обработку бонусных вопросов;
- валидацию пользовательских ответов;
- отправку аналитических и XP-событий во внешние сервисы.

### Основные возможности

- CRUD-операции для опросов
- поиск опросов через `POST /api/v1/surveys:search`
- поддержка изображений у опросов (`image_url`)
- бонусные вопросы (`is_bonus`) с начислением `+2 XP`
- regex-валидация текстовых ответов (`email`, `phone`)
- идемпотентная отправка ответов
- частичное дозаполнение ответов после добавления новых вопросов
- аналитические endpoints для популярных опросов и рекомендаций

---

## 2. Архитектура и зависимости

### Технологии и фреймворки

Сервис реализован на:
- Python
- FastAPI
- SQLAlchemy
- Alembic
- SQLite
- Pytest
- Docker

### Взаимодействие с другими микросервисами

#### `user-service`

Используется для отправки XP-событий после прохождения опроса.

Endpoint:
- `POST /api/v1/internal-events:answer-created`

#### `analytics-service`

Используется для отправки аналитических событий и получения статистики.

Endpoints:
- `POST /api/v1/internal-events:answer-created`
- `POST /api/v1/internal-events:submission-created`

Также сервис предоставляет:
- список опросов автора;
- статистику по ответам.

### Внешние зависимости

На текущий момент сервис использует:
- SQLite в качестве базы данных
- Docker для контейнеризации

---

## 3. Способы запуска сервиса

### Запуск через Docker

```powershell
docker build -t survey-service .

docker run --rm -p 8001:8001 `
  -e DATABASE_URL=sqlite:///./data/survey.db `
  -e USER_SERVICE_URL=http://host.docker.internal:8080 `
  -e ANALYTICS_SERVICE_URL=http://host.docker.internal:8082 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  survey-service
```

### Локальный запуск без Docker

```powershell
python -m venv .venv

.\.venv\Scripts\python -m pip install -r requirements.txt

.\.venv\Scripts\python -m alembic upgrade head

.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Переменные окружения

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/survey.db` | SQLite база данных |
| `USER_SERVICE_URL` | `http://localhost:8080` | адрес `user-service` |
| `ANALYTICS_SERVICE_URL` | `http://localhost:8082` | адрес `analytics-service` |
| `INTERNAL_API_KEY` | `change-me` | ключ внутренних API |
| `HTTP_TIMEOUT_SECONDS` | `5.0` | timeout исходящих HTTP-запросов |

---

## 4. API документация

Сервис соответствует `API Design Guide`:
https://docs.ensi.tech/guidelines/api

### Базовая информация

- базовый префикс API: `/api/v1`
- формат ответов:
  - `data`
  - `errors`
  - `meta`

### Основные endpoints

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/health` | healthcheck |
| `POST` | `/api/v1/surveys` | создать опрос |
| `POST` | `/api/v1/surveys:search` | поиск опросов |
| `GET` | `/api/v1/surveys/{survey_id}` | получить опрос |
| `PUT` | `/api/v1/surveys/{survey_id}` | обновить опрос |
| `DELETE` | `/api/v1/surveys/{survey_id}` | удалить опрос |
| `POST` | `/api/v1/surveys/{survey_id}/questions` | добавить вопрос |
| `GET` | `/api/v1/surveys/{survey_id}/answer-stats` | статистика ответов |
| `POST` | `/api/v1/surveys:popular` | популярные опросы |
| `POST` | `/api/v1/surveys:recommendations` | рекомендации |
| `POST` | `/api/v1/answers` | отправить ответ |
| `POST` | `/api/v1/users/{user_id}/surveys:search` | опросы автора |

### Пример создания опроса

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

---

## 5. Как тестировать

### Запуск тестов

```powershell
python -m pytest
```

### Git hooks

В репозиторий добавлен `pre-push` hook, который запускает тесты перед отправкой изменений.

#### Установка внутри `survey-service`

```powershell
git config core.hooksPath .githooks
```

#### Установка из корня монорепозитория

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ..\..\scripts\install-git-hooks.ps1
```

---

## 6. Контакты и поддержка

### Автор
Скалеух Ивар


### Поддержка

- https://github.com/isco25/survey-service/issues
- @Truasu
