import pytest
import asyncio
from typing import Any


@pytest.fixture(scope="module")
def event_loop(request: Any):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def get(response: Any):
    if response:
        return response
