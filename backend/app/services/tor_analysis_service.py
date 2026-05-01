"""TOR / D1 PDF structured extraction.

Uses an LLM to read the Thai TOR text and return a structured JSON document
with project basics, money, scope (with itemized BOQ), qualification rules,
and red-flag signals (tailored-bid indicators).

Designed to be re-runnable: each call writes a new TorAnalysis row keyed by
(project_id, prompt_version, model_name) so we can compare prompt iterations
and provider outputs side-by-side without losing history.
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.models import TorAnalysis, PdfTemplate
from app.services import llm_client

PROMPT_VERSION = "v1"

# How much of the PDF text we send to the LLM. Claude Sonnet 4.5 has a huge
# context window so this is generous; trim only to keep cost in check on
# unusually large TORs (we've seen ~33k chars on typical D1 PDFs).
MAX_TOR_CHARS = 60_000

SYSTEM_PROMPT = """\
You are a senior Thai government procurement analyst. You read Thai TOR
(เอกสารประกวดราคา / ขอบเขตของงาน) PDFs and extract structured data for
vendor analytics.

Rules:
- Output a single valid JSON object that matches the schema given by the user.
- Use null when a field is not stated in the document. NEVER invent values.
- Numbers must be numeric (no thousand separators, no currency suffix).
- All free-text fields keep the original Thai unless the schema says English.
- For dates, copy the raw text the document uses (Thai BE is fine).
- For "red_flags": be specific and conservative. Flag only patterns that
  *materially* narrow the bidder pool (e.g. brand-locked specs, very tight
  timelines under 7 working days, capital requirements far above project
  size, oddly-specific certifications). Do not flag standard boilerplate.
"""

# JSON schema as a string we paste into the user prompt so the model knows
# exactly which keys / types are expected. We do NOT use OpenAI's strict
# JSON schema mode here because OpenRouter passes that through unevenly to
# Claude — instead we rely on response_format=json_object + a clear schema
# in the prompt + post-validation.
SCHEMA_DOC = """\
Return JSON with exactly these top-level keys:

{
  "project": {
    "name": str | null,
    "dept_name": str | null,
    "method": str | null,                    // "e-bidding" / "เฉพาะเจาะจง" / "สอบราคา" / etc
    "announce_date_text": str | null,        // raw Thai date text from doc
    "submission_deadline_text": str | null,  // raw Thai date+time text
    "bid_open_date_text": str | null
  },
  "money": {
    "budget_thb": number | null,             // วงเงินงบประมาณ
    "price_build_thb": number | null,        // ราคากลาง
    "bid_bond_thb": number | null,
    "bid_bond_pct": number | null,
    "performance_bond_pct": number | null
  },
  "scope": {
    "thai_summary": str,                     // 2-3 sentence summary, Thai
    "items": [                               // BOQ-like itemization if present
      { "item": str, "qty": number | null, "unit": str | null, "spec": str | null }
    ],
    "delivery_days": number | null,
    "delivery_location": str | null
  },
  "qualification": {
    "juridical_type": str | null,            // "นิติบุคคล" / "บุคคลธรรมดา" / "ทั้งสอง"
    "registered_capital_min_thb": number | null,
    "paid_capital_min_thb": number | null,
    "past_work_required": [
      { "description": str, "value_min_thb": number | null, "recency_years": number | null }
    ],
    "certifications_required": [str],
    "sme_advantage": boolean | null,
    "blacklist_check": boolean | null
  },
  "evaluation": {
    "criteria": str | null,                  // "เกณฑ์ราคา" / "เกณฑ์ราคาประกอบเกณฑ์อื่น" / etc
    "min_quality_score": number | null
  },
  "red_flags": {
    "unusual_qualifications": [str],          // each entry: short Thai phrase
    "tight_timeline_days": number | null,    // calendar days from announce → submission
    "brand_specific": boolean | null,
    "notes": str | null                       // 1-2 sentences why we flagged
  }
}

If a list section has no entries, return an empty list ([]), not null.
"""


def _build_user_prompt(tor_text: str) -> str:
    truncated = tor_text[:MAX_TOR_CHARS]
    if len(tor_text) > MAX_TOR_CHARS:
        truncated += f"\n\n[...truncated; original was {len(tor_text)} chars]"
    return (
        SCHEMA_DOC
        + "\n\n--- TOR TEXT BELOW ---\n\n"
        + truncated
    )


def analyze_tor(
    db: Session,
    project_id: str,
    *,
    pdf_template_id: int | None = None,
    tor_text: str | None = None,
    model: str | None = None,
) -> TorAnalysis:
    """Run extraction on a project's TOR text. Returns the persisted TorAnalysis row.

    If tor_text is None, looks up `pdf_templates` for the latest D1 PDF for the
    project and uses its `extracted_text`. Raises if nothing usable found.
    """
    if tor_text is None:
        q = db.query(PdfTemplate).filter_by(project_id=project_id, template_type="D1").order_by(PdfTemplate.id.desc())
        pdf = q.first()
        if pdf is None:
            raise ValueError(f"no D1 PDF in pdf_templates for project_id={project_id}")
        if not pdf.extracted_text:
            raise ValueError(f"D1 PDF for project_id={project_id} has no extracted_text")
        pdf_template_id = pdf.id
        tor_text = pdf.extracted_text

    row = TorAnalysis(
        project_id=project_id,
        pdf_template_id=pdf_template_id,
        prompt_version=PROMPT_VERSION,
        model_name=model or "",
        status="PROCESSING",
    )
    db.add(row)
    db.flush()

    t0 = time.monotonic()
    try:
        result = llm_client.chat_json(
            system=SYSTEM_PROMPT,
            user=_build_user_prompt(tor_text),
            model=model,
            temperature=0.0,
            max_tokens=8000,
        )
    except Exception as e:
        row.status = "FAILED"
        row.error_message = f"{type(e).__name__}: {e}"
        row.duration_sec = round(time.monotonic() - t0, 2)
        db.commit()
        return row

    row.model_name = result.get("model") or row.model_name
    row.raw_response = result.get("raw")
    row.input_tokens = result.get("input_tokens")
    row.output_tokens = result.get("output_tokens")
    row.duration_sec = result.get("duration_sec")

    if result.get("json") is None:
        row.status = "FAILED"
        row.error_message = "LLM returned non-JSON or invalid JSON"
    else:
        row.summary = result["json"]
        row.status = "COMPLETED"

    db.commit()
    return row
