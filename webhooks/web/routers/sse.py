import asyncio
from typing import AsyncGenerator, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import BackgroundTasks, Depends, HTTPException, Query, Request
from sse_starlette.sse import EventSourceResponse

from shared import DISCONNECT_CHECK_PERIOD, QUEUE_POLL_PERIOD, SSE_TIMEOUT, APIRouter
from shared.constants import MAX_EVENT_AGE_SECONDS
from shared.log_config import get_logger
from shared.models.webhook_events import WEBHOOK_TOPIC_ALL
from webhooks.services.dependency_injection.container import Container
from webhooks.services.sse_manager import SseManager
from webhooks.util.event_generator_wrapper import EventGeneratorWrapper

logger = get_logger(__name__)

router = APIRouter(
    prefix="/sse",
    tags=["sse"],
)

lookback_time_field = Query(
    default=MAX_EVENT_AGE_SECONDS,
    description=(
        "Duration in seconds to lookback in time to include past events "
        f"(default is the max event age stored in SSE: {MAX_EVENT_AGE_SECONDS} seconds). "
        "Setting to 0 means only events after connection is established will be returned"
    ),
)

group_id_field = Query(
    default=None,
    description="Group ID to which the wallet belongs",
)


class BadGroupIdException(HTTPException):
    """Custom exception when group_id is specified and no events exist on redis"""

    def __init__(self):
        super().__init__(
            status_code=404, detail="No events found for this wallet/group combination"
        )


