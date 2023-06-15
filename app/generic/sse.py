from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.facades.sse import (
    sse_subscribe_event_with_field_and_state,
    sse_subscribe_event_with_state,
    sse_subscribe_stream_with_fields,
    sse_subscribe_wallet,
    sse_subscribe_wallet_topic,
)
from shared.dependencies.auth import AcaPyAuthVerified, acapy_auth_verified

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get(
    "/{wallet_id}", response_class=StreamingResponse, name="sse:subscribe_wallet"
)
async def get_sse_subscribe_wallet(
    request: Request,
    wallet_id: str,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
):
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
    """
    return StreamingResponse(
        sse_subscribe_wallet(wallet_id), media_type="text/event-stream"
    )


@router.get(
    "/{wallet_id}/{topic}",
    response_class=StreamingResponse,
    name="sse:subscribe_wallet_topic",
)
async def get_sse_subscribe_wallet_topic(
    request: Request,
    wallet_id: str,
    topic: str,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
):
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
    """
    return StreamingResponse(
        sse_subscribe_wallet_topic(wallet_id, topic), media_type="text/event-stream"
    )


@router.get(
    "/{wallet_id}/{topic}/{desired_state}",
    response_class=StreamingResponse,
    name="sse:subscribe_event_with_state",
)
async def get_sse_subscribe_event_with_state(
    request: Request,
    wallet_id: str,
    topic: str,
    desired_state: str,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
):
    """
    Subscribe to server-side events for a specific wallet ID and topic, and wait for a desired state to be reached.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        desired_state: The desired state to be reached.
    """
    return StreamingResponse(
        sse_subscribe_event_with_state(wallet_id, topic, desired_state),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}",
    response_class=StreamingResponse,
    name="sse:subscribe_stream_with_fields",
)
async def get_sse_subscribe_stream_with_fields(
    request: Request,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
):
    """
    Subscribe to server-side events for a specific wallet ID and topic, and filter the events by a specific field and field ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        field: The field to which the wallet is subscribing.
        field_id: The ID of the field subscribing to the events.
    """
    return StreamingResponse(
        sse_subscribe_stream_with_fields(wallet_id, topic, field, field_id),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}",
    response_class=StreamingResponse,
    name="sse:subscribe_event_with_field_and_state",
)
async def get_sse_subscribe_event_with_field_and_state(
    request: Request,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
):
    """
    Wait for a desired state to be reached for some event for this wallet and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        field: The field to which the wallet is subscribing.
        field_id: The ID of the field subscribing to the events.
        desired_state: The desired state to be reached.
    """

    async def single_event_stream():
        async for event in sse_subscribe_event_with_field_and_state(
            wallet_id, topic, field, field_id, desired_state
        ):
            yield event
            break  # Stop processing the stream after the first event

    return StreamingResponse(single_event_stream(), media_type="text/event-stream")
