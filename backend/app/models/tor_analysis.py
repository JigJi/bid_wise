from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class TorAnalysis(Base):
    """Structured extraction of a TOR / D1 PDF via LLM.

    Source: `pdf_templates.extracted_text` rows where template_type='D1' (or W-variants).
    Each project should have one row per (model, prompt_version) combination — keeping
    history lets us re-run with a better prompt and compare outputs without losing
    the previous extraction.
    """

    __tablename__ = "tor_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, nullable=False)
    pdf_template_id = Column(Integer, ForeignKey("pdf_templates.id"), index=True, nullable=True)

    prompt_version = Column(String(16), nullable=False, default="v1")
    model_name = Column(String(64), nullable=False)
    status = Column(String(16), default="PENDING", index=True)
    # PENDING / PROCESSING / COMPLETED / FAILED

    # the structured extraction — Pydantic-validated shape; freeform JSONB lets us
    # evolve schema without alembic churn while we iterate
    summary = Column(JSONB, nullable=True)

    # raw + diagnostic fields
    raw_response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), nullable=True)
    duration_sec = Column(Numeric(8, 2), nullable=True)

    first_run_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
