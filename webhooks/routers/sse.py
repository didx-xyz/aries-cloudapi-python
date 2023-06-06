import asyncio
import logging
import time
from typing import Any, Generator

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, Request
from sse_starlette.sse import EventSourceResponse

from shared import WEBHOOK_TOPIC_ALL, APIRouter, TopicItem
from webhooks.dependencies.container import Container
from webhooks.dependencies.sse_manager import SseManager

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sse",
    tags=["sse"],
)


@router.get(
    "/{wallet_id}",
    response_class=EventSourceResponse,
    summary="Subscribe to wallet ID server-side events",
)
@inject
async def sse_subscribe_wallet(
    request: Request,
    wallet_id: str,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
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
                    await asyncio.sleep(0.2)
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
async def sse_subscribe_wallet_topic(
    request: Request,
    wallet_id: str,
    topic: str,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
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
                    await asyncio.sleep(0.2)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}/{desired_state}",
    response_class=EventSourceResponse,
    summary="Wait for a desired state to be reached. "
    "`desired_state` may be `offer-received`, `transaction-acked`, or `done`.",
)
@inject
async def sse_subscribe_desired_state(
    request: Request,
    wallet_id: str,
    topic: str,
    desired_state: str,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
):
    async def event_stream(duration=150):
        async with sse_manager.sse_event_stream(wallet_id, topic) as queue:
            start_time = time.time()
            while time.time() - start_time < duration:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event: TopicItem = queue.get_nowait()
                    payload = dict(event.payload)  # to check if keys exist in payload
                    if "state" in payload and payload["state"] == desired_state:
                        yield event.json()  # Send the event
                        break  # End the generator
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.2)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}",
    response_class=EventSourceResponse,
    summary="Wait for a desired state to be reached. "
    "The `relevant_id` refers to a `transaction_id` when using topic `endorsements,"
    "or a `connection_id` on topics: `connections`, `credentials`, or `proofs`."
    "`desired_state` may be `offer-received`, `transaction-acked`, or `done`.",
)
@inject
async def sse_subscribe_filtered_event(
    request: Request,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
):
    async def event_stream(duration=150):
        async with sse_manager.sse_event_stream(wallet_id, topic) as queue:
            start_time = time.time()
            while time.time() - start_time < duration:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    LOGGER.debug("SSE event_stream: client disconnected")
                    break
                try:
                    event: TopicItem = queue.get_nowait()
                    payload = dict(event.payload)  # to check if keys exist in payload
                    if (
                        field in payload
                        and payload[field] == field_id
                        and payload["state"] == desired_state
                    ):
                        yield event.json()  # Send the event
                        break  # End the generator
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.2)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return EventSourceResponse(event_stream())
