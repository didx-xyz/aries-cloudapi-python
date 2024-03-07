from aries_cloudcontroller import ApiException, SDJWSCreate, SDJWSVerify
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions import CloudApiException
from app.models.sd_jws import (
    SDJWSCreateRequest,
    SDJWSCreateResponse,
    SDJWSVerifyRequest,
    SDJWSVerifyResponse,
)
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/wallet/sd-jws", tags=["wallet"])


@router.post(
    "/sign",
    response_model=SDJWSCreateResponse,
    summary="Sign SD-JWS",
    description="""
Sign Select Disclosure for JWS (SD-JWS)

See https://www.ietf.org/archive/id/draft-ietf-oauth-selective-disclosure-jwt-07.html for the SD-JWT / SD-JWS spec.
""",
)
async def sign_sd_jws(
    body: SDJWSCreateRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> SDJWSCreateResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Sign SD-JWS")

    try:
        async with client_from_auth(auth) as aries_controller:
            sd_jws = await aries_controller.wallet.wallet_sd_jwt_sign_post(
                body=SDJWSCreate(**body.model_dump())
            )
    except ApiException as e:
        if str(e.status).startswith("4"):
            bound_logger.info("Client error during SD-JWS signing: {}", e)
        else:
            bound_logger.warning("Error during SD-JWS signing: {}", e)

        raise CloudApiException(status_code=e.status, detail=e.body) from e

    result = SDJWSCreateResponse(sd_jws=sd_jws)
    bound_logger.info("Successfully signed SD-JWS.")
    return result


@router.post(
    "/verify",
    response_model=SDJWSVerifyResponse,
    summary="Verify SD-JWS",
    description="""
Verify Select Disclosure for JWS (SD-JWS)

See https://www.ietf.org/archive/id/draft-ietf-oauth-selective-disclosure-jwt-07.html for the SD-JWT / SD-JWS spec.
""",
)
async def verify_sd_jws(
    body: SDJWSVerifyRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> SDJWSVerifyResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Verify SD-JWS")

    try:
        async with client_from_auth(auth) as aries_controller:
            verify_result = await aries_controller.wallet.wallet_sd_jwt_verify_post(
                body=SDJWSVerify(sd_jwt=body.sd_jws)
            )
    except ApiException as e:
        if str(e.status).startswith("4"):
            bound_logger.info("Client error during SD-JWS verification: {}", e)
        else:
            bound_logger.warning("API exception during SD-JWS verification: {}", e)

        raise CloudApiException(status_code=e.status, detail=e.body) from e

    result = SDJWSVerifyResponse(**verify_result.model_dump())
    bound_logger.info("Successfully verified SD-JWS.")
    return result
