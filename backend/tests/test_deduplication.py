"""
test_deduplication.py
─────────────────────
Unit tests for app/services/deduplication.py covering:
  - MD5 hash computation for identical / different files
  - find_duplicate: returns None when no match exists
  - find_duplicate: detects fuzzy triple-match (vendor + date + amount)
  - Edge cases: missing fields → skips fuzzy query safely
"""

import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.deduplication import compute_document_hash, find_duplicate
from app.models.document import Document, DocumentStatus


# ══════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════

def _make_document(
    doc_id: str = None,
    vendor: str = "شركة الخليج",
    date: str = "2025-01-15",
    total: float = 1050.0,
) -> Document:
    doc = Document()
    doc.id = doc_id or str(uuid.uuid4())
    doc.filename = "invoice.pdf"
    doc.original_path = "/uploads/invoice.pdf"
    doc.mime_type = "application/pdf"
    doc.file_size = 102400
    doc.status = DocumentStatus.COMPLETED
    doc.extracted_data = {
        "llm_output": {
            "vendor_name": vendor,
            "invoice_date": date,
            "total_amount": total,
        }
    }
    doc.confidence_score = 0.97
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


def _make_structured_data(
    vendor: str = "شركة الخليج",
    date: str = "2025-01-15",
    total: float = 1050.0,
) -> Dict[str, Any]:
    return {"vendor_name": vendor, "invoice_date": date, "total_amount": total}


# ══════════════════════════════════════════════════════
#  1. compute_document_hash
# ══════════════════════════════════════════════════════

def test_hash_identical_files():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(b"PDF content equivalent to invoice data")
        tmp_path = f.name
    try:
        hash1 = compute_document_hash(tmp_path)
        hash2 = compute_document_hash(tmp_path)
        assert hash1 == hash2, "Same file must produce the same MD5 hash"
        assert len(hash1) == 32, "MD5 digest must be 32 hex chars"
    finally:
        os.unlink(tmp_path)


def test_hash_different_files_produce_different_digests():
    with tempfile.NamedTemporaryFile(delete=False) as f1, \
         tempfile.NamedTemporaryFile(delete=False) as f2:
        f1.write(b"Invoice A content")
        f2.write(b"Invoice B different content")
        p1, p2 = f1.name, f2.name
    try:
        assert compute_document_hash(p1) != compute_document_hash(p2)
    finally:
        os.unlink(p1)
        os.unlink(p2)


def test_hash_empty_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"")
        tmp_path = f.name
    try:
        h = compute_document_hash(tmp_path)
        # MD5 of empty string is known
        assert h == hashlib.md5(b"").hexdigest()
    finally:
        os.unlink(tmp_path)


def test_hash_large_file_chunks_correctly():
    """File larger than 4096-byte chunk size is correctly hashed."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        content = b"A" * 50_000
        f.write(content)
        tmp_path = f.name
    try:
        h = compute_document_hash(tmp_path)
        expected = hashlib.md5(content).hexdigest()
        assert h == expected
    finally:
        os.unlink(tmp_path)


# ══════════════════════════════════════════════════════
#  2. find_duplicate — no match
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_find_duplicate_returns_none_when_no_match():
    """When DB returns no matching candidates, find_duplicate should return None."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # empty candidate list
    mock_session.execute = AsyncMock(return_value=mock_result)

    incoming_doc = _make_document(doc_id=str(uuid.uuid4()))
    structured = _make_structured_data(vendor="شركة جديدة", date="2024-03-01", total=5000.0)

    result = await find_duplicate(mock_session, incoming_doc, structured)
    assert result is None


# ══════════════════════════════════════════════════════
#  3. find_duplicate — duplicate detected
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_find_duplicate_returns_existing_document():
    """When DB returns a matching document in candidates, it should be returned."""
    existing_doc = _make_document(doc_id=str(uuid.uuid4()))
    # The real find_duplicate uses scalars().all() and filters in Python
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_doc]
    mock_session.execute = AsyncMock(return_value=mock_result)

    incoming_doc = _make_document(doc_id=str(uuid.uuid4()))
    # structured_data with the same key values as the existing_doc's llm_output
    structured = _make_structured_data()  # vendor="شركة الخليج", date="2025-01-15", total=1050.0

    result = await find_duplicate(mock_session, incoming_doc, structured)
    assert result is not None
    assert result.id == existing_doc.id


# ══════════════════════════════════════════════════════
#  4. find_duplicate — missing fields skips fuzzy query
# ══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_find_duplicate_skips_query_when_vendor_missing():
    """If vendor_name is absent, the fuzzy query should NOT be executed."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()  # should NOT be called

    incoming_doc = _make_document()
    structured = {"vendor_name": None, "invoice_date": "2025-01-15", "total_amount": 1050.0}

    result = await find_duplicate(mock_session, incoming_doc, structured)
    assert result is None
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_find_duplicate_skips_query_when_date_missing():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    incoming_doc = _make_document()
    structured = {"vendor_name": "شركة الخليج", "invoice_date": None, "total_amount": 1050.0}

    result = await find_duplicate(mock_session, incoming_doc, structured)
    assert result is None
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_find_duplicate_skips_query_when_amount_missing():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    incoming_doc = _make_document()
    structured = {"vendor_name": "شركة الخليج", "invoice_date": "2025-01-15", "total_amount": None}

    result = await find_duplicate(mock_session, incoming_doc, structured)
    assert result is None
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_find_duplicate_empty_structured_data():
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    incoming_doc = _make_document()
    result = await find_duplicate(mock_session, incoming_doc, {})
    assert result is None
    mock_session.execute.assert_not_called()


# ══════════════════════════════════════════════════════
#  5. Integration of hash + find_duplicate logic
# ══════════════════════════════════════════════════════

def test_different_content_different_hash_proves_uniqueness():
    """Proves that two invoices with different content won't collide on hash."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as a, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as b:
        a.write(b"Invoice vendor A total 1050")
        b.write(b"Invoice vendor B total 9999")
        pa, pb = a.name, b.name
    try:
        assert compute_document_hash(pa) != compute_document_hash(pb)
    finally:
        os.unlink(pa)
        os.unlink(pb)
