from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.triage import QuestionType
from app.schemas.common import ORMModel


class TriageQuestionInput(BaseModel):
    text: str
    qtype: QuestionType = QuestionType.TEXT
    options: list[str] = Field(default_factory=list)
    order: int = 0
    required: bool = True
    is_active: bool = True


class TriageQuestionRead(ORMModel):
    id: int
    text: str
    qtype: QuestionType
    options: list[str]
    order: int
    required: bool
    is_active: bool


class TriageAnswerInput(BaseModel):
    question_id: int
    # Value shape depends on the question type: str | bool | list[str].
    value: Any = None


class TriageAnswerRead(ORMModel):
    question_id: int
    question_text: str
    value: Any


class TriageResponseRead(ORMModel):
    id: int
    answers: list[TriageAnswerRead]