async def check_disconnection(request: Request, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        if await request.is_disconnected():
            logger.debug("SSE check_disconnection: request has disconnected.")
            stop_event.set()
        await asyncio.sleep(DISCONNECT_CHECK_PERIOD)


@router.get(
    "/{wallet_id}",
    response_class=EventSourceResponse,
    summary="Subscribe to wallet ID server-side events",
)
@inject
async def sse_subscribe_wallet(
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    lookback_time: int = lookback_time_field,
    group_id: Optional[str] = group_id_field,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
    """
    bound_logger = logger.bind(body={"wallet_id": wallet_id, "group_id": group_id})
    bound_logger.info(
        "SSE: GET request received: Subscribe to wallet events on all topics"
    )

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    async def event_stream() -> AsyncGenerator[str, None]:
        stop_event = asyncio.Event()
        event_generator_wrapper: EventGeneratorWrapper = (
            await sse_manager.sse_event_stream(
                wallet=wallet_id,
                topic=WEBHOOK_TOPIC_ALL,
                lookback_time=lookback_time,
                stop_event=stop_event,
            )
        )
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnection, request, stop_event)

            async for event in event_generator:
                if await request.is_disconnected():
                    bound_logger.info("SSE event_stream: client disconnected.")
                    stop_event.set()
                    break
                try:
                    result = event.model_dump_json()
                    bound_logger.trace("Yielding SSE event: {}", result)
                    yield result
                except asyncio.QueueEmpty:
                    await asyncio.sleep(QUEUE_POLL_PERIOD)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    bound_logger.info("SSE event stream cancelled.")
                    stop_event.set()
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
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: str,
    lookback_time: int = lookback_time_field,
    group_id: Optional[str] = group_id_field,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    """
    Subscribe to server-side events for a specific topic and wallet ID.

    Args:
        topic: The topic to which the wallet is subscribing.
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
    """
    bound_logger = logger.bind(
        body={"wallet_id": wallet_id, "group_id": group_id, "topic": topic}
    )
    bound_logger.info("SSE: GET request received: Subscribe to wallet events by topic")

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    async def event_stream() -> AsyncGenerator[str, None]:
        stop_event = asyncio.Event()
        event_generator_wrapper: EventGeneratorWrapper = (
            await sse_manager.sse_event_stream(
                wallet=wallet_id,
                topic=topic,
                lookback_time=lookback_time,
                stop_event=stop_event,
            )
        )
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnection, request, stop_event)

            async for event in event_generator:
                if await request.is_disconnected():
                    bound_logger.info("SSE event_stream: client disconnected.")
                    stop_event.set()
                    break
                try:
                    result = event.model_dump_json()
                    bound_logger.trace("Yielding SSE event: {}", result)
                    yield result
                except asyncio.QueueEmpty:
                    await asyncio.sleep(QUEUE_POLL_PERIOD)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    bound_logger.info("SSE event stream cancelled.")
                    stop_event.set()
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}/{desired_state}",
    response_class=EventSourceResponse,
    summary="Wait for a desired state to be reached for some event for this wallet and topic "
    "`desired_state` may be `offer-received`, `transaction-acked`, `done`, etc.",
)
@inject
async def sse_subscribe_event_with_state(
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: str,
    desired_state: str,
    lookback_time: int = lookback_time_field,
    group_id: Optional[str] = group_id_field,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            "desired_state": desired_state,
        }
    )
    bound_logger.info(
        "SSE: GET request received: Subscribe to wallet event by topic, "
        "waiting for specific state"
    )

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    async def event_stream() -> AsyncGenerator[str, None]:
        stop_event = asyncio.Event()
        event_generator_wrapper: EventGeneratorWrapper = (
            await sse_manager.sse_event_stream(
                wallet=wallet_id,
                topic=topic,
                lookback_time=lookback_time,
                stop_event=stop_event,
                duration=SSE_TIMEOUT,
            )
        )
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnection, request, stop_event)

            async for event in event_generator:
                if await request.is_disconnected():
                    bound_logger.info("SSE event_stream: client disconnected.")
                    stop_event.set()
                    break
                try:
                    payload = dict(event.payload)  # to check if keys exist in payload

                    if "state" in payload and payload["state"] == desired_state:
                        result = event.model_dump_json()
                        bound_logger.trace("Yielding SSE event: {}", result)
                        yield result  # Send the event
                        stop_event.set()
                        break  # End the generator
                except asyncio.QueueEmpty:
                    await asyncio.sleep(QUEUE_POLL_PERIOD)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    bound_logger.info("SSE event stream cancelled.")
                    stop_event.set()
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}",
    response_class=EventSourceResponse,
    summary="Wait for a desired state to be reached for some event for this wallet and topic "
    "The `relevant_id` refers to a `transaction_id` when using topic `endorsements,"
    "or a `connection_id` on topics: `connections`, `credentials`, or `proofs`, etc."
    "`desired_state` may be `offer-received`, `transaction-acked`, `done`, etc.",
)
@inject
async def sse_subscribe_stream_with_fields(
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    lookback_time: int = lookback_time_field,
    group_id: Optional[str] = group_id_field,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            field: field_id,
        }
    )
    bound_logger.info(
        "SSE: GET request received: Subscribe to wallet events by topic, "
        "only events with specific field-id pairs"
    )

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    async def event_stream() -> AsyncGenerator[str, None]:
        stop_event = asyncio.Event()
        event_generator_wrapper: EventGeneratorWrapper = (
            await sse_manager.sse_event_stream(
                wallet=wallet_id,
                topic=topic,
                lookback_time=lookback_time,
                stop_event=stop_event,
                duration=SSE_TIMEOUT,
            )
        )
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnection, request, stop_event)

            async for event in event_generator:
                if await request.is_disconnected():
                    bound_logger.info("SSE event_stream: client disconnected.")
                    stop_event.set()
                    break
                try:
                    payload = dict(event.payload)  # to check if keys exist in payload
                    if field in payload and payload[field] == field_id:
                        result = event.model_dump_json()
                        bound_logger.trace("Yielding SSE event: {}", result)
                        yield result  # Send the event
                except asyncio.QueueEmpty:
                    await asyncio.sleep(QUEUE_POLL_PERIOD)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    bound_logger.info("SSE event stream cancelled.")
                    stop_event.set()
                    break

    return EventSourceResponse(event_stream())


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}",
    response_class=EventSourceResponse,
    summary="Wait for a desired state to be reached for some event for this wallet and topic "
    "The `relevant_id` refers to a `transaction_id` when using topic `endorsements,"
    "or a `connection_id` on topics: `connections`, `credentials`, or `proofs`, etc."
    "`desired_state` may be `offer-received`, `transaction-acked`, `done`, etc.",
)
@inject
async def sse_subscribe_event_with_field_and_state(
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
    lookback_time: int = lookback_time_field,
    group_id: Optional[str] = group_id_field,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            field: field_id,
            "desired_state": desired_state,
        }
    )
    bound_logger.info(
        "SSE: GET request received: Subscribe to wallet event by topic, "
        "waiting for payload with field-id pair and specific state"
    )

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    async def event_stream() -> AsyncGenerator[str, None]:
        stop_event = asyncio.Event()
        event_generator_wrapper: EventGeneratorWrapper = (
            await sse_manager.sse_event_stream(
                wallet=wallet_id,
                topic=topic,
                lookback_time=lookback_time,
                stop_event=stop_event,
                duration=SSE_TIMEOUT,
            )
        )
        async with event_generator_wrapper as event_generator:
            background_tasks.add_task(check_disconnection, request, stop_event)

            async for event in event_generator:
                if await request.is_disconnected():
                    bound_logger.info("SSE event_stream: client disconnected.")
                    stop_event.set()
                    break
                try:
                    payload = dict(event.payload)  # to check if keys exist in payload
                    if (
                        field in payload
                        and payload[field] == field_id
                        and payload["state"] == desired_state
                    ):
                        result = event.model_dump_json()
                        bound_logger.trace("Yielding SSE event: {}", result)
                        yield result  # Send the event
                        stop_event.set()
                        break  # End the generator
                except asyncio.QueueEmpty:
                    await asyncio.sleep(QUEUE_POLL_PERIOD)
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    bound_logger.info("SSE event stream cancelled.")
                    stop_event.set()
                    break

    return EventSourceResponse(event_stream())
