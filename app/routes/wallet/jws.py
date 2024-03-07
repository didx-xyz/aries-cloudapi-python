from aries_cloudcontroller import ApiException, JWSCreate, JWSVerify
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions import CloudApiException
from app.models.jws import (
    JWSCreateRequest,
    JWSCreateResponse,
    JWSVerifyRequest,
    JWSVerifyResponse,
)
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/wallet/jws", tags=["wallet"])


@router.post(
    "/sign",
    response_model=JWSCreateResponse,
    summary="Sign JWS",
    description="""
Sign JSON Web Signature (JWS)

See https://www.rfc-editor.org/rfc/rfc7515.html for the JWS spec.""",
)
async def sign_jws(
    body: JWSCreateRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> JWSCreateResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Sign JWS")

    try:
        async with client_from_auth(auth) as aries_controller:
            jws = await aries_controller.wallet.wallet_jwt_sign_post(
                body=JWSCreate(**body.model_dump())
            )
    except ApiException as e:
        if str(e.status).startswith("4"):
            bound_logger.info("Client error during JWS signing: {}", e)
        else:
            bound_logger.warning("Error during JWS signing: {}", e)

        raise CloudApiException(status_code=e.status, detail=e.body) from e

    result = JWSCreateResponse(jws=jws)
    bound_logger.info("Successfully signed JWS.")
    return result


@router.post(
    "/verify",
    response_model=JWSVerifyResponse,
    summary="Verify JWS",
    description="""
Verify JSON Web Signature (JWS)

See https://www.rfc-editor.org/rfc/rfc7515.html for the JWS spec.""",
)
async def verify_jws(
    body: JWSVerifyRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> JWSVerifyResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Verify JWS")

    try:
        async with client_from_auth(auth) as aries_controller:
            verify_result = await aries_controller.wallet.wallet_jwt_verify_post(
                body=JWSVerify(jwt=body.jws)
            )
    except ApiException as e:
        if str(e.status).startswith("4"):
            bound_logger.info("Client error during JWS verification: {}", e)
        else:
            bound_logger.warning("API exception during JWS verification: {}", e)

        raise CloudApiException(status_code=e.status, detail=e.body) from e

    result = JWSVerifyResponse(**verify_result.model_dump())
    bound_logger.info("Successfully verified JWS.")
    return result
