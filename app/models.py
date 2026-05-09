from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    author_id: Mapped[int] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    questions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    answers: Mapped[list["Answer"]] = relationship(
        back_populates="survey",
        cascade="all, delete-orphan",
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("survey_id", "respondent_id", name="uq_answers_survey_respondent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    respondent_id: Mapped[int] = mapped_column(nullable=False, index=True)
    business_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    source_service: Mapped[str] = mapped_column(String(64), nullable=False, default="api-gateway")
    answers: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    survey: Mapped["Survey"] = relationship(back_populates="answers")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "source_service",
            "operation",
            "idempotency_key",
            name="uq_idempotency_source_operation_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    business_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=OperationStatus.IN_PROGRESS.value
    )
    response_code: Mapped[int | None] = mapped_column(nullable=True)
    response_body: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_id: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
