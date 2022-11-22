import logging
from typing import Any, Dict, Optional
from aiohttp import ClientResponseError

from aries_cloudcontroller import (
    AcaPyClient,
    Doc,
    SignRequest,
    SignResponse,
    SignatureOptions,
    VerifyRequest,
    VerifyResponse,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector
from app.error.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/jsonld", tags=["jsonld"])


class JsonLdSignRequest(BaseModel):
    credential_id: Optional[str]
    credential: Optional[Dict[str, Any]]
    verkey: Optional[str] = None
    pub_did: Optional[str] = None
    signature_options: Optional[SignatureOptions] = None


class JsonLdVerifyRequest(BaseModel):
    signed_doc: Dict[str, Any]
    their_pub_did: Optional[str] = None
    verkey: Optional[str] = None


@router.post("/sign", response_model=SignResponse)
async def sign_jsonld(
    body: JsonLdSignRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Sign a JSON-LD structure
    """

    if body.pub_did and body.verkey:
        raise CloudApiException(
            "Please provide either or neither, but not both, public did of the verkey or the verkey for the document.",
            418,
        )
    try:
        if body.verkey:
            verkey = body.verkey
        else:
            if body.pub_did:
                pub_did = body.pub_did
            else:
                pub_did = (await aries_controller.wallet.get_public_did()).result.did
            verkey = (await aries_controller.ledger.get_did_verkey(did=pub_did)).verkey

        if not body.credential:
            if body.credential_id:
                # Can this ever be correct as in are there jsonLD credential potentially being returned?
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

        return await aries_controller.jsonld.sign(
            body=SignRequest(
                doc=Doc(credential=credential, options=body.signature_options),
                verkey=verkey,
            )
        )
    except ClientResponseError as e:
        raise CloudApiException(f"Failed to sign payload. {e['message']}")


@router.post("/verify", response_model=VerifyResponse)
async def verify_jsonld(
    body: JsonLdVerifyRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Verify a JSON-LD structure
    """

    if not (bool(body.their_pub_did) != bool(body.verkey)):
        raise CloudApiException(
            "Please provide either, but not both, public did of the verkey or the verkey for the document.",
            418,
        )
    try:
        if not body.verkey:
            their_verkey = (
                await aries_controller.ledger.get_did_verkey(did=body.their_pub_did)
            ).verkey
        else:
            their_verkey = body.verkey

        # TODO: fixme below
        # FIXME: Aca-py returns not enough values to unpack (expected 1, got 0) even for a presumably valid jsonld
        # Example taken from aca-py aries_cloudagent/messaging/jsonld/tests/test_routes.py mock_sign_request() and request_body()
        # When this is fixed it should return something like 204 None for valid or raise an error otherwise.
        return await aries_controller.jsonld.verify(
            body=VerifyRequest(
                doc=body.signed_doc,
                verkey=their_verkey,
            )
        )
    except ClientResponseError as e:
        raise CloudApiException(f"Failed to verify payload. {e['message']}")
