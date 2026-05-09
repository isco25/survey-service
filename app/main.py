from __future__ import annotations

from fastapi import FastAPI

from app.routers.answers import router as answers_router
from app.routers.surveys import router as surveys_router
from app.routers.users import router as users_router

app = FastAPI(
    title="Сервис опросов",
    description="CRUD опросов и сохранение ответов.",
    version="1.0.0",
)


@app.get("/health", summary="Проверка здоровья сервиса")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(surveys_router)
app.include_router(answers_router)
app.include_router(users_router)
