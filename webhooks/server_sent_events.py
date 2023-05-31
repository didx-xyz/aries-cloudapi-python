import asyncio

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from shared_models import WEBHOOK_TOPIC_ALL
from webhooks.containers import Container
from webhooks.services import Service
from webhooks.sse_manager import SSEManager

router = APIRouter()

sse_manager_global_instance = SSEManager()


def get_sse_manager():
    return sse_manager_global_instance


@router.get(
    "/sse/{wallet_id}",
    response_class=StreamingResponse,
    summary="Subscribe to wallet ID server-side events",
)
@inject
async def sse_subscribe_wallet(
    wallet_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
    service: Service = Depends(Provide[Container.service]),
):
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
        service: The service instance for fetching undelivered messages.
    """

    async def event_stream():
        async with sse_manager.sse_event_stream(
            wallet_id, WEBHOOK_TOPIC_ALL, service
        ) as queue:
            while True:
                # The 'while True' loop is safe here because it is inside an async function. It
                # doesn't block; it awaits for new events from the queue and yields them as they arrive.
                try:
                    event = await queue.get()
                    yield f"data: {event}\n\n"
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/sse/{topic}/{wallet_id}",
    response_class=StreamingResponse,
    summary="Subscribe to topic and wallet ID server-side events",
)
@inject
async def sse_subscribe(
    topic: str,
    wallet_id: str,
    sse_manager: SSEManager = Depends(get_sse_manager),
    service: Service = Depends(Provide[Container.service]),
):
    """
    Subscribe to server-side events for a specific topic and wallet ID.

    Args:
        topic: The topic to which the wallet is subscribing.
        wallet_id: The ID of the wallet subscribing to the events.
        sse_manager: The SSEManager instance managing the server-sent events.
        service: The service instance for fetching undelivered messages.
    """

    async def event_stream():
        async with sse_manager.sse_event_stream(wallet_id, topic, service) as queue:
            while True:
                try:
                    event = await queue.get()
                    yield f"data: {event}\n\n"
                except asyncio.CancelledError:
                    # This exception is thrown when the client disconnects.
                    break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
