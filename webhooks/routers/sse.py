import asyncio
import logging
import time
from typing import Any, Generator

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from shared_models import WEBHOOK_TOPIC_ALL, TopicItem
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

    async def event_stream(duration=1) -> Generator[str, Any, None]:
        async with sse_manager.sse_event_stream(
            wallet_id,
            WEBHOOK_TOPIC_ALL,
        ) as queue:
            start_time = time.time()
            while time.time() - start_time < duration:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event: TopicItem = queue.get_nowait()
                    yield event.json()
                except asyncio.QueueEmpty:
                    time.sleep(0.2)
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

    async def event_stream(duration=1) -> Generator[str, Any, None]:
        async with sse_manager.sse_event_stream(wallet_id, topic) as queue:
            start_time = time.time()
            while time.time() - start_time < duration:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event: TopicItem = queue.get_nowait()
                    yield event.json()
                except asyncio.QueueEmpty:
                    time.sleep(0.2)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return EventSourceResponse(event_stream())
