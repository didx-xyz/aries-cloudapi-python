from typing import Any, Dict, Optional

from aiohttp import ClientResponseError
from aries_cloudcontroller import (
    Doc,
    SignatureOptions,
    SignRequest,
    SignResponse,
    VerifyResponse,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from uplink import Body, Consumer, json, post, returns

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth
from app.exceptions.cloud_api_error import CloudApiException
from shared.log_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generic/jsonld", tags=["jsonld"])


class JsonLdSignRequest(BaseModel):
    credential_id: Optional[str]
    credential: Optional[Dict[str, Any]]
    verkey: Optional[str] = None
    pub_did: Optional[str] = None
    signature_options: Optional[SignatureOptions] = None


class JsonLdVerifyRequest(BaseModel):
    doc: Dict[str, Any]
    public_did: Optional[str] = None
    verkey: Optional[str] = None


# NOTE: Wrong/incomplete aca-py openAPI spec results in wrong/overly-strict model for controller endpoint
# Hence, custom override api endpoint that is incorrect in aca-py
class JsonldApi(Consumer):
    async def verify(
        self, *, body: Optional[JsonLdVerifyRequest] = None
    ) -> VerifyResponse:
        """Verify a JSON-LD structure."""
        return await self.__verify(
            body=body,
        )

    @returns.json
    @json
    @post("/jsonld/verify")
    def __verify(self, *, body: Body(type=JsonLdVerifyRequest) = {}) -> VerifyResponse:
        """Internal uplink method for verify"""


@router.post("/sign", response_model=SignResponse)
async def sign_jsonld(
    body: JsonLdSignRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Sign a JSON-LD structure
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Sign JsonLD")

    if body.pub_did and body.verkey:
        bound_logger.info("Bad request: both public did and verkey provided.")
        raise CloudApiException(
            "Please provide either or neither, but not both, public did of the verkey or the verkey for the document.",
            400,
        )
    try:
        async with client_from_auth(auth) as aries_controller:
            if body.verkey:
                verkey = body.verkey
            else:
                if body.pub_did:
                    pub_did = body.pub_did
                else:
                    bound_logger.debug("Fetching public DID")
                    pub_did = (
                        await aries_controller.wallet.get_public_did()
                    ).result.did
                bound_logger.debug("Fetching verkey for DID")
                verkey = (
                    await aries_controller.ledger.get_did_verkey(did=pub_did)
                ).verkey

            if not body.credential:
                if body.credential_id:
                    # Can this ever be correct as in are there jsonLD credential potentially being returned?
                    bound_logger.debug("Fetching credential from wallet")
                    credential = (
                        await aries_controller.credentials.get_record(
                            credential_id=body.credential_id
                        )
                    ).dict()
                else:
                    raise CloudApiException(
                        "Cannot retrieve credential without credential ID."
                    )
            else:
                credential = body.credential

            bound_logger.debug("Signing JsonLD")
            result = await aries_controller.jsonld.sign(
                body=SignRequest(
                    doc=Doc(credential=credential, options=body.signature_options),
                    verkey=verkey,
                )
            )
    except ClientResponseError as e:
        logger.warning(
            "A ClientResponseError was caught while signing jsonld. The error message is: '{}'.",
            e.message,
        )
        raise CloudApiException("Failed to sign payload.") from e

    if result:
        bound_logger.info("Successfully signed JsonLD.")
    else:
        bound_logger.warning("No result from signing JsonLD.")
    return result


@router.post("/verify", status_code=204)
async def verify_jsonld(
    body: JsonLdVerifyRequest,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Verify a JSON-LD structure
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Verify JsonLD")

    if not bool(body.public_did) != bool(body.verkey):
        bound_logger.info("Bad request: both public did and verkey provided.")
        raise CloudApiException(
            "Please provide either, but not both, public did of the verkey or the verkey for the document.",
            400,
        )
    try:
        async with client_from_auth(auth) as aries_controller:
            if not body.verkey:
                bound_logger.debug("Fetching verkey for DID")
                verkey = (
                    await aries_controller.ledger.get_did_verkey(did=body.public_did)
                ).verkey
            else:
                verkey = body.verkey

            aries_controller.jsonld = JsonldApi(
                base_url=aries_controller.base_url, client=aries_controller.client
            )
            bound_logger.debug("Verifying JsonLD")
            jsonld_verify_response = await aries_controller.jsonld.verify(
                body=JsonLdVerifyRequest(doc=body.doc, verkey=verkey)
            )
            if not jsonld_verify_response.valid:
                raise CloudApiException(
                    f"Failed to verify payload with error message: `{jsonld_verify_response.error}`.",
                    422,
                )
    except ClientResponseError as e:
        logger.warning(
            "A ClientResponseError was caught while verifying jsonld. The error message is: '{}'.",
            e.message,
        )
        raise CloudApiException("Failed to verify payload.") from e

    bound_logger.info("Successfully verified JsonLD.")
