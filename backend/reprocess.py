"""
reprocess.py  —  manually trigger process_document_async on all PREPROCESSING docs
Run with: python reprocess.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from sqlalchemy.future import select

# Important: import the fixed worker
from app.worker import process_document_async


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document).where(Document.status == DocumentStatus.PREPROCESSING)
        )
        stuck_docs = result.scalars().all()
        print(f"Found {len(stuck_docs)} document(s) stuck in PREPROCESSING")

        if not stuck_docs:
            print("Nothing to reprocess.")
            return

        # Process just the first one as a test
        doc = stuck_docs[0]
        print(f"\nProcessing document: {doc.filename}  id={doc.id}")
        print("Starting pipeline...")

    try:
        await process_document_async(str(doc.id))
        print("Pipeline completed!")
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()

    # Check result
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).where(Document.id == doc.id))
        updated = result.scalar_one_or_none()
        if updated:
            print(f"\nFinal status: {updated.status}")
            print(f"Confidence score: {updated.confidence_score}")
            if updated.extracted_data:
                llm = updated.extracted_data.get("llm_output", {})
                print(f"Extracted vendor: {llm.get('vendor_name', 'N/A')}")
                print(f"Extracted total: {llm.get('total_amount', 'N/A')}")
                print(f"VAT valid: {llm.get('vat_validation', {}).get('is_valid', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
