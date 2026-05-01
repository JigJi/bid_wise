from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class TorSummary(BaseModel):
    """The structured extraction stored in `tor_analyses.summary`. Mirrors the
    LLM prompt schema (loosely typed because the shape evolves with prompt
    revisions; we ship the JSON through as-is rather than over-validating)."""
    model_config = ConfigDict(extra="allow")

    project: dict | None = None
    money: dict | None = None
    scope: dict | None = None
    qualification: dict | None = None
    evaluation: dict | None = None
    red_flags: dict | None = None


class TorAnalyzeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_id: str
    status: str
    prompt_version: str
    model_name: str
    summary: TorSummary | None = None
    raw_response: str | None = None
    error_message: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_sec: Decimal | None = None
    last_run_at: datetime | None = None


class TorQARequest(BaseModel):
    question: str
    # optional thread / company-profile hints to be added in Quick Win 1.5+
    company_profile: dict | None = None


class TorQAResponse(BaseModel):
    answer: str
    model: str
    duration_sec: Decimal
    input_tokens: int | None = None
    output_tokens: int | None = None
