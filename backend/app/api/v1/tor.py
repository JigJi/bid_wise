"""TOR Intelligence endpoints — get extraction, run extraction, ask Q&A."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import TorAnalysis
from app.schemas import TorAnalyzeResponse, TorQARequest, TorQAResponse, TorSummary
from app.services import tor_analysis_service, tor_qa_service

router = APIRouter(prefix="/tor", tags=["tor"])


def _serialize(row: TorAnalysis) -> TorAnalyzeResponse:
    return TorAnalyzeResponse(
        project_id=row.project_id,
        status=row.status,
        prompt_version=row.prompt_version,
        model_name=row.model_name or "",
        summary=TorSummary(**row.summary) if row.summary else None,
        raw_response=row.raw_response if row.status == "FAILED" else None,
        error_message=row.error_message,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        duration_sec=row.duration_sec,
        last_run_at=row.last_run_at,
    )


@router.get("/{project_id}", response_model=TorAnalyzeResponse)
def get_analysis(project_id: str, db: Session = Depends(get_db)) -> TorAnalyzeResponse:
    """Return the latest analysis for a project. 404 if none exists."""
    row = (
        db.query(TorAnalysis)
        .filter_by(project_id=project_id)
        .order_by(TorAnalysis.id.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="no analysis yet — POST /analyze to create one")
    return _serialize(row)


@router.post("/{project_id}/analyze", response_model=TorAnalyzeResponse)
def analyze(project_id: str, db: Session = Depends(get_db)) -> TorAnalyzeResponse:
    """Run extraction (or re-run). Always creates a new TorAnalysis row."""
    try:
        row = tor_analysis_service.analyze_tor(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # OPENROUTER_API_KEY missing or similar config error
        raise HTTPException(status_code=503, detail=str(e))
    return _serialize(row)


@router.post("/{project_id}/qa", response_model=TorQAResponse)
def qa(project_id: str, body: TorQARequest, db: Session = Depends(get_db)) -> TorQAResponse:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question is empty")
    try:
        result = tor_qa_service.answer(
            db, project_id, body.question,
            company_profile=body.company_profile,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return TorQAResponse(
        answer=result["text"],
        model=result["model"],
        duration_sec=result["duration_sec"],
        input_tokens=result.get("input_tokens"),
        output_tokens=result.get("output_tokens"),
    )
