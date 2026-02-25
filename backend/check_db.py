import asyncio
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from sqlalchemy.future import select

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Document).order_by(Document.created_at.desc()))
        doc = result.scalars().first()
        if doc:
            print(f"File: {doc.filename}")
            print(f"Status: {doc.status}")
            print(f"Confidence: {doc.confidence_score}")
        else:
            print("No documents found")

if __name__ == "__main__":
    asyncio.run(main())
