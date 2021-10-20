import logging

from aries_cloudcontroller import AcaPyClient, PingRequest, SendMessage
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/messaging", tags=["messaging"])


class Message(BaseModel):
    conn_id: str
    sendMessage: SendMessage


class TrustPingMsg(BaseModel):
    conn_id: str
    pingRequest: PingRequest


@router.post("/send-message")
async def send_messages(
    message: Message,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Send basic message.

    Parameters:
    -----------
    message: Message
        payload for sending a message

    Returns:
    ---------
    The response object obtained when sending a message.
    """
    send = await aries_controller.basicmessage.send_message(
        conn_id=message.conn_id, body=message.sendMessage
    )
    return send


@router.post("/trust-ping")
async def send_trust_ping(
    trustping_msg: TrustPingMsg,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Trust ping

    Parameters:
    -----------
    trustping_msg : TrustPingMsg
        payload for sending a trust ping

    Returns:
    --------
    The response object obtained when sending a trust ping.
    """
    response = await aries_controller.trustping.send_ping(
        conn_id=trustping_msg.conn_id, body=trustping_msg.pingRequest
    )
    return response
