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
)
async def sign_sd_jws(
    body: SDJWSCreateRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> SDJWSCreateResponse:
    """
    Sign Selective Disclosure for JWS (SD-JWS)
    ---

    This endpoint allows the user to sign a Selective Disclosure for JWS (SD-JWS).
    The endpoint returns an SD-JWS that can be used to selectively disclose attributes
    to a verifier.

    When populating the body of the request, the user must provide either the
    did or the verification_method field.

    If an issuer signs a JWS with a did:sov DID, the DID must be public.

    The difference between the did and verification_method fields is:

     - If the did field is used, the Aries agent will make an educated guess about
       which verkey associated with the DID to use for signing the JWT.
     - If the verification_method field is used, the user explicitly specifies which
       verkey to use for signing the JWT, i.e., the DID with the associated key.

    The header field is optional and can be used to specify the header of the JWS.
    The typ, alg, and kid fields in the header are automatically populated by the Aries agent.

    The non_sd_list field is a list of non-selective disclosure attributes.
    These attributes are not included in the selective disclosure; i.e., they are always disclosed.
    If an attribute is a list or a dictionary, the attribute name should be included
    in the non_sd_list.
    In such cases, the attribute itself will be disclosed in the SD-JWS, but not
    the values in the list or the key-value pairs in the dictionary.

    Values in a list can be added to the non_sd_list by including the attribute
    name and the range of the list in the following format:

    "<attribute_name>[start:end]"

     - start is the start of the range as a int.
     - end is the end of the range (exclusive).

    Values in a dictionary can be added to the non_sd_list by specifying the
    dictionary name followed by the attribute name in the following format:

    "<dictionary_name>.<attribute_name>"

     - <dictionary_name> is the name of the dictionary.
     - <attribute_name> is the attribute name within the dictionary.

    The endpoint will return the signed SD-JWS along with the disclosures needed
    to reveal the attributes in the SD-JWS:

    <Issuer-signed JWS>~<Disclosure 1>~<Disclosure 2>~...~<Disclosure N>

    It is the holder’s responsibility to identify which disclosure corresponds to
    which attributes in the SD-JWS.
    The holder must provide the SD-JWS with the appropriate disclosures to the
    verifier upon request.

    See https://www.ietf.org/archive/id/draft-ietf-oauth-selective-disclosure-jwt-07.html
    for the SD-JWT / SD-JWS spec.

    Example request body:
    ---
    ```
        {
          "did": "did:sov:39TXHazGAYif5FUFCjQhYX",  < --- Public did of issuer
          "payload": {
           ""credential_subject": "reference_to_holder",
           "given_name": "John",
           "family_name": "Doe",
           "email": "johndoe@example.com",
           "phone_number": "+1-202-555-0101",
           "nationalities": ["a","b","c","d"],
           "address": {
             "street_address": "123 Main St",
             "locality": "Anytown",
             "region": "Anystate",
             "country": "US"
           },
           "birthdate": "1940-01-01"
          },
          "non_sd_list": [
            "given_name",
            "address",
            "address.street_address",
            "nationalities",
            "nationalities[1:3]"
          ]
        }
    ```

    Request body:
    ---
        SDJWSCreateRequest: The SD-JWS to sign.
            did: str:
              The DID to sign the SD-JWS with.
            headers: dict:
              The header of the SD-JWS.
            payload: dict:
              The payload of the SD-JWS.
            verification_method:
              str: The verification method (did with verkey) to use.
            non_sd_list: Optional(list):
              List of non-selective disclosure attributes.

    Returns:
    ---
        SDJWSCreateResponse:
          The signed SD-JWS followed by the disclosures.
    """
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
)
async def verify_sd_jws(
    body: SDJWSVerifyRequest,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> SDJWSVerifyResponse:
    """
    Verify Selective Disclosure JWS (SD-JWS)
    ---

    This endpoint allows the user to verify a Selective Disclosure JWS (SD-JWS).
    The validity of the SD-JWS is checked and the disclosures are returned.

    The SD-JWS followed by the disclosures are passed to this endpoint and should be in the format:
        `<Issuer-signed JWS>~<Disclosure 1>~<Disclosure 2>~...~<Disclosure N>~`
    Where each disclosure will reveal its associated attribute.
    The holder only needs to reveal the disclosures that the verifier requests,
    and can keep the rest of the disclosures secret.

    See https://www.ietf.org/archive/id/draft-ietf-oauth-selective-disclosure-jwt-07.html
    for the SD-JWT / SD-JWS spec.

    Request body:
    ---
        SDJWSVerifyRequest:
            sd_jws: str:
              The SD-JWS and disclosures to verify and reveal.

    Returns:
    ---
        SDJWSVerifyResponse:
          The validity of the SD-JWS and the selectively disclosed attributes.
    """
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
