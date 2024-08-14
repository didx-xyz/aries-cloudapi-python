from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.dependencies.auth import (
    AcaPyAuthVerified,
    acapy_auth_verified,
    verify_wallet_access,
)
from app.services.event_handling.sse import (
    sse_subscribe_event_with_field_and_state,
    sse_subscribe_event_with_state,
    sse_subscribe_stream_with_fields,
    sse_subscribe_wallet,
    sse_subscribe_wallet_topic,
)
from shared.constants import MAX_EVENT_AGE_SECONDS
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/sse", tags=["sse"])


look_back_field: float = Query(
    default=MAX_EVENT_AGE_SECONDS,
    description=(
        "The duration in seconds to look back in time, defining the window of additional webhook events that should "
        "be included, prior to the initial connection of the stream. The default value will include events up to "
        f"{MAX_EVENT_AGE_SECONDS} seconds ago, and represents the maximum value for this setting. "
        "Setting to 0 means only events after the connection is established will be returned."
    ),
    ge=0.0,
    le=MAX_EVENT_AGE_SECONDS,
)

group_id_query: Optional[str] = Query(
    default=None,
    description="Group ID to which the wallet belongs",
    include_in_schema=False,
)


@router.get(
    "/{wallet_id}",
    response_class=StreamingResponse,
    name="Subscribe to Wallet Events",
)
async def get_sse_subscribe_wallet(
    request: Request,
    wallet_id: str,
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> StreamingResponse:
    """
    Subscribe to server-side events for a specific wallet ID.

    Parameters:
    -----------
        wallet_id: The ID of the wallet subscribing to the events.
        look_back: Specifies the look back window in seconds, to include events before connection established.
    """
    logger.bind(
        body={
            "group_id": group_id,
            "wallet_id": wallet_id,
            "look_back": look_back,
        }
    ).debug("GET request received: Subscribe to wallet events")

    verify_wallet_access(auth, wallet_id)

    return StreamingResponse(
        sse_subscribe_wallet(
            request=request,
            group_id=group_id,
            wallet_id=wallet_id,
            look_back=look_back,
        ),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}",
    response_class=StreamingResponse,
    name="Subscribe to Wallet Events by Topic",
)
async def get_sse_subscribe_wallet_topic(
    request: Request,
    wallet_id: str,
    topic: str,
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> StreamingResponse:
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Parameters:
    -----------
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        look_back: Specifies the look back window in seconds, to include events before connection established.
    """
    logger.bind(
        body={
            "group_id": group_id,
            "wallet_id": wallet_id,
            "topic": topic,
            "look_back": look_back,
        }
    ).debug("GET request received: Subscribe to wallet events by topic")

    verify_wallet_access(auth, wallet_id)

    return StreamingResponse(
        sse_subscribe_wallet_topic(
            request=request,
            group_id=group_id,
            wallet_id=wallet_id,
            topic=topic,
            look_back=look_back,
        ),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}/{desired_state}",
    response_class=StreamingResponse,
    name="Subscribe to a Wallet Event by Topic and Desired State",
)
async def get_sse_subscribe_event_with_state(
    request: Request,
    wallet_id: str,
    topic: str,
    desired_state: str,
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> StreamingResponse:
    """
    Subscribe to server-side events for a specific wallet ID and topic,
    and wait for an event that matches the desired state.

    Parameters:
    -----------
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        desired_state: The desired state to be reached.
        look_back: Specifies the look back window in seconds, to include events before connection established.
    """
    logger.bind(
        body={
            "group_id": group_id,
            "wallet_id": wallet_id,
            "topic": topic,
            "desired_state": desired_state,
            "look_back": look_back,
        }
    ).debug(
        "GET request received: Subscribe to wallet events by topic and desired state"
    )

    verify_wallet_access(auth, wallet_id)

    return StreamingResponse(
        sse_subscribe_event_with_state(
            request=request,
            group_id=group_id,
            wallet_id=wallet_id,
            topic=topic,
            desired_state=desired_state,
            look_back=look_back,
        ),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}",
    response_class=StreamingResponse,
    name="Subscribe to Wallet Events by Topic and Field",
)
async def get_sse_subscribe_stream_with_fields(
    request: Request,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> StreamingResponse:
    """
    Subscribe to server-side events for a specific wallet ID and topic, and
    filter the events for payloads containing a specific field and field ID pair.

    Parameters:
    -----------
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        field: The field to which the wallet is subscribing.
        field_id: The ID of the field subscribing to the events.
        look_back: Specifies the look back window in seconds, to include events before connection established.
    """
    logger.bind(
        body={
            "group_id": group_id,
            "wallet_id": wallet_id,
            "topic": topic,
            field: field_id,
            "look_back": look_back,
        }
    ).debug(
        "GET request received: Subscribe to wallet events by topic and select field"
    )

    verify_wallet_access(auth, wallet_id)

    return StreamingResponse(
        sse_subscribe_stream_with_fields(
            request=request,
            group_id=group_id,
            wallet_id=wallet_id,
            topic=topic,
            field=field,
            field_id=field_id,
            look_back=look_back,
        ),
        media_type="text/event-stream",
    )


@router.get(
    "/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}",
    response_class=StreamingResponse,
    name="Subscribe to a Wallet Event by Topic, Field, and Desired State",
)
async def get_sse_subscribe_event_with_field_and_state(
    request: Request,
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
    look_back: float = look_back_field,
    group_id: Optional[str] = group_id_query,
    auth: AcaPyAuthVerified = Depends(acapy_auth_verified),
) -> StreamingResponse:
    """
    Wait for a desired state to be reached for some event for this wallet and topic,
    filtering for payloads that contain `field:field_id`.

    Parameters:
    -----------
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
        field: The field to which the wallet is subscribing.
        field_id: The ID of the field subscribing to the events.
        desired_state: The desired state to be reached.
        look_back: Specifies the look back window in seconds, to include events before connection established.
    """
    logger.bind(
        body={
            "group_id": group_id,
            "wallet_id": wallet_id,
            "topic": topic,
            field: field_id,
            "desired_state": desired_state,
            "look_back": look_back,
        }
    ).debug(
        "GET request received: Subscribe to wallet events by topic, field and state"
    )

    verify_wallet_access(auth, wallet_id)

    return StreamingResponse(
        sse_subscribe_event_with_field_and_state(
            request=request,
            group_id=group_id,
            wallet_id=wallet_id,
            topic=topic,
            field=field,
            field_id=field_id,
            desired_state=desired_state,
            look_back=look_back,
        ),
        media_type="text/event-stream",
    )
