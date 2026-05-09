# Survey Service

## 1. Название и назначение сервиса

`survey-service` — микросервис опросов в системе PIUS. Он отвечает за создание и хранение опросов, вопросы внутри опросов, прием ответов пользователей и отправку событий в другие сервисы.

Основные функции:

- CRUD для опросов;
- хранение категории, статуса и структуры вопросов;
- прием и валидация ответов;
- идемпотентное сохранение ответов через `Idempotency-Key`;
- подсчет количества ответов по опросу;
- отправка событий в `user-service` и `analytics-service`.

## 2. Архитектура и зависимости

Технологии:

- Python 3.11;
- FastAPI и Uvicorn;
- Pydantic;
- SQLAlchemy;
- SQLite;
- Alembic;
- HTTPX;
- pytest и FastAPI TestClient.

Взаимодействие с микросервисами:

- вызывает `user-service`: `POST /internal/events/answer-created` для начисления XP;
- вызывает `analytics-service`: `POST /internal/events/submission-created` для обновления аналитики;
- предоставляет `analytics-service` эндпоинты `GET /surveys/{id}/answers/count` и `GET /users/{user_id}/surveys`;
- внутренние вызовы защищены `INTERNAL_API_KEY`.

Внешние сервисы не используются. Redis, Kafka, S3 и внешняя PostgreSQL в текущей версии не требуются.

## 3. Способы запуска сервиса

### Через Docker

```powershell
docker build -t survey-service .
docker run --rm -p 8081:8081 `
  -e DATABASE_URL=sqlite:///./data/survey.db `
  -e USER_SERVICE_URL=http://host.docker.internal:8080 `
  -e ANALYTICS_SERVICE_URL=http://host.docker.internal:8082 `
  -e INTERNAL_API_KEY=change-me-local-internal-key `
  survey-service
```

### Без Docker

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8081
```

### Переменные окружения

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./survey.db` | SQLite база данных |
| `USER_SERVICE_URL` | `http://localhost:8080` | URL сервиса пользователей |
| `ANALYTICS_SERVICE_URL` | `http://localhost:8082` | URL сервиса аналитики |
| `INTERNAL_API_KEY` | `change-me` | ключ внутренних API-вызовов |
| `HTTP_TIMEOUT_SECONDS` | `5.0` | таймаут исходящих HTTP-запросов |

Для запуска всей системы используется общий репозиторий `bozvan/PIUS` и команда `docker compose up --build -d`.

## 4. API документация

После запуска Swagger доступен по адресу:

- `http://localhost:8081/docs`
- `http://localhost:8081/openapi.json`

Основные эндпоинты:

| Метод | Путь | Описание |
| --- | --- | --- |
| `GET` | `/health` | проверка работоспособности |
| `POST` | `/surveys` | создание опроса |
| `GET` | `/surveys` | список опросов, фильтр по категории |
| `GET` | `/surveys/{survey_id}` | получение опроса |
| `PUT` | `/surveys/{survey_id}` | обновление опроса |
| `DELETE` | `/surveys/{survey_id}` | удаление опроса |
| `POST` | `/answers` | сохранение ответа и отправка событий |
| `GET` | `/surveys/{survey_id}/answers/count` | количество ответов |
| `GET` | `/users/{user_id}/surveys` | опросы пользователя |

## 5. Как тестировать

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pytest
```

## 6. Контакты и поддержка

Автор сервиса: Скалеух И.

Поддержка:

- GitHub Issues: https://github.com/isco25/survey-service/issues
- GitHub: https://github.com/isco25
