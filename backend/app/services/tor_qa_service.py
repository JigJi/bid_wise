"""TOR Q&A — answer free-form vendor questions about a specific project's TOR.

Lightweight RAG: we already have full TOR text + structured summary in DB,
so for one project the entire context fits in the LLM window. No vector
search needed. (Will revisit if we add cross-project Q&A.)

Default model is gpt-4o-mini for cost (Q&A is the high-volume path); caller
can override per-call.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import PdfTemplate, TorAnalysis, Project
from app.services import llm_client

MAX_TOR_CHARS = 50_000  # context budget for Q&A; enough for a full D1 PDF

SYSTEM_PROMPT = """\
You are bid_wise — a smart admin helping Thai vendors evaluate government
procurement projects. Answer questions about a specific TOR concisely in
Thai, citing the section/clause when possible.

Rules:
- Stick to what the TOR document says. If the answer is not in the TOR,
  say "ไม่ปรากฏในเอกสาร" — do NOT make up requirements.
- Be concise. Default 2-4 sentences. Bullet only when the answer is a list.
- Use the structured summary as a quick lookup but always prefer the raw
  TOR text when there's a discrepancy.
- If the user's question is about whether their company qualifies, ask one
  clarifying question if you're missing critical company info.
"""


def _build_user_prompt(*, tor_text: str, summary: dict | None, project_meta: dict | None, question: str, company_profile: dict | None) -> str:
    parts = []
    if project_meta:
        parts.append("=== ข้อมูลโครงการ (จากระบบ e-GP) ===")
        parts.append(json.dumps(project_meta, ensure_ascii=False, indent=2))
    if summary:
        parts.append("=== สรุปโครงสร้าง TOR (สกัดด้วย AI) ===")
        parts.append(json.dumps(summary, ensure_ascii=False, indent=2))
    if company_profile:
        parts.append("=== ข้อมูลบริษัทผู้ถาม ===")
        parts.append(json.dumps(company_profile, ensure_ascii=False, indent=2))
    truncated = tor_text[:MAX_TOR_CHARS]
    if len(tor_text) > MAX_TOR_CHARS:
        truncated += f"\n\n[truncated; original {len(tor_text)} chars]"
    parts.append("=== TOR ฉบับเต็ม ===")
    parts.append(truncated)
    parts.append("=== คำถามของผู้ใช้ ===")
    parts.append(question.strip())
    return "\n\n".join(parts)


def answer(db: Session, project_id: str, question: str, *,
           company_profile: dict | None = None, model: str | None = None) -> dict[str, Any]:
    """Return {answer, model, duration_sec, input_tokens, output_tokens}.
    Raises ValueError if no TOR text is available for this project.
    """
    pdf = (
        db.query(PdfTemplate)
        .filter_by(project_id=project_id, template_type="D1")
        .order_by(PdfTemplate.id.desc())
        .first()
    )
    if pdf is None or not pdf.extracted_text:
        raise ValueError(f"no D1 TOR text for project_id={project_id}")

    analysis = (
        db.query(TorAnalysis)
        .filter_by(project_id=project_id, status="COMPLETED")
        .order_by(TorAnalysis.id.desc())
        .first()
    )
    summary = analysis.summary if analysis else None

    proj = db.get(Project, project_id)
    project_meta: dict | None = None
    if proj is not None:
        project_meta = {
            "project_id": proj.project_id,
            "project_name": proj.project_name,
            "dept_sub_name": (proj.raw_detail or {}).get("deptSubName") if proj.raw_detail else None,
            "method_id": proj.method_id,
            "step_id": proj.step_id,
            "project_money": float(proj.project_money) if proj.project_money else None,
            "price_build": float(proj.price_build) if proj.price_build else None,
            "price_agree": float(proj.price_agree) if proj.price_agree else None,
            "announce_date": str(proj.announce_date) if proj.announce_date else None,
        }

    user_prompt = _build_user_prompt(
        tor_text=pdf.extracted_text,
        summary=summary,
        project_meta=project_meta,
        question=question,
        company_profile=company_profile,
    )
    return llm_client.chat_text(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model=model,
        temperature=0.2,
        max_tokens=1500,
    )
