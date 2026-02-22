import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base
from datetime import datetime, timezone
import enum

class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    OCR_EXTRACTION = "ocr_extraction"
    NLP_EXTRACTION = "nlp_extraction"
    LLM_VALIDATION = "llm_validation"
    HITL_REVIEW = "hitl_review"
    COMPLETED = "completed"
    FAILED = "failed"

class Document(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    file_size = Column(Float, nullable=False)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True) # made true for dev
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    extracted_data = Column(JSON, nullable=True) # Final approved JSON
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class DocumentAuditLog(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
