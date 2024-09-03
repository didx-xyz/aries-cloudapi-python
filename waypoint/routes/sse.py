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


