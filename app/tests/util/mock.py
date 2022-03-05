from typing import Optional, Any

# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response