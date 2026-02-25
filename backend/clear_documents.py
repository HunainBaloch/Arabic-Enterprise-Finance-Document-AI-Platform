"""
Clear all documents and uploads. Requires .env with correct POSTGRES_* credentials.
For local runs, ensure POSTGRES_HOST=localhost and credentials match your Postgres.
"""
import asyncio
import os
import shutil
from sqlalchemy import delete
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentAuditLog
from app.core.config import settings

async def clear_database():
    print("Clearing database tables...")
    async with AsyncSessionLocal() as session:
        # Delete audit logs first due to foreign key constraints
        await session.execute(delete(DocumentAuditLog))
        await session.execute(delete(Document))
        await session.commit()
    print("Database tables cleared.")

def clear_uploads():
    uploads_dir = getattr(settings, "UPLOAD_DIR", "uploads")
    print(f"Clearing files in {uploads_dir}...")
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            file_path = os.path.join(uploads_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.is_dir(file_path):
                    shutil.rmtree(file_path)
                print(f"Deleted: {filename}")
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    print("Uploads folder cleared.")

async def main():
    await clear_database()
    clear_uploads()

if __name__ == "__main__":
    asyncio.run(main())
