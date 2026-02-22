from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.document import DocumentStatus

class DocumentBase(BaseModel):
    filename: str
    original_path: str
    mime_type: str
    file_size: float
    status: DocumentStatus = DocumentStatus.UPLOADED

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: UUID4
    uploader_id: Optional[UUID4] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
