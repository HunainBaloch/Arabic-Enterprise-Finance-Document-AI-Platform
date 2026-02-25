import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def main():
    async with AsyncSessionLocal() as session:
        user = User(
            email="reviewer@idp.local",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            role="reviewer",
            is_superuser=False,
        )
        session.add(user)
        try:
            await session.commit()
            print("User created successfully: reviewer@idp.local / TestPass123!")
        except Exception as e:
            print("Failed to create user. May already exist.", e)

if __name__ == "__main__":
    asyncio.run(main())
