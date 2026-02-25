import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app.core.security import get_password_hash
from app.core.config import settings
import asyncpg

async def main():
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to: {db_url}")
    
    conn = await asyncpg.connect(db_url)
    
    # List tables
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print('Tables:', [t['tablename'] for t in tables])
    
    # Create admin user
    await conn.execute(
        """
        INSERT INTO "user" (id, email, hashed_password, is_active, is_superuser, role, created_at)
        VALUES (gen_random_uuid(), $1, $2, true, true, $3, now())
        ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password, role = EXCLUDED.role
        """,
        'admin@test.com', get_password_hash('AdminPass123!'), 'admin'
    )
    
    # Create reviewer user
    await conn.execute(
        """
        INSERT INTO "user" (id, email, hashed_password, is_active, is_superuser, role, created_at)
        VALUES (gen_random_uuid(), $1, $2, true, false, $3, now())
        ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password, role = EXCLUDED.role
        """,
        'reviewer@test.com', get_password_hash('TestPass123!'), 'reviewer'
    )
    
    result = await conn.fetch('SELECT email, role FROM "user"')
    print('Users in DB:', [(r['email'], r['role']) for r in result])
    await conn.close()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
