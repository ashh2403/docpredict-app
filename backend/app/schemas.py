"""Pydantic request/response schemas."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Theme = Literal["light", "dark", "system"]
Priority = Literal["low", "medium", "high"]


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes long.")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one number.")
    return value


def _clean_name(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("Name cannot be empty.")
    if any(ord(c) < 32 for c in value):
        raise ValueError("Name contains invalid characters.")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(max_length=128)

    _name = field_validator("full_name")(_clean_name)
    _pw = field_validator("password")(_validate_password)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    theme: Theme
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    theme: Theme | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return None if v is None else _clean_name(v)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    _pw = field_validator("new_password")(_validate_password)


class AccountDelete(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class AnalysisUpdate(BaseModel):
    bookmarked: bool


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    word_count: int
    category: str
    category_label: str
    confidence: float
    is_uncertain: bool
    priority: Priority
    bookmarked: bool
    summary: str
    keywords: list[dict]
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    page_count: int | None
    char_count: int
    uncertainty_reasons: list[str]
    top_predictions: list[dict]
    explanation: dict
    extracted_fields: dict
    priority_reasons: list[str]
    model_version: str
    processing_ms: int


class AnalysisPage(BaseModel):
    items: list[AnalysisSummary]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    detail: str
