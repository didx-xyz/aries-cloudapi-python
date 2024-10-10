from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.dependencies.auth import (
    AcaPyAuthVerified,
    acapy_auth_verified,
    verify_wallet_access,
)
from app.services.event_handling.sse import sse_subscribe_event_with_field_and_state
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/sse", tags=["sse"])


group_id_query: Optional[str] = Query(
    default=None,
    description="Group ID to which the wallet belongs",
    include_in_schema=False,
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
        ),
        media_type="text/event-stream",
    )
