import asyncio
from logging import Logger
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

look_back_field: float = Query(
    default=MAX_EVENT_AGE_SECONDS,
    description=(
        "Duration in seconds to look back in time to include past events "
        f"(default is the max event age stored in SSE: {MAX_EVENT_AGE_SECONDS} seconds). "
        "Setting to 0 means only events after connection is established will be returned"
    ),
    ge=0,
    le=MAX_EVENT_AGE_SECONDS,
)

group_id_query: Optional[str] = Query(
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
    """
    Periodically checks if the client connected to the SSE stream has disconnected.

    Args:
        request (Request): The FastAPI request object from which the client's connection
                           status can be determined.
        stop_event (asyncio.Event): An event that, when set, indicates that the client
                                    has disconnected and the stream should be stopped.

    This function is typically run as a background task during the lifespan of an SSE
    stream. It allows the server to gracefully terminate the event stream and clean up
    resources when the client disconnects.

    Note:
        DISCONNECT_CHECK_PERIOD is a constant that defines how often (in seconds) the
        function checks for client disconnection. Adjust this value based on the desired
        balance between responsiveness and resource usage.
    """
    while not stop_event.is_set():
        if await request.is_disconnected():
            logger.debug("SSE check_disconnection: request has disconnected.")
            stop_event.set()
        await asyncio.sleep(DISCONNECT_CHECK_PERIOD)


async def sse_event_stream_generator(
    *,
    sse_manager: SseManager,
    request: Request,
    background_tasks: BackgroundTasks,
    wallet_id: str,
    topic: Optional[str] = None,
    field: Optional[str] = None,
    field_id: Optional[str] = None,
    desired_state: Optional[str] = None,
    look_back: float = MAX_EVENT_AGE_SECONDS,
    logger: Logger,  # pylint: disable=redefined-outer-name
) -> AsyncGenerator[str, None]:
    """
    Asynchronously generates a stream of Server-Sent Events (SSE) for a specific wallet,
    optionally filtered by topic, field, field ID, and/or desired state.

    Args:
        sse_manager (SseManager): The SSE manager instance managing events.
        request (Request): The incoming request object, to detect client disconnects.
        background_tasks (BackgroundTasks): Background tasks dependency for adding new tasks.
        wallet_id (str): The wallet ID for which to generate event stream.
        topic (Optional[str]): The specific topic to subscribe to. Defaults to all topics.
        field (Optional[str]): The specific field to filter events by.
        field_id (Optional[str]): The ID of the field to match for filtering.
        desired_state (Optional[str]): The desired state to filter events by.
        look_back (float): How far back to look for events in seconds. Defaults to a predefined maximum.
        logger (Logger): The logger for logging information about the event stream.

    Yields:
        str: A JSON string representation of the SSE event that matches the subscription criteria.

    This generator listens for events related to the specified wallet ID, filtering them
    based on the provided criteria (topic, field, field ID, and desired state). It yields
    events as they occur, formatting them into JSON strings.

    It also monitors the request connection status, terminating the event stream if the
    client disconnects. A background task is used to check for disconnections.

    Note:
        If neither topic nor desired state is specified, the generator will listen for
        all events related to the wallet ID. Specifying a desired state implies a
        subscription to a single event, after which the generator will stop.
    """
    if topic is None:
        topic = WEBHOOK_TOPIC_ALL

    yield_single_event = bool(desired_state)  # True if exists, False otherwise

    stop_event = asyncio.Event()
    event_generator_wrapper: EventGeneratorWrapper = await sse_manager.sse_event_stream(
        wallet=wallet_id,
        topic=topic,
        look_back=look_back,
        stop_event=stop_event,
        duration=SSE_TIMEOUT if desired_state else 0,
    )
    async with event_generator_wrapper as event_generator:
        background_tasks.add_task(check_disconnection, request, stop_event)

        async for event in event_generator:
            if await request.is_disconnected():
                logger.info("SSE event_stream: client disconnected.")
                stop_event.set()
                break
            try:
                should_yield_event = True
                # Determine if event matches subscription:
                if field or desired_state:
                    payload = dict(event.payload)  # to check if field or state exists

                    if (
                        field
                        and field_id
                        and (field not in payload or payload[field] != field_id)
                    ):
                        should_yield_event = False

                    if desired_state and payload.get("state") != desired_state:
                        should_yield_event = False

                if should_yield_event:
                    # Dump event model to json:
                    result = event.model_dump_json()
                    logger.trace("Yielding SSE event: {}", result)
                    yield result  # Send the event

                    if yield_single_event:
                        stop_event.set()
                        break  # End the generator
            except asyncio.QueueEmpty:
                await asyncio.sleep(QUEUE_POLL_PERIOD)
            except asyncio.CancelledError:
                # This exception is thrown when the client disconnects.
                logger.info("SSE event stream cancelled.")
                stop_event.set()
                break


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
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
    """
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "look_back": look_back,
        }
    )
    bound_logger.info(
        "SSE: GET request received: Subscribe to wallet events on all topics"
    )

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    event_stream = sse_event_stream_generator(
        sse_manager=sse_manager,
        request=request,
        background_tasks=background_tasks,
        wallet_id=wallet_id,
        look_back=look_back,
        logger=bound_logger,
    )

    return EventSourceResponse(event_stream)


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
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
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
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            "look_back": look_back,
        }
    )
    bound_logger.info("SSE: GET request received: Subscribe to wallet events by topic")

    if group_id and not await sse_manager.check_wallet_belongs_to_group(
        wallet_id=wallet_id, group_id=group_id
    ):
        raise BadGroupIdException()

    event_stream = sse_event_stream_generator(
        sse_manager=sse_manager,
        request=request,
        background_tasks=background_tasks,
        wallet_id=wallet_id,
        topic=topic,
        look_back=look_back,
        logger=bound_logger,
    )

    return EventSourceResponse(event_stream)


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
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            "desired_state": desired_state,
            "look_back": look_back,
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

    event_stream = sse_event_stream_generator(
        sse_manager=sse_manager,
        request=request,
        background_tasks=background_tasks,
        wallet_id=wallet_id,
        topic=topic,
        desired_state=desired_state,
        look_back=look_back,
        logger=bound_logger,
    )

    return EventSourceResponse(event_stream)


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
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            field: field_id,
            "look_back": look_back,
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

    event_stream = sse_event_stream_generator(
        sse_manager=sse_manager,
        request=request,
        background_tasks=background_tasks,
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        look_back=look_back,
        logger=bound_logger,
    )

    return EventSourceResponse(event_stream)


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
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    sse_manager: SseManager = Depends(Provide[Container.sse_manager]),
) -> EventSourceResponse:
    bound_logger = logger.bind(
        body={
            "wallet_id": wallet_id,
            "group_id": group_id,
            "topic": topic,
            field: field_id,
            "desired_state": desired_state,
            "look_back": look_back,
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

    event_stream = sse_event_stream_generator(
        sse_manager=sse_manager,
        request=request,
        background_tasks=background_tasks,
        wallet_id=wallet_id,
        topic=topic,
        field=field,
        field_id=field_id,
        desired_state=desired_state,
        look_back=look_back,
        logger=bound_logger,
    )

    return EventSourceResponse(event_stream)
