from sqlalchemy import Column, String, Integer, Numeric, DateTime, Boolean, ForeignKey, Text, func
from app.core.database import Base


class Bidder(Base):
    """One row per (project × consider-group × bidder). Source: getProcureResult.
    A project that splits its evaluation into multiple `considerDesc` groups
    (e.g. ซื้อข้าว 2 รุ่น) can have multiple winner rows."""

    __tablename__ = "bidders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, nullable=False)
    vendor_tin = Column(String(20), ForeignKey("vendors.tin"), index=True, nullable=False)

    consider_desc = Column(Text, nullable=True)                     # รายการพิจารณา
    consider_seq = Column(Integer, nullable=True)                   # 1..N within project

    receive_name_th = Column(String(255), nullable=False)           # snapshot at bid time (vendor name may change later)
    price_proposal = Column(Numeric(20, 2), nullable=True)          # ราคาที่เสนอ
    price_agree = Column(Numeric(20, 2), nullable=True)             # ราคาตกลง (only winner has this)
    result_flag = Column(String(2), index=True)                     # P=ผ่าน, N=ไม่ผ่าน
    score_type_id = Column(String(8), nullable=True)
    is_winner = Column(Boolean, default=False, index=True)          # derived: priceAgree IS NOT NULL

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())


class JointVentureMember(Base):
    """When a bidder is a JV/Consortium, members come in
    `jointVentureAndConsortiumsResponseList` of the procureResult bidder."""

    __tablename__ = "jv_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bidder_id = Column(Integer, ForeignKey("bidders.id"), index=True, nullable=False)
    member_tin = Column(String(20), ForeignKey("vendors.tin"), index=True, nullable=True)
    member_name_th = Column(String(255), nullable=False)
    member_role = Column(String(40), nullable=True)
