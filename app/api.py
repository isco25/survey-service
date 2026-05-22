from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    meta: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    errors: list[ApiError] | None = None
    meta: dict[str, Any] | None = None


def success_response(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"data": data}
    if meta is not None:
        payload["meta"] = meta
    return payload


def empty_response() -> dict[str, Any]:
    return {"data": None}


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if meta is not None:
        error["meta"] = meta
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "errors": [error],
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(
            status_code=exc.status_code,
            code=_resolve_error_code(exc.status_code),
            message=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(_, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="ValidationHttpException",
            message="Request validation failed",
            meta={"validation": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(_, __: Exception) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="InternalServerError",
            message="Internal server error",
        )


def _resolve_error_code(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "BadRequestHttpException",
        status.HTTP_401_UNAUTHORIZED: "UnauthorizedHttpException",
        status.HTTP_403_FORBIDDEN: "ForbiddenHttpException",
        status.HTTP_404_NOT_FOUND: "NotFoundHttpException",
        status.HTTP_409_CONFLICT: "ConflictHttpException",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "ValidationHttpException",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "InternalServerError",
    }.get(status_code, "HttpException")
