"""CLI: extract structured TOR JSON from already-ingested D1 PDFs.

Usage:
    python scripts/analyze_tor.py                # all projects with a D1 PDF
    python scripts/analyze_tor.py 69039576531    # one specific projectId
    python scripts/analyze_tor.py --model openai/gpt-4o   # override model

Prereq:
    .env has OPENROUTER_API_KEY filled (https://openrouter.ai/keys)
    `pdf_templates` table has rows with template_type='D1' and extracted_text
    populated (run scripts/ingest_project.py first if not).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from app.core.database import SessionLocal  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.models import PdfTemplate, TorAnalysis  # noqa: E402
from app.services import tor_analysis_service  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_ids", nargs="*", help="Optional project IDs to limit to")
    ap.add_argument("--model", default=None, help=f"Override model (default {settings.LLM_MODEL_EXTRACTION})")
    ap.add_argument("--reanalyze", action="store_true", help="Re-run even if a COMPLETED analysis exists")
    args = ap.parse_args()

    if not settings.OPENROUTER_API_KEY:
        print("[!] OPENROUTER_API_KEY is empty. Fill it in .env first.")
        print("    Get a key at https://openrouter.ai/keys")
        return 1

    db = SessionLocal()
    try:
        q = db.query(PdfTemplate).filter_by(template_type="D1")
        if args.project_ids:
            q = q.filter(PdfTemplate.project_id.in_(args.project_ids))
        pdfs = q.all()
        if not pdfs:
            print("[!] no D1 PDFs in DB. Run scripts/ingest_project.py <pid> first.")
            return 2

        print(f"[+] {len(pdfs)} D1 PDF(s) ready for analysis")
        print(f"[+] model = {args.model or settings.LLM_MODEL_EXTRACTION}")

        for pdf in pdfs:
            existing = (
                db.query(TorAnalysis)
                .filter_by(project_id=pdf.project_id, prompt_version=tor_analysis_service.PROMPT_VERSION, status="COMPLETED")
                .first()
            )
            if existing and not args.reanalyze:
                print(f"\n  pid={pdf.project_id}  [skip — already COMPLETED, use --reanalyze to redo]")
                continue

            print(f"\n  pid={pdf.project_id}  text_chars={len(pdf.extracted_text or '')}")
            row = tor_analysis_service.analyze_tor(
                db, pdf.project_id, pdf_template_id=pdf.id, model=args.model,
            )
            print(f"    status={row.status}  model={row.model_name}  duration={row.duration_sec}s")
            if row.input_tokens:
                print(f"    tokens: in={row.input_tokens} out={row.output_tokens}")
            if row.status == "COMPLETED" and row.summary:
                s = row.summary
                proj = s.get("project") or {}
                money = s.get("money") or {}
                qual = s.get("qualification") or {}
                rf = s.get("red_flags") or {}
                items = (s.get("scope") or {}).get("items") or []
                print(f"    name: {(proj.get('name') or '')[:80]!r}")
                print(f"    method: {proj.get('method')}  budget={money.get('budget_thb')}  price_build={money.get('price_build_thb')}")
                print(f"    submission deadline: {proj.get('submission_deadline_text')}")
                print(f"    BOQ items: {len(items)}")
                print(f"    qualification: capital_min={qual.get('registered_capital_min_thb')}  past_work={len(qual.get('past_work_required') or [])} cert={len(qual.get('certifications_required') or [])}")
                print(f"    red_flags: brand_specific={rf.get('brand_specific')}  unusual={len(rf.get('unusual_qualifications') or [])}")
                if rf.get("notes"):
                    print(f"      notes: {rf['notes'][:200]}")
            elif row.error_message:
                print(f"    error: {row.error_message[:200]}")
                if row.raw_response:
                    print(f"    raw[:200]: {row.raw_response[:200]!r}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
