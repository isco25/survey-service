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


def health_payload() -> dict[str, object]:
    return success_response({"status": "ok"})


@app.get("/api/v1/health", summary="Service healthcheck")
def healthcheck_v1() -> dict[str, object]:
    return health_payload()


@app.get("/health", include_in_schema=False)
def healthcheck_legacy() -> dict[str, object]:
    return health_payload()


app.include_router(surveys_router)
app.include_router(answers_router)
app.include_router(users_router)
