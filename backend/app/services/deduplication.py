"""
deduplication.py
────────────────
Detects duplicate invoice uploads using a two-pass strategy:

  Pass 1 — Byte-level MD5 hash (identical file re-upload detection).
  Pass 2 — Semantic fuzzy match: same vendor + date + total_amount triple
            across all COMPLETED documents in the database.

The fuzzy query uses Python-side filtering to stay compatible with both
PostgreSQL (production JSON/JSONB) and SQLite (test in-memory mode).
"""

import hashlib
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)


async def check_hash_duplicate(
    db: AsyncSession,
    document: Document
) -> Optional[Document]:
    """
    Pass 1: Searches for a duplicate invoice by exactly matching the 
    MD5 file_hash against all COMPLETED documents in the database.
    """
    if not document.file_hash:
        return None

    query = select(Document).where(
        Document.id != document.id,
        Document.file_hash == document.file_hash,
        Document.status == DocumentStatus.COMPLETED
    )
    result = await db.execute(query)
    candidate = result.scalars().first()
    
    if candidate:
        logger.warning(
            f"Pass 1 Duplicate (Hash) detected: document {document.id} matches "
            f"completed document {candidate.id}"
        )
        return candidate
        
    return None


def compute_document_hash(file_path: str) -> str:
    """
    Computes the MD5 hex digest of a file using 4 KB streaming chunks.
    Used for byte-identical duplicate detection.
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


async def find_duplicate(
    db: AsyncSession,
    document: Document,
    structured_data: Dict[str, Any],
) -> Optional[Document]:
    """
    Pass 2: Searches for a semantically duplicate invoice by matching the
    (vendor_name, invoice_date, total_amount) triple against all
    COMPLETED documents in the database.

    Returns the first matching Document or None.
    """
    vendor_name  = structured_data.get("vendor_name")
    invoice_date = structured_data.get("invoice_date")
    total_amount = structured_data.get("total_amount")

    # Guard: skip fuzzy check if any required field is absent
    if not (vendor_name and invoice_date and total_amount is not None):
        logger.debug("Deduplication skipped — missing extracted fields.")
        return None

    # Retrieve all COMPLETED documents (excluding the current one) and filter
    # the JSON payload in Python.  This keeps the query portable across engines.
    query = select(Document).where(
        Document.id != document.id,
        Document.status == DocumentStatus.COMPLETED,
        Document.extracted_data.is_not(None),
    )
    result = await db.execute(query)
    candidates = result.scalars().all()

    for candidate in candidates:
        llm_out = (candidate.extracted_data or {}).get("llm_output", {})
        if (
            llm_out.get("vendor_name") == str(vendor_name)
            and llm_out.get("invoice_date") == str(invoice_date)
            and str(llm_out.get("total_amount", "")) == str(total_amount)
        ):
            logger.warning(
                f"Pass 2 Duplicate (Semantic) detected: document {document.id} matches "
                f"completed document {candidate.id}"
            )
            return candidate

    return None
