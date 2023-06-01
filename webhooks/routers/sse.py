import asyncio
import logging
from typing import Any, Generator

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from shared_models import WEBHOOK_TOPIC_ALL
from webhooks.dependencies.container import Container
from webhooks.dependencies.service import Service
from webhooks.dependencies.sse_manager import SSEManager

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sse",
    tags=["sse"],
)


@inject
async def get_sse_manager(service: Service = Depends(Provide[Container.service])):
    return SSEManager(service)


@router.get(
    "/{wallet_id}",
    response_class=EventSourceResponse,
    summary="Subscribe to wallet ID server-side events",
)
@inject
async def sse_subscribe_wallet(
    request: Request,
    wallet_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
):
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
        service: The service instance for fetching undelivered messages.
    """

    async def event_stream() -> Generator[str, Any, None]:
        async with sse_manager.sse_event_stream(
            wallet_id,
            WEBHOOK_TOPIC_ALL,
        ) as queue:
            # The 'while True' loop is safe here because it is inside an async function. It
            # doesn't block; it awaits for new events from the queue and yields them as they arrive.
            while True:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event = await queue.get()
                    yield f"data: {event}"
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    LOGGER.debug("SSE event_stream closing with CancelledError")
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}",
    response_class=EventSourceResponse,
    summary="Subscribe to topic and wallet ID server-side events",
)
@inject
async def sse_subscribe(
    request: Request,
    topic: str,
    wallet_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
):
    """
    Subscribe to server-side events for a specific topic and wallet ID.

    Args:
        topic: The topic to which the wallet is subscribing.
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
        service: The service instance for fetching undelivered messages.
    """

    async def event_stream() -> Generator[str, Any, None]:
        async with sse_manager.sse_event_stream(wallet_id, topic) as queue:
            while True:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event = await queue.get()
                    yield f"data: {event}"
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return EventSourceResponse(event_stream())
