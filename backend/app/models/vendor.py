from sqlalchemy import Column, String, DateTime, Boolean, func
from app.core.database import Base


class Vendor(Base):
    """ผู้ประกอบการ (bidder/winner). Identified primarily by 13-digit Thai TIN
    (`receiveTin`). Older records can carry a partially-masked TIN for natural
    persons (last 4 digits as `XXXX`); we store whatever e-GP gives us and
    reconcile when a fully-unmasked record arrives.

    A small fraction of records have only a name + no TIN (very old data);
    those rows get NULL `tin` and we synthesize a stable hash key in
    `name_hash` for joins.
    """

    __tablename__ = "vendors"

    tin = Column(String(20), primary_key=True)  # 13 digits, or `<hash>:<name>` synthesized when TIN absent
    name_th = Column(String(255), nullable=False, index=True)
    name_normalized = Column(String(255), index=True)  # lower+trim+remove honorifics for fuzzy match

    # entity hints (filled later from cross-reference / classification)
    is_juridical = Column(Boolean, nullable=True)  # True = บริษัท/หจก/ห้าง; False = บุคคลธรรมดา
    is_sme = Column(Boolean, nullable=True)        # SME flag from e-GP UI badge
    is_made_in_thailand = Column(Boolean, nullable=True)  # MiT flag from e-GP UI badge
    is_tin_masked = Column(Boolean, default=False)        # True when TIN ends with XXXX

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
