from aries_cloudcontroller import SDJWSCreate, SDJWSVerify
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import CloudApiException, handle_acapy_call
from app.models.sd_jws import (
    SDJWSCreateRequest,
    SDJWSCreateResponse,
    SDJWSVerifyRequest,
    SDJWSVerifyResponse,
)
from app.util.extract_validation_error import extract_validation_error_msg
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
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> SDJWSCreateResponse:
    bound_logger = logger.bind(
        # Do not log payload:
        body=body.model_dump(exclude="payload")
    )
    bound_logger.debug("POST request received: Sign SD-JWS")

    try:
        sign_request = SDJWSCreate(**body.model_dump())
    except ValidationError as e:
        # Handle Pydantic validation error:
        error_msg = extract_validation_error_msg(e)
        bound_logger.info(
            "Bad request: Validation error from SDJWSCreateRequest body: {}", error_msg
        )
        raise CloudApiException(status_code=422, detail=error_msg) from e

    async with client_from_auth(auth) as aries_controller:
        sd_jws = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.wallet.sign_sd_jwt,
            body=sign_request,
        )

    result = SDJWSCreateResponse(sd_jws=sd_jws)
    bound_logger.debug("Successfully signed SD-JWS.")
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
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> SDJWSVerifyResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.debug("POST request received: Verify SD-JWS")

    try:
        verify_request = SDJWSVerify(sd_jwt=body.sd_jws)
    except ValidationError as e:
        # Handle Pydantic validation error:
        error_msg = extract_validation_error_msg(e)
        error_msg = error_msg.replace("sd_jwt", "sd_jws")  # match the input field
        bound_logger.info(
            "Bad request: Validation error from SDJWSVerifyRequest body: {}", error_msg
        )
        raise CloudApiException(status_code=422, detail=error_msg) from e

    async with client_from_auth(auth) as aries_controller:
        verify_result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.wallet.verify_sd_jwt,
            body=verify_request,
        )

    result = SDJWSVerifyResponse(**verify_result.model_dump())
    bound_logger.debug("Successfully verified SD-JWS.")
    return result
