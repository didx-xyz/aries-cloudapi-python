import logging
from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import agent_selector
from fastapi import APIRouter, Depends, Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/messaging", tags=["messaging"])


@router.post("/send-message")
async def send_messages(
    connection_id: str,
    msg: str,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    send = await aries_controller.messaging.send_message(
        connection_id=connection_id, msg=msg
    )
    return send


@router.post("/trust-ping")
async def send_trust_ping(connection_id: str, comment_msg: Optional[str]):

    response = await aries_controller.messaging.trust_ping(
        connection_id=connection_id, comment_msg=comment_msg
    )
    return response
