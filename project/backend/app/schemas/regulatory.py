from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    unit_name: str = Field(min_length=1, max_length=100)
    year: int = Field(default=2026, ge=2020, le=2100, strict=True)
    quarter: int = Field(default=3, ge=1, le=4, strict=True)
    owner: str = Field(min_length=1, max_length=50)
    due_date: date
    note: str = Field(min_length=5, max_length=1000)


class CaseTransition(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    target: Literal['checking', 'rectifying', 'review', 'closed']
    note: str = Field(min_length=5, max_length=2000)
    actor: str = Field(min_length=1, max_length=50)
    version: int = Field(ge=1, strict=True)
