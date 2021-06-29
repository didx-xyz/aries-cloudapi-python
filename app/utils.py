import logging
import os
from typing import Type, Union, List, Dict, Generic, TypeVar
from contextlib import asynccontextmanager

import acapy_ledger_facade
import acapy_wallet_facade as wallet_facade
from schemas import DidCreationResponse
import ledger_facade
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException

T_co = TypeVar("T_co", contravariant=True)
admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)

logger = logging.getLogger(__name__)


def get_controller_type(auth_headers) -> Union[str, None]:
    """
    Validates the passed in request header to verify is has correct attributes
    api_key or (tenant_jwt and wallet_id)

    Parameters:
    -----------
    auth_headers: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    "admin", "tenant", or None: Union[str, None]
        (One of) the appropriate type(s) for the controller based on the headers provided
    """
    if auth_headers.get("api_key", None):
        return "admin"
    elif auth_headers.get("wallet_id", None) and auth_headers.get("tenant_jwt", None):
        return "tenant"
    return None


def controller_factory(
    auth_headers,
) -> Type[Union[AriesAgentController, AriesTenantController]]:
    """
    Aries Controller factory returning an
    AriesController object based on a request header

    Parameters:
    -----------
    auth_headers: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    controller: AriesCloudController (object)
    """
    controller_type = get_controller_type(auth_headers)
    if not controller_type:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    if controller_type == "admin":
        return AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=auth_headers["api_key"],
            is_multitenant=is_multitenant,
        )
    else:
        return AriesTenantController(
            admin_url=f"{admin_url}:{admin_port}",
            wallet_id=auth_headers["wallet_id"],
            tenant_jwt=auth_headers["tenant_jwt"],
        )


def construct_zkp(zero_knowledge_proof: List[dict], schema_id: str) -> list:
    if zero_knowledge_proof == [{}]:
        return []
    req_preds = []
    [
        req_preds.append(
            {
                "name": item["name"],
                "p_type": item["p_type"],
                "p_value": item["p_value"],
                "restrictions": [{"schema_id": schema_id}],
            }
        )
        for item in zero_knowledge_proof
    ]
    return req_preds


def construct_indy_proof_request(
    name_proof_request: str, schema_id: str, attr_req, req_preds
):
    indy_proof_request = {
        "name": name_proof_request,
        "version": schema_id.split(":")[-1],
        "requested_attributes": {
            f"0_{req_attr['name']}_uuid": req_attr for req_attr in attr_req
        },
        "requested_predicates": {
            f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
        },
    }
    return indy_proof_request


@asynccontextmanager
async def create_controller(auth_headers) -> Generic[T_co]:
    """
    Instantiate an AriesAgentController or a TenantController
    based on header attributes

    Parameters:
    -----------
    auth_header: dict
        The header object containing wallet_id and jwt_token, or api_key

    Returns:
    --------
    controller: Generic type of aries_cloudcontroller instance
        The AsyncContextMananger instance of the cloudcontroller
    """
    controller = controller_factory(auth_headers)
    try:
        yield controller
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        # yes but we are _not_ providing this context managed resource via a fast api dependency so there's no reason
        # not to raise the exception
        logger.error(f"{e!r}")
        raise e
    finally:
        await controller.terminate()


async def create_pub_did(req_header: Dict[str, str]) -> DidCreationResponse:
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    # TODO Can we break down this endpoint into smaller functions?
    # Because this really is too complex/too much happening at once.
    # This way not really testible/robust
    async with create_controller(req_header) as aries_agent_controller:
        # TODO: Should this come from env var or from the client request?
        # Adding empty header as parameters are being sent in payload
        generate_did_res = await wallet_facade.create_did(aries_agent_controller)
        did_object = generate_did_res["result"]
        await ledger_facade.post_to_ledger(
            did_object=did_object, ledger_url=req_header.get("ledger_url", None)
        )

        taa_response = await acapy_ledger_facade.get_taa(aries_agent_controller)

        await acapy_ledger_facade.accept_taa(aries_agent_controller, taa_response)
        await wallet_facade.assign_pub_did(aries_agent_controller, did_object["did"])
        get_pub_did_response = await wallet_facade.get_pub_did(aries_agent_controller)
        issuer_nym = get_pub_did_response["result"]["did"]
        issuer_verkey = get_pub_did_response["result"]["verkey"]
        issuer_endpoint = await acapy_ledger_facade.get_did_endpoint(
            aries_agent_controller, issuer_nym
        )
        issuer_endpoint_url = issuer_endpoint["endpoint"]
        final_response = DidCreationResponse(
            did_object=get_pub_did_response["result"],
            issuer_verkey=issuer_verkey,
            issuer_endpoint=issuer_endpoint_url,
        )
        return final_response
