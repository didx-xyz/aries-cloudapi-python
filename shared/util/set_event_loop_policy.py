import asyncio

import uvloop


def set_event_loop_policy() -> None:
    """Set uvloop as the default event loop policy."""
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
