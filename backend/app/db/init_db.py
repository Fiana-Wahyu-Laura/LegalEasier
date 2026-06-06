import asyncio

from app.db.session import engine
from app.models.base import Base


async def init_db() -> None:
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())
