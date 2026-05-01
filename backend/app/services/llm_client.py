"""Single LLM client for bid_wise.

Uses the OpenAI Python SDK pointed at OpenRouter so we can switch provider/model
by changing a string. All LLM calls in the app go through this module so we can
add caching, telemetry, and rate limiting in one place later.

Two model defaults (set in .env):
  - LLM_MODEL_EXTRACTION  — quality-first; structured TOR JSON, run once per project
  - LLM_MODEL_QA          — cost-first; user Q&A on extracted TOR, repeated calls
"""
from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from app.core.config import settings


def _client() -> OpenAI:
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set in .env. Get a key at https://openrouter.ai/keys"
        )
    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        default_headers={
            # OpenRouter recommends including these for app-attribution + rankings
            "HTTP-Referer": settings.LLM_HTTP_REFERER,
            "X-Title": settings.LLM_APP_TITLE,
        },
    )


def chat_json(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 8000,
) -> dict[str, Any]:
    """One-shot LLM call that expects a JSON object back. Returns dict with:
        json: parsed dict (None on parse failure)
        raw: full text body
        model: actually-used model string
        input_tokens / output_tokens: from usage if provided by the upstream
        duration_sec
    Caller decides how to handle parse failures (retry / fallback / store error).
    """
    model = model or settings.LLM_MODEL_EXTRACTION
    cli = _client()
    t0 = time.monotonic()
    resp = cli.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # OpenRouter passes through to upstream when supported (Claude/GPT-4o)
        response_format={"type": "json_object"},
    )
    dt = time.monotonic() - t0

    text = resp.choices[0].message.content or ""
    parsed: dict | None = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    usage = getattr(resp, "usage", None)
    return {
        "json": parsed,
        "raw": text,
        "model": resp.model or model,
        "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "duration_sec": round(dt, 2),
    }


def chat_text(
    *,
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> dict[str, Any]:
    """Free-form text response. For Q&A and human-readable summaries."""
    model = model or settings.LLM_MODEL_QA
    cli = _client()
    t0 = time.monotonic()
    resp = cli.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    dt = time.monotonic() - t0
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    return {
        "text": text,
        "model": resp.model or model,
        "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "duration_sec": round(dt, 2),
    }
