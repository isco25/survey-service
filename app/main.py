from __future__ import annotations

from fastapi import FastAPI

from app.api import register_exception_handlers, success_response
from app.routers.answers import router as answers_router
from app.routers.surveys import router as surveys_router
from app.routers.users import router as users_router

app = FastAPI(
    title="Survey Service",
    description="Survey CRUD, submissions, and recommendation APIs.",
    version="1.0.0",
)
register_exception_handlers(app)


@app.get("/api/v1/health", summary="Service healthcheck")
def healthcheck() -> dict[str, object]:
    return success_response({"status": "ok"})


app.include_router(surveys_router)
app.include_router(answers_router)
app.include_router(users_router)
