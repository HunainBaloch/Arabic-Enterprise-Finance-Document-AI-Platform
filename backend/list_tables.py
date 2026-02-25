import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from app.core.config import settings
import asyncpg

async def main():
    db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    print(f"Connecting to: {db_url}")
    conn = await asyncpg.connect(db_url)
    tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    print('Tables:', [t['tablename'] for t in tables])
    await conn.close()

asyncio.run(main())
