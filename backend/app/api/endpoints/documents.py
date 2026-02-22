import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.document import DocumentResponse, DocumentCreate
from app.models.document import Document, DocumentStatus, DocumentAuditLog
from app.models.user import User
from app.core.config import settings
from app.api.deps import get_current_user, get_current_active_user, get_current_active_reviewer
from typing import List

router = APIRouter()

UPLOAD_DIR = getattr(settings, "UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save the file to disk
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
        
    file_size = os.path.getsize(file_path)
    mime = file.content_type or "application/octet-stream"

    # Create DB Record
    db_document = Document(
        filename=file.filename,
        original_path=file_path,
        mime_type=mime,
        file_size=file_size,
        status=DocumentStatus.PREPROCESSING
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Trigger background Celery task
    from app.worker import process_document
    process_document.delay(str(db_document.id))
    
    return db_document

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.future import select
    # Order by newest first
    result = await db.execute(select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit))
    documents = result.scalars().all()
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.future import select
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from sqlalchemy.future import select
    from fastapi.responses import FileResponse
    
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document or not os.path.exists(document.original_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(path=document.original_path, media_type=document.mime_type, filename=document.filename)

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str, 
    update_data: dict, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_reviewer)
):
    from sqlalchemy.future import select
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if "status" in update_data:
        document.status = update_data["status"]
        
    if "extracted_data" in update_data:
        # Create an audit log for the change
        audit_log = DocumentAuditLog(
            document_id=document.id,
            user_id=current_user.id,
            previous_state=document.extracted_data,
            new_state=update_data["extracted_data"]
        )
        db.add(audit_log)
        document.extracted_data = update_data["extracted_data"]
        
    await db.commit()
    await db.refresh(document)
    
    return document

@router.post("/{document_id}/sync/{provider}")
async def sync_to_erp(
    document_id: str, 
    provider: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_reviewer)
):
    from sqlalchemy.future import select
    from app.services.erp.factory import get_erp_connector
    
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document must be COMPLETED before syncing to ERP")
        
    extracted = document.extracted_data.get("llm_output")
    if not extracted:
        raise HTTPException(status_code=400, detail="Document does not have structured data to sync")
        
    connector = get_erp_connector(provider)
    if not connector:
        raise HTTPException(status_code=400, detail=f"ERP Provider {provider} not supported or not configured")
        
    # Trigger robust celery task instead of synchronous wait
    from app.worker import erp_sync_task
    task = erp_sync_task.delay(str(document.id), provider, extracted)
    
    return {
        "success": True,
        "message": f"ERP sync triggered. Task ID: {task.id}"
    }

@router.get("/export/training-data")
async def export_training_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_reviewer)
):
    """
    Exports COMPLETED documents into a JSONL structure for NLP/LLM fine-tuning.
    """
    from sqlalchemy.future import select
    from fastapi.responses import PlainTextResponse
    import json
    
    result = await db.execute(select(Document).where(Document.status == DocumentStatus.COMPLETED))
    documents = result.scalars().all()
    
    lines = []
    for doc in documents:
        if not doc.extracted_data:
            continue
            
        raw = doc.extracted_data.get("raw_extraction_cache", {}).get("raw_text", "")
        # Get the human-corrected final output
        final_json = doc.extracted_data.get("llm_output", {})
        
        # Build a prompt-completion pair suitable for instruct tuning
        pair = {
            "instruction": "Extract the financial entities from the following invoice as JSON.",
            "input": raw,
            "output": json.dumps(final_json, ensure_ascii=False)
        }
        lines.append(json.dumps(pair, ensure_ascii=False))
        
    jsonl_content = "\n".join(lines)
    return PlainTextResponse(content=jsonl_content, media_type="application/jsonl")
