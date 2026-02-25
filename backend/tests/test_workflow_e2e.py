import pytest
import os
from unittest.mock import patch
from app.models.document import DocumentStatus
# from app.core.celery_app import celery_app
from app.worker import process_document_async

from tests.conftest import TestingSessionLocal

# Do NOT use celery eager mode as it deadlocks with FastAPI TestClient async loops.
# We will mock `process_document.delay` and manually call `await process_document_async()`
# We must patch AsyncSessionLocal so the worker uses the test SQLite DB (not production Postgres)


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a temporary dummy PDF file."""
    file_path = tmp_path / "dummy_invoice.pdf"
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF content\n")
    return file_path

@pytest.mark.asyncio
async def test_successful_document_processing(client, sample_pdf, db_session):
    """
    Test Case 1: End-to-End Successful Processing & Completed Status
    - Uploads document
    - Mocks the OCR and NLP services
    - Manually runs process_document_async
    - Verifies document completed successfully
    """
    with patch('app.worker.AsyncSessionLocal', TestingSessionLocal), \
         patch('app.worker.extract_text') as mock_ocr, \
         patch('app.worker.extract_financial_entities') as mock_nlp, \
         patch('app.worker.process_document.delay') as mock_celery_delay:
         
        mock_ocr.return_value = {
            "raw_text": "Dummy High Confidence Invoice Text",
            "blocks": [],
            "confidence": 0.98
        }
        mock_nlp.return_value = {
            "total_amount": 105.00,
            "vat_amount": 5.00,
            "vendor_name": "Test Vendor"
        }
        
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("dummy_invoice.pdf", f, "application/pdf")}
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "dummy_invoice.pdf"
        assert data["status"] == DocumentStatus.PREPROCESSING.value
        
        document_id = data["id"]
        
        # Verify the endpoint tried to schedule the celery task
        mock_celery_delay.assert_called_once_with(document_id)
        
        # Manually run the worker logic (as an async function) to avoid thread loop deadlocks
        await process_document_async(document_id)
        
        # Check DB status after processing
        response_get = client.get(f"/api/v1/documents/{document_id}")
        assert response_get.status_code == 200
        doc_data = response_get.json()
        
        assert doc_data["status"] in [DocumentStatus.COMPLETED.value, DocumentStatus.HITL_REVIEW.value]
        assert "llm_output" in doc_data.get("extracted_data", {})

@pytest.mark.asyncio
async def test_low_confidence_routes_to_hitl(client, sample_pdf):
    """
    Test Case 2: Document processing routed to Human-In-The-Loop (HITL) due to low OCR confidence
    """
    with patch('app.worker.AsyncSessionLocal', TestingSessionLocal), \
         patch('app.worker.extract_text') as mock_ocr, \
         patch('app.worker.extract_financial_entities') as mock_nlp, \
         patch('app.worker.process_document.delay'):
         
        mock_ocr.return_value = {
            "raw_text": "Blurry Invoice",
            "blocks": [],
            "confidence": 0.85
        }
        mock_nlp.return_value = {}
        
        with open(sample_pdf, "rb") as f:
            response = client.post("/api/v1/documents/upload", files={"file": ("blurry.pdf", f, "application/pdf")})
            
        doc_id = response.json()['id']
        await process_document_async(doc_id)
        
        doc_data = client.get(f"/api/v1/documents/{doc_id}").json()
        assert doc_data["status"] == DocumentStatus.HITL_REVIEW.value
        assert doc_data["confidence_score"] == 0.85

@pytest.mark.asyncio
async def test_worker_catches_exception_and_fails_document(client, sample_pdf):
    """
    Test Case 4: Error During Processing (e.g., OCR Failure)
    """
    with patch('app.worker.AsyncSessionLocal', TestingSessionLocal), \
         patch('app.worker.extract_text', side_effect=Exception("OCR Engine Crash")), \
         patch('app.worker.process_document.delay'):
        
        with open(sample_pdf, "rb") as f:
            response = client.post("/api/v1/documents/upload", files={"file": ("error.pdf", f, "application/pdf")})
            
        doc_id = response.json()['id']
        await process_document_async(doc_id)
        
        doc_data = client.get(f"/api/v1/documents/{doc_id}").json()
        assert doc_data["status"] == DocumentStatus.FAILED.value

@pytest.mark.asyncio
async def test_invalid_upload_no_file(client):
    """
    Test Case 5: Invalid File Upload
    """
    response = client.post("/api/v1/documents/upload", files={})
    assert response.status_code == 422 

@pytest.mark.asyncio
async def test_duplicate_document_detection(client, sample_pdf):
    """
    Test Case 3: Duplicate Document Detection
    """
    with patch('app.worker.AsyncSessionLocal', TestingSessionLocal), \
         patch('app.worker.extract_text') as mock_ocr, \
         patch('app.worker.extract_financial_entities') as mock_nlp, \
         patch('app.services.deduplication.find_duplicate') as mock_dedup, \
         patch('app.worker.process_document.delay'):
         
        mock_ocr.return_value = {"raw_text": "Dup", "blocks": [], "confidence": 0.99}
        mock_nlp.return_value = {"total_amount": 100.0}
        
        class DummyDup:
            id = "00000000-0000-0000-0000-000000000000"
        mock_dedup.return_value = DummyDup()
        
        with open(sample_pdf, "rb") as f:
            response = client.post("/api/v1/documents/upload", files={"file": ("duplicate.pdf", f, "application/pdf")})
            
        doc_id = response.json()['id']
        await process_document_async(doc_id)
        
        doc_data = client.get(f"/api/v1/documents/{doc_id}").json()
        
        assert doc_data["status"] == DocumentStatus.FAILED.value
        assert doc_data["extracted_data"]["llm_output"]["is_duplicate"] is True
        assert doc_data["extracted_data"]["llm_output"]["duplicate_of_id"] == "00000000-0000-0000-0000-000000000000"
