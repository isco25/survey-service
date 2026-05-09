from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    user_service_url: str
    analytics_service_url: str
    internal_api_key: str
    http_timeout_seconds: float


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./survey.db"),
        user_service_url=os.getenv("USER_SERVICE_URL", "http://localhost:8080"),
        analytics_service_url=os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8082"),
        internal_api_key=os.getenv("INTERNAL_API_KEY", "change-me"),
        http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "5.0")),
    )
