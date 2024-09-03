import asyncio
from logging import Logger
from typing import Any, AsyncGenerator, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import BackgroundTasks, Depends, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from shared import DISCONNECT_CHECK_PERIOD, SSE_TIMEOUT, APIRouter
from shared.log_config import get_logger
from shared.models.webhook_events import CloudApiWebhookEventGeneric
from waypoint.services.dependency_injection.container import Container
from waypoint.services.nats_service import NatsEventsProcessor
from waypoint.util.event_generator_wrapper import EventGeneratorWrapper

logger = get_logger(__name__)

router = APIRouter(
    prefix="/stuff",
    tags=["waypoint"],
)


class BadGroupIdException(HTTPException):
    """Custom exception when group_id is specified and no events exist on redis"""

    def __init__(self):
        super().__init__(
            status_code=404, detail="No events found for this wallet/group combination"
        )


async def check_disconnect(request: Request, stop_event: asyncio.Event) -> None:
    """
    Check if the client has disconnected
    """
    while not stop_event.is_set():
        if await request.is_disconnected:
            stop_event.set()
        await asyncio.sleep(DISCONNECT_CHECK_PERIOD)


async def nats_event_stream_generator(
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
    group_id: Optional[str],
    nats_processor: NatsEventsProcessor,
) -> AsyncGenerator[str, None]:
    """
    Generator for NATS events
    """
    logger.error("got connection")
    stop_event = asyncio.Event()

    event_generator_wrapper: EventGeneratorWrapper = (
        await nats_processor.process_events(
            group_id=group_id,
            wallet_id=wallet_id,
            topic=topic,
            stop_event=stop_event,
            duration=SSE_TIMEOUT,
        )
    )

    try:
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnect, request, stop_event)
            async for event in event_generator:
                if await request.is_disconnected():
                    stop_event.set()
                    break
                payload = dict(event.payload)
                if payload[field] == field_id and payload["state"] == desired_state:
                    yield event.model_dump_json()
                    stop_event.set()
                    break
    except asyncio.CancelledError:
        stop_event.set()
