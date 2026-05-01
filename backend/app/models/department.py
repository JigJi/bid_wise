from sqlalchemy import Column, String, DateTime, func
from app.core.database import Base


class Department(Base):
    """หน่วยงานจัดซื้อจัดจ้าง — sub-department level (deptSubId is the unique key
    used by e-GP across project/plan records)."""

    __tablename__ = "departments"

    dept_sub_id = Column(String(20), primary_key=True)
    dept_id = Column(String(20), index=True)
    dept_sub_name = Column(String(255), nullable=False)

    # geography (from project detail when available)
    province_moi_id = Column(String(10), index=True)
    province_moi_name = Column(String(80))
    district_moi_id = Column(String(10))

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
