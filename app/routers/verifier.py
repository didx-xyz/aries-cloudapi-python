import logging
import time
import traceback
from typing import List, Optional

from facade import (
    create_controller,
    get_schema_attributes,
    send_proof_request,
    verify_proof_req,
)
from fastapi import APIRouter, Header, HTTPException, Query
from utils import construct_indy_proof_request, construct_zkp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verifier")


# TODO verify that active connection exists
# Better tag?
@router.post("/request-proof-for-schema", tags=["proof", "verifier"])
async def get_proof_request(
    connection_id: str,
    schema_id: str,
    name_proof_request: str,
    zero_knowledge_proof: List[dict] = None,
    requested_attrs: List[str] = Query(None),
    self_attested: List[str] = None,
    revocation: int = None,
    exchange_tracing: bool = False,
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Request proof of a (sub) set of attributes against a schema by ID.
    This may contain zero-knowledge attributes.
    This may contain revocation of the proof.

    Parameters:
    -----------
    connection_id: str
    schema_id: str
    name_proof_request: str
    zero_knowledge_proof: Dict = None
    requested_attrs: List[str] = Query(None)
    self_attested: List[
        str
    ] = None,
    revocation: int = None,
    exchange_tracing: bool = False,
    req_header: Optional[str] = Header(None),

    Returns:
    --------
    presentation_exchange_id: json
        The presentation exchange ID JSON object
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:
            schema_resp = await get_schema_attributes(controller, schema_id)
            is_attrs_match = all(x in schema_resp for x in requested_attrs)
            if not is_attrs_match:
                raise HTTPException(
                    status_code=400,
                    detail="Requested attributes not a (sub) set of schema attributes.",
                )
            attr_req = [
                {"name": k, "restrictions": [{"schema_id": schema_id}]}
                for k in requested_attrs
            ]
            revocation_attributes = []
            if revocation and len(revocation_attributes) > 0:
                [
                    attr_req.append(
                        {
                            "name": rev_attr,
                            "restrictions": [{"schema_id": schema_id}],
                            "non_revoked": {"to": int(time.time() - 1)},
                        }
                    )
                    for rev_attr in revocation_attributes
                ]

            if self_attested:
                [attr_req.append({"name": att}) for att in self_attested]

            req_preds = construct_zkp(zero_knowledge_proof, schema_id)

            indy_proof_request = construct_indy_proof_request(
                name_proof_request, schema_id, attr_req, req_preds
            )
            if revocation:
                indy_proof_request["non_revoked"] = {"to": int(time.time())}

            proof_request_web_request = {
                "connection_id": connection_id,
                "proof_request": indy_proof_request,
                "trace": exchange_tracing,
            }

            response = await send_proof_request(controller, proof_request_web_request)

            presentation_exchange_id = response["presentation_exchange_id"]

            return presentation_exchange_id
    except Exception as e:
        logger.error(f"Failed to request proof: \n {e}")
        raise e


@router.get("/verify-proof-request", tags=["verifier", "proof"])
async def verify_proof_request(
    presentation_exchange_id: str,
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Verify a proof request against the ledger

    Parameters:
    -----------
    presentation_exchange_id: str
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    --------
    verify: dict
        The json representation of the verify request
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:
            verify = await verify_proof_req(controller, presentation_exchange_id)

            if not verify["state"] == "verified":
                raise HTTPException(
                    status_code=400,
                    detail="Presentation state not verified!",
                )
            return verify
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to verify proof request. THe following error occured:\n{e!r}\n{err_trace}"
        )
        raise e
