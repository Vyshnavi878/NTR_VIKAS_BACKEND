import pytest_asyncio
from app.database.session import async_engine


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_connections():
    yield
    await async_engine.dispose()
