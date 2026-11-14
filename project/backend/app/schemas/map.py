from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..services.spatial import validate_ring


class AreaSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coordinates: list[list[float]]

    @field_validator("coordinates", mode="before")
    @classmethod
    def polygon(cls, value):
        return validate_ring(value)


class MapContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool = True
    selected_unit: str | None = Field(default=None, max_length=100)
    area: AreaSelection | None = None
    year: int = Field(default=2026, ge=2020, le=2100, strict=True)
    quarter: int = Field(default=3, ge=1, le=4, strict=True)


class AreaAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area: AreaSelection
    industry: Literal["制造业", "服务业", "农业", "建筑业"] | None = None
    warning_percent: float = Field(default=90, ge=50, le=100, allow_inf_nan=False)
    year: int = Field(default=2026, ge=2020, le=2100, strict=True)
    quarter: int = Field(default=3, ge=1, le=4, strict=True)
