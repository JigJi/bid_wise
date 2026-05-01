from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, Text, ForeignKey, func
from app.core.database import Base


class ProcurementPlan(Base):
    """ประกาศแผนจัดซื้อจัดจ้าง — what an agency announced it intends to buy
    in a given fiscal year. Each plan has a `plan_id` (P-prefix), groups under
    a `mix_plan_id` (M-prefix), and lists 1..N planned procurements with
    expected announce-month + budget.

    e-GP exposes plan content via:
      getMixplanId?planId=P… → returns mix_plan_id
      process3.gprocurement.go.th/eGPProcure/secureds/RDBI0006/PRINT?mixPlanId=M…&templateTypeName=APLT&krut=true
        → JSON {templateData: <html>}, charset=tis-620 (must decode manually)

    `raw_html` keeps the source so we can re-parse if our extraction logic
    changes; structured fields (project_name, budget, expected_month) are
    extracted on insert.
    """

    __tablename__ = "procurement_plans"

    plan_id = Column(String(20), primary_key=True)               # P{12-13 digits}
    mix_plan_id = Column(String(20), index=True, nullable=True)  # M{12-13 digits}, set after getMixplanId

    dept_sub_id = Column(String(20), ForeignKey("departments.dept_sub_id"), index=True, nullable=True)
    budget_year = Column(String(4), index=True)                  # "2569"
    plan_announce_date = Column(Date, nullable=True)             # date the plan was published

    project_name = Column(Text, nullable=True)                   # ชื่อโครงการในแผน
    budget = Column(Numeric(20, 2), nullable=True)               # งบประมาณโครงการ (THB)
    expected_announce_month = Column(String(7), nullable=True)   # "MM/YYYY" Thai BE
    signed_by_name = Column(String(255), nullable=True)
    signed_by_position = Column(String(255), nullable=True)

    raw_html = Column(Text, nullable=True)                       # APLT templateData (utf-8 normalized)

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
