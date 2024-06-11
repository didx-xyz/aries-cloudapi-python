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
)
async def sign_jws(
    body: JWSCreateRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> JWSCreateResponse:
    """
    Sign JSON Web Signature (JWS)
    ---

    This endpoint allows the user to sign a json payload into a Json Web Signature (JWS)
    using a DID or a verification method.

    When populating the the body of the request, the user must populate either the `did`
    or the `verification_method` field.

    If an issuer sings a JWS with a `did:sov` DID, the did should be public.

    The difference between the did and verification_method fields is
    that if the `did` field is used, the Aries agent will make an educated guess
    about which key associated with the did to use to sign the jwt, i.e. the did with the key to use.

    While with the `verification_method` field, the user is explicitly
    specifying which key to use to sign the jwt.

    The `header` field is optional and can be used to specify the header of the JWS.
    The `typ`, `alg`, and `kid` fields are automatically populated by the Aries agent.

    See https://www.rfc-editor.org/rfc/rfc7515.html for the JWS spec.

    Example request body:
    ---
    ```
    {
        "did": "did:sov:WWMjrBJkUzz9suEtwKxmiY", <-- Public did of issuer
        "payload": {
            "credential_subject":"reference_to_holder",
            "name":"Alice",
            "surname":"Demo"
        }
    }
    ```
    OR
    ```
    {
        "payload": {
            "subject":"reference_to_holder",
            "name":"Alice",
            "surname":"Demo"
        },
        "verification_method": "did:key:z6Mkprf81ujG1n48n5LMD...M6S3#z6Mkprf81ujG1n48n5LMDaxyCLLFrnqCRBPhkTWsPfA8M6S3"
    }
    ```


    Request body:
    ---
        JWSCreateRequest:
            did: str:
              The DID to sign the JWS with.
            headers: Optional(dict):
              The header of the JWS.
            payload: dict:
              The payload of the JWS.
            verification_method: str:
              The verification (did with key) method to use.

    Returns:
    ---
        JWSCreateResponse:
          The signed JWS string representing the signed JSON Web Signature.
    """
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
    bound_logger.debug("Successfully signed JWS.")
    return result


@router.post(
    "/verify",
    response_model=JWSVerifyResponse,
    summary="Verify JWS",
)
async def verify_jws(
    body: JWSVerifyRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> JWSVerifyResponse:
    """
    Verify JSON Web Signature (JWS)
    ---

    This endpoint allows the user to verify and decode the JWS string gotten from the sign endpoint.
    Passing the JWS string to this endpoint will return the payload and headers of the JWS.

    It will also return the validity of the JWS.

    See https://www.rfc-editor.org/rfc/rfc7515.html for the JWS spec.

    Request body:
    ---
        JWSVerifyRequest: The JWS to verify.
            jws: str

    Returns:
    ---
        JWSVerifyResponse
            payload: dict:
              The payload of the JWS.
            headers: dict:
              The headers of the JWS.
            kid: str:
              The key id of the signer.
            valid: bool:
              Whether the JWS is valid.
            error: str:
              The error message if the JWS is invalid.
    """
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
    bound_logger.debug("Successfully verified JWS.")
    return result
