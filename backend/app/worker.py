import asyncio
import logging
from sqlalchemy.future import select
from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.services.ocr import extract_text
from app.services.nlp import extract_financial_entities

logger = logging.getLogger(__name__)

async def process_document_async(document_id: str):
    async with AsyncSessionLocal() as session:
        # Fetch document
        result = await session.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            logger.error(f"Worker could not find document {document_id}")
            return
            
        try:
            # 1. OCR Extraction Phase
            document.status = DocumentStatus.OCR_EXTRACTION
            await session.commit()
            
            # Using run_in_executor since OCR is synchronous
            ocr_result = await asyncio.to_thread(extract_text, document.original_path)
            
            # 2. NLP Output Entity Phase
            document.status = DocumentStatus.NLP_EXTRACTION
            await session.commit()
            
            nlp_entities = await asyncio.to_thread(extract_financial_entities, ocr_result["raw_text"])
            
            # Compile intermediate raw data
            raw_data = {
                "raw_text": ocr_result["raw_text"],
                "blocks": ocr_result["blocks"],
                "extracted_entities": nlp_entities
            }
            
            # 3. LLM JSON Structuring & Validation Phase
            from app.services.llm import generate_json_validation
            from app.services.validation import validate_uae_vat
            from app.services.deduplication import find_duplicate
            
            document.status = DocumentStatus.LLM_VALIDATION
            await session.commit()
            
            # Generate clean JSON
            final_json = await generate_json_validation(ocr_result["raw_text"], nlp_entities)
            
            # Apply UAE VAT Math Check
            vat_check = validate_uae_vat(
                final_json.get("total_amount"), 
                final_json.get("vat_amount")
            )
            final_json["vat_validation"] = vat_check
            
            # Apply Duplicate Detection
            duplicate = await find_duplicate(session, document, final_json)
            final_json["is_duplicate"] = duplicate is not None
            if duplicate:
                final_json["duplicate_of_id"] = str(duplicate.id)
                document.status = DocumentStatus.FAILED
            
            # Attach final packaged payload
            document.extracted_data = {
                "llm_output": final_json,
                "raw_extraction_cache": raw_data
            }
            
            document.confidence_score = ocr_result["confidence"]
            
            # Routing logic to HITL or COMPLETED phase
            # If not a duplicate and confident and VAT matches:
            if not duplicate:
                if document.confidence_score >= 0.95 and vat_check.get("is_valid"):
                    document.status = DocumentStatus.COMPLETED
                else:
                    document.status = DocumentStatus.HITL_REVIEW
                
            await session.commit()
            logger.info(f"Successfully processed document {document_id}")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            document.status = DocumentStatus.FAILED
            await session.commit()

@celery_app.task(name="app.worker.process_document")
def process_document(document_id: str):
    # Celery tasks are synchronous; run async code in an isolated event loop
    asyncio.run(process_document_async(document_id))
    return f"Processed {document_id}"

@celery_app.task(
    name="app.worker.erp_sync_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 5}
)
def erp_sync_task(self, document_id: str, provider: str, extracted_data: dict):
    from app.services.erp.factory import get_erp_connector
    logger.info(f"Starting Celery ERP Sync task for {document_id} -> {provider}")
    
    connector = get_erp_connector(provider)
    if not connector:
        raise ValueError(f"Provider {provider} not supported.")
        
    result = connector.sync_invoice(document_id, extracted_data)
    return result
