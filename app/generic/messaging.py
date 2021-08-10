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


class TrustPingMsg(BaseModel):
    connection_id: str
    comment_msg: str = None


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
    trustping_msg: TrustPingMsg,
    aries_controller: AriesAgentControllerBase = Depends(agent_selector),
):

    response = await aries_controller.messaging.trust_ping(
        connection_id=trustping_msg.connection_id, comment_msg=trustping_msg.comment_msg
    )
    return response
