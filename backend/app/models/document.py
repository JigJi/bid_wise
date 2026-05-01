from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func
from app.core.database import Base


class DocumentZip(Base):
    """The announcement ZIP fetched via:
      infoProcureDocAnnounZip?projectId={pid} → returns zipId
      egp-upload-service/v1/downloadFileTest?fileId={zipId} → binary ZIP

    Local file is kept under data/zips/{project_id}.zip.
    """

    __tablename__ = "document_zips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, unique=True, nullable=False)

    zip_id = Column(String(64), nullable=False)                  # 32-hex
    build_name1 = Column(String(255), nullable=True)             # e.g. {pid}_{ddmmyyyy}.zip
    build_name2 = Column(String(64), nullable=True)              # UUID alt handle

    file_path = Column(String(255), nullable=True)               # local path
    size_bytes = Column(Integer, nullable=True)
    sha1 = Column(String(40), nullable=True, index=True)
    n_entries = Column(Integer, nullable=True)

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentFile(Base):
    """Files extracted from a DocumentZip (TOR PDFs, bond templates, etc.)."""

    __tablename__ = "document_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_id = Column(Integer, ForeignKey("document_zips.id"), index=True, nullable=False)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, nullable=False)

    name = Column(String(255), nullable=False)                   # original entry name
    kind = Column(String(20), index=True)                        # tor / attach_tor / annoudoc / contract / bond / quotation / xlsx_template / other
    size_bytes = Column(Integer, nullable=True)
    sha1 = Column(String(40), nullable=True, index=True)
    file_path = Column(String(255), nullable=True)               # extracted local path

    extracted_text = Column(Text, nullable=True)                 # for PDFs we parsed (defer OCR)
    text_extract_status = Column(String(16), default="pending")  # pending/done/needs_ocr/failed


class PdfTemplate(Base):
    """The single-PDF templates rendered server-side via:
      infoApproveTemplate?projectId={pid}&templateType={D1|W13|...} → templateId
      view-pdf-file?templateId={uuid} → binary PDF
    """

    __tablename__ = "pdf_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(20), ForeignKey("projects.project_id"), index=True, nullable=False)

    template_type = Column(String(8), nullable=False)            # D1, W13, ...
    template_id = Column(String(64), nullable=False)             # UUID returned by infoApproveTemplate
    template_name = Column(String(255), nullable=True)           # dwnt_..., dpbt_...

    file_path = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    sha1 = Column(String(40), nullable=True, index=True)

    extracted_text = Column(Text, nullable=True)                 # pdfplumber output

    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())
