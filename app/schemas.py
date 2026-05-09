from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SurveyStatus = Literal["draft", "active", "closed"]
QuestionType = Literal["text", "single_choice", "multiple_choice"]


def normalize_category(value: str) -> str:
    return value.strip().lower()


class SurveyQuestion(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1, max_length=255)
    type: QuestionType
    options: list[str] = Field(default_factory=list)
    required: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("options")
    @classmethod
    def normalize_options(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("Question options must not be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Question options must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_question(self) -> SurveyQuestion:
        if self.type == "text" and self.options:
            raise ValueError("Text questions must not define options")
        if self.type in {"single_choice", "multiple_choice"} and not self.options:
            raise ValueError("Choice questions must define options")
        return self


class SurveyBase(BaseModel):
    author_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(..., min_length=1, max_length=64)
    questions: list[SurveyQuestion] = Field(..., min_length=1)
    status: SurveyStatus = "draft"

    @field_validator("category")
    @classmethod
    def normalize_category_value(cls, value: str) -> str:
        return normalize_category(value)

    @model_validator(mode="after")
    def validate_question_names(self) -> SurveyBase:
        names = [question.name for question in self.questions]
        if len(set(names)) != len(names):
            raise ValueError("Question names must be unique inside a survey")
        return self


class SurveyCreate(SurveyBase):
    pass


class SurveyUpdate(BaseModel):
    author_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    questions: list[SurveyQuestion] | None = Field(default=None, min_length=1)
    status: SurveyStatus | None = None

    @field_validator("category")
    @classmethod
    def normalize_category_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_category(value)

    @model_validator(mode="after")
    def validate_question_names(self) -> SurveyUpdate:
        if self.questions is None:
            return self
        names = [question.name for question in self.questions]
        if len(set(names)) != len(names):
            raise ValueError("Question names must be unique inside a survey")
        return self


class SurveyRead(SurveyBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AnswerItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    value: Any

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class AnswerCreate(BaseModel):
    survey_id: int = Field(..., gt=0)
    respondent_id: int = Field(..., gt=0)
    answers: list[AnswerItem] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_answers(self) -> AnswerCreate:
        names = [answer.name for answer in self.answers]
        if len(set(names)) != len(names):
            raise ValueError("Answer names must be unique inside one submission")
        return self


class AnswerRead(BaseModel):
    id: int
    survey_id: int
    respondent_id: int
    business_key: str
    source_service: str
    answers: list[AnswerItem]
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerCountRead(BaseModel):
    survey_id: int
    answers_count: int
