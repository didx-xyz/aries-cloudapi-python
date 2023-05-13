from typing import Any


# This allows easy mocking of async functions, making `response` awaitable
async def to_async(response: Any):
    return response
