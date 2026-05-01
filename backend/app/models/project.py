from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, Text, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class Project(Base):
    """e-GP project (`projectId`) — the unit that everything else hangs off of.

    Source of truth: getProcurementDetail JSON; bidder list comes from
    getProcureResult; the announcement lifecycle comes from greenBook (B0,
    D0, D1, BOQ, price, W0, …); attachments come from infoProcureDocAnnounZip.
    """

    __tablename__ = "projects"

    project_id = Column(String(20), primary_key=True)            # 11–13 digits
    project_name = Column(Text, nullable=False)

    # link upward to plan (reverse-lookup only via getMixplanId for now)
    plan_id = Column(String(20), ForeignKey("procurement_plans.plan_id"), index=True, nullable=True)

    # owning department
    dept_sub_id = Column(String(20), ForeignKey("departments.dept_sub_id"), index=True, nullable=True)

    # method / type / step (codes)
    method_id = Column(String(4), index=True)        # 16=e-bidding, 19=เฉพาะเจาะจง, 02=สอบราคา, ...
    type_id = Column(String(4))                      # ประเภทการจัดหา
    type_project = Column(String(4))                 # 9, etc.
    step_id = Column(String(8), index=True)          # M03, W03, X01, I03, ...
    project_status = Column(String(8))               # A=active

    # money
    project_money = Column(Numeric(20, 2))           # วงเงินงบประมาณ
    price_build = Column(Numeric(20, 2))             # ราคากลาง (rolled-up; line items in D1 PDF)
    price_agree = Column(Numeric(20, 2))             # มูลค่าที่จัดหาได้ (final contract; mirrors winner.priceAgree)
    project_cost = Column(String(2))                 # C=เกณฑ์ราคา, Q=เกณฑ์คุณภาพ+ราคา
    project_cost_name = Column(String(80))
    min_quality_score = Column(Numeric(5, 2), nullable=True)

    # dates
    announce_date = Column(DateTime(timezone=True), index=True)   # announce date (ประกาศ)
    announce_winner_date = Column(DateTime(timezone=True), nullable=True)
    report_date = Column(DateTime(timezone=True), nullable=True)
    deliver_day = Column(Integer, nullable=True)                  # ระยะเวลาส่งมอบ

    # geography (denormalized from department snapshot at the time of project insert)
    province_moi_id = Column(String(10), index=True, nullable=True)
    province_moi_name = Column(String(80), nullable=True)

    # raw payloads — keep so we can re-parse without re-fetching
    raw_detail = Column(JSONB, nullable=True)            # getProcurementDetail full body
    raw_procure_result = Column(JSONB, nullable=True)    # getProcureResult full body
    raw_greenbook = Column(JSONB, nullable=True)         # greenBook(mode=LINK) full body

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
