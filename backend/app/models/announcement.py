from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, Numeric, func
from app.core.database import Base


class Announcement(Base):
    """One row per announcement event in a project's lifecycle. From greenBook:
    B0=ร่าง TOR, D0=ประกาศเชิญชวน, D1=ราคากลาง, BOQ=, price=สรุปการเสนอราคา,
    W0=ประกาศผู้ชนะ, plus cancellation/amendment variants. Each links to a
    PDF template via templateType when applicable."""

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, nullable=False)

    announce_type = Column(String(8), index=True, nullable=False)   # B0/D0/D1/W0/BOQ/price/...
    announce_type_desc = Column(String(160))                        # human label
    template_type = Column(String(8))                               # for infoApproveTemplate (D1, W13, ...)
    seq_no = Column(Integer, nullable=True)
    no = Column(String(8), nullable=True)                           # display rank

    announce_date = Column(Date, index=True, nullable=True)

    price_build = Column(Numeric(20, 2), nullable=True)             # only present on some types

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
