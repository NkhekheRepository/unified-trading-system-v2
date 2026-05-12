import pytest
import aiohttp

@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s
