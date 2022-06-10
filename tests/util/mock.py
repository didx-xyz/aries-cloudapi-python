from typing import Any, Optional

# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response
