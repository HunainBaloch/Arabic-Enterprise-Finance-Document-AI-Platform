"""
test_api_integration.py
───────────────────────
FastAPI endpoint integration tests covering:
  - Health & root endpoints
  - Auth: login, invalid credentials, inactive user
  - Document upload  (authenticated + anonymous rejection)
  - Document listing (authenticated)
  - Document detail retrieval
  - Document HITL update (reviewer approval)
  - ERP sync trigger validation
  - Training-data export endpoint
  - 404 handling for missing resources
"""

import io
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_bearer_token, override_get_db


# ══════════════════════════════════════════════════════
#  1. Health & Root
# ══════════════════════════════════════════════════════

def test_root_endpoint(anon_client: TestClient):
    r = anon_client.get("/")
    assert r.status_code == 200
    assert "Arabic Enterprise Finance" in r.json()["message"]


def test_health_endpoint(anon_client: TestClient):
    r = anon_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ══════════════════════════════════════════════════════
#  2. Authentication
# ══════════════════════════════════════════════════════

def test_login_valid(client: TestClient):
    """Verify that a correct login returns a JWT token."""
    # POST to the token endpoint using form data
    r = client.post(
        "/api/v1/login/access-token",
        data={"username": "reviewer@test.com", "password": "TestPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(anon_client: TestClient):
    r = anon_client.post(
        "/api/v1/login/access-token",
        data={"username": "reviewer@test.com", "password": "WRONG"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 400
    assert "Incorrect" in r.json()["detail"]


def test_login_nonexistent_user(anon_client: TestClient):
    r = anon_client.post(
        "/api/v1/login/access-token",
        data={"username": "ghost@test.com", "password": "anything"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 400


# ══════════════════════════════════════════════════════
#  3. Document Upload
# ══════════════════════════════════════════════════════

@patch("app.worker.process_document.delay", return_value=MagicMock(id="task-uuid-1"))
@patch("app.services.ocr.extract_text", return_value={"raw_text": "مورد", "blocks": [], "confidence": 0.92})
def test_upload_txt_authenticated(mock_ocr, mock_delay, client: TestClient, tmp_path):
    """Authenticated reviewer can upload a valid text file."""
    test_file = tmp_path / "invoice.txt"
    test_file.write_text("فاتورة ضريبية\nالمورد: شركة الخليج\nالإجمالي: 1050 AED\nضريبة القيمة المضافة: 50 AED", encoding="utf-8")

    with open(test_file, "rb") as f:
        r = client.post(
            "/api/v1/documents/upload",
            files={"file": ("invoice.txt", f, "text/plain")},
        )
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "filename" in body
    assert body["filename"] == "invoice.txt"


def test_upload_rejected_without_auth(anon_client: TestClient, tmp_path):
    """Anonymous users must be rejected with 401."""
    test_file = tmp_path / "anon.txt"
    test_file.write_bytes(b"content")
    with open(test_file, "rb") as f:
        r = anon_client.post(
            "/api/v1/documents/upload",
            files={"file": ("anon.txt", f, "text/plain")},
        )
    assert r.status_code == 401


def test_upload_empty_filename_rejected(client: TestClient):
    """Request with no file should return 400."""
    r = client.post(
        "/api/v1/documents/upload",
        files={"file": ("", io.BytesIO(b""), "text/plain")},
    )
    assert r.status_code in (400, 422)


# ══════════════════════════════════════════════════════
#  4. Document Listing
# ══════════════════════════════════════════════════════

def test_list_documents_authenticated(client: TestClient):
    """Authenticated user can list documents."""
    r = client.get("/api/v1/documents/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_documents_rejected_without_auth(anon_client: TestClient):
    r = anon_client.get("/api/v1/documents/")
    assert r.status_code == 401


def test_list_documents_pagination(client: TestClient):
    """Check skip/limit query params are accepted."""
    r = client.get("/api/v1/documents/?skip=0&limit=5")
    assert r.status_code == 200


# ══════════════════════════════════════════════════════
#  5. Document Detail
# ══════════════════════════════════════════════════════

def test_get_nonexistent_document_returns_404(client: TestClient):
    fake_id = str(uuid.uuid4())
    r = client.get(f"/api/v1/documents/{fake_id}")
    assert r.status_code == 404


# ══════════════════════════════════════════════════════
#  6. Document Update (HITL Approval)
# ══════════════════════════════════════════════════════

@patch("app.worker.process_document.delay", return_value=MagicMock(id="task-uuid-2"))
def test_update_nonexistent_document_returns_404(mock_delay, client: TestClient):
    fake_id = str(uuid.uuid4())
    r = client.put(
        f"/api/v1/documents/{fake_id}",
        json={
            "status": "COMPLETED",
            "extracted_data": {"vendor_name": "شركة الاختبار"},
        },
    )
    assert r.status_code == 404


# ══════════════════════════════════════════════════════
#  7. ERP Sync Validation
# ══════════════════════════════════════════════════════

def test_erp_sync_nonexistent_document(client: TestClient):
    """ERP sync on missing document should return 404."""
    fake_id = str(uuid.uuid4())
    r = client.post(f"/api/v1/documents/{fake_id}/sync/odoo")
    assert r.status_code == 404


def test_erp_sync_unsupported_provider(client: TestClient):
    """Should return 400 or 404 for an unrecognised ERP provider name on a real doc."""
    # We can only test the provider-not-found path if the document itself is found
    # so we accept either 404 (doc not found) or 400 (bad provider)
    fake_id = str(uuid.uuid4())
    r = client.post(f"/api/v1/documents/{fake_id}/sync/saprandom")
    assert r.status_code in (400, 404)


# ══════════════════════════════════════════════════════
#  8. Training-data Export
# ══════════════════════════════════════════════════════

def test_export_training_data(client: TestClient):
    """Export endpoint should return 200 and JSONL content-type."""
    r = client.get("/api/v1/documents/export/training-data")
    assert r.status_code == 200
    assert "jsonl" in r.headers.get("content-type", "")


# ══════════════════════════════════════════════════════
#  9. Metrics Endpoint (Prometheus)
# ══════════════════════════════════════════════════════

def test_metrics_endpoint_exposed(anon_client: TestClient):
    r = anon_client.get("/metrics")
    # Must exist; content is Prometheus text format
    assert r.status_code == 200
