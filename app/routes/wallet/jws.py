from aries_cloudcontroller import JWSCreate, JWSVerify
from fastapi import APIRouter, Depends
from pydantic import ValidationError

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import CloudApiException, handle_acapy_call
from app.models.jws import (
    JWSCreateRequest,
    JWSCreateResponse,
    JWSVerifyRequest,
    JWSVerifyResponse,
)
from app.util.extract_validation_error import extract_validation_error_msg
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
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> JWSCreateResponse:
    bound_logger = logger.bind(
        # Do not log payload:
        body=body.model_dump(exclude="payload")
    )
    bound_logger.debug("POST request received: Sign JWS")

    try:
        sign_request = JWSCreate(**body.model_dump())
    except ValidationError as e:
        # Handle Pydantic validation error:
        error_msg = extract_validation_error_msg(e)
        bound_logger.info(
            "Bad request: Validation error from JWSCreateRequest body: {}", error_msg
        )
        raise CloudApiException(status_code=422, detail=error_msg) from e

    async with client_from_auth(auth) as aries_controller:
        jws = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.wallet.sign_jwt,
            body=sign_request,
        )

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
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> JWSVerifyResponse:
    bound_logger = logger.bind(body=body)
    bound_logger.debug("POST request received: Verify JWS")

    try:
        verify_request = JWSVerify(jwt=body.jws)
    except ValidationError as e:
        # Handle Pydantic validation error:
        error_msg = extract_validation_error_msg(e)
        error_msg = error_msg.replace("jwt", "jws")  # match the input field
        bound_logger.info(
            "Bad request: Validation error from JWSVerifyRequest body: {}", error_msg
        )
        raise CloudApiException(status_code=422, detail=error_msg) from e

    async with client_from_auth(auth) as aries_controller:
        verify_result = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.wallet.verify_jwt,
            body=verify_request,
        )

    result = JWSVerifyResponse(**verify_result.model_dump())
    bound_logger.info("Successfully verified JWS.")
    return result
