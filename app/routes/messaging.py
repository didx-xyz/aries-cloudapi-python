from aries_cloudcontroller import PingRequest, PingRequestResponse, SendMessage
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions.handle_acapy_call import handle_acapy_call
from app.models.messaging import Message, TrustPingMsg
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/messaging", tags=["messaging"])


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
    request_body = SendMessage(content=message.content)
    async with client_from_auth(auth) as aries_controller:
        await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.basicmessage.send_message,
            conn_id=message.connection_id,
            body=request_body,
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
    request_body = PingRequest(comment=trustping_msg.comment)
    async with client_from_auth(auth) as aries_controller:
        response = await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.trustping.send_ping,
            conn_id=trustping_msg.connection_id,
            body=request_body,
        )
    logger.info("Successfully sent trust ping.")
    return response
