import logging
from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import agent_selector
from fastapi import APIRouter, Depends
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/messaging", tags=["messaging"])


class Message(BaseModel):
    connection_id: str
    msg: str


@router.post("/send-message")
async def send_messages(
    message: Message,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):
    send = await aries_controller.messaging.send_message(
        connection_id=message.connection_id, msg=message.msg
    )
    return send


@router.post("/trust-ping")
async def send_trust_ping(
    connection_id: str,
    comment_msg: Optional[str],
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    response = await aries_controller.messaging.trust_ping(
        connection_id=connection_id, comment_msg=comment_msg
    )
    return response
