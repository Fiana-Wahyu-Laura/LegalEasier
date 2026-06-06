import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.base import Base
import app.models  # load all models

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("SUCCESS")

if __name__ == "__main__":
    asyncio.run(main())
