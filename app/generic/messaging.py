import logging

from aries_cloudcontroller import AcaPyClient, PingRequest, SendMessage
from aries_cloudcontroller.model.ping_request_response import PingRequestResponse
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/messaging", tags=["messaging"])


class Message(BaseModel):
    connection_id: str
    content: str


class TrustPingMsg(BaseModel):
    connection_id: str
    comment: str


@router.post("/send-message", status_code=204)
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
    await aries_controller.basicmessage.send_message(
        conn_id=message.connection_id, body=SendMessage(content=message.content)
    )


@router.post("/trust-ping", response_model=PingRequestResponse)
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
        conn_id=trustping_msg.connection_id,
        body=PingRequest(comment=trustping_msg.comment),
    )
    return response
