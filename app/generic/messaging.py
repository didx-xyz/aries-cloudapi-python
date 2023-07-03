from aries_cloudcontroller import PingRequest, SendMessage
from aries_cloudcontroller.model.ping_request_response import PingRequestResponse
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config.log_config import get_logger
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.dependencies.role import client_from_auth

logger = get_logger(__name__)

router = APIRouter(prefix="/generic/messaging", tags=["messaging"])


class Message(BaseModel):
    connection_id: str
    content: str


class TrustPingMsg(BaseModel):
    connection_id: str
    comment: str


@router.post("/send-message")
async def send_messages(
    message: Message,
    auth: AcaPyAuth = Depends(acapy_auth),
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
    logger.info("POST request received: Send message")
    async with client_from_auth(auth) as aries_controller:
        await aries_controller.basicmessage.send_message(
            conn_id=message.connection_id, body=SendMessage(content=message.content)
        )
    logger.info("Successfully sent message.")


@router.post("/trust-ping", response_model=PingRequestResponse)
async def send_trust_ping(
    trustping_msg: TrustPingMsg,
    auth: AcaPyAuth = Depends(acapy_auth),
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
    logger.info("POST request received: Send trust ping")
    async with client_from_auth(auth) as aries_controller:
        response = await aries_controller.trustping.send_ping(
            conn_id=trustping_msg.connection_id,
            body=PingRequest(comment=trustping_msg.comment),
        )
    logger.info("Successfully sent trust ping.")
    return response
