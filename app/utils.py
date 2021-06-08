from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException
from contextlib import asynccontextmanager
import json
import requests
import os
import logging

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_controller(req_header: Header):
    is_valid_header = req_header and (
        (("wallet_id" in req_header) and ("tenant_jwt" in req_header))
        or "api_key" in req_header
    )
    if is_valid_header:
        req_header = eval(req_header)
        if "api_key" in req_header:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            controller = AriesTenantController(
                admin_url=f"{admin_url}:{admin_port}",
                wallet_id=req_header["wallet_id"],
                tenant_jwt=req_header["tenant_jwt"],
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    try:
        yield controller
    except Exception as e:
        logger.error(f"{e!r}")
        if e.status:
            raise HTTPException(
                status_code=e.status,
                detail=e.message,
            ) from e
        else:
            raise e
    finally:
        await controller.terminate()


async def create_did(controller):
    generate_did_res = await controller.wallet.create_did()
    if not generate_did_res["result"]:
        raise HTTPException(
            # TODO: Should this return HTTPException, if so which status code?
            # Check same for occurences below
            status_code=404,
            detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
        )
    return generate_did_res


async def post_to_ledger(url, payload):
    r = requests.post(url, data=json.dumps(payload), headers={})
    if r.status_code != 200:
        error_json = r.json()
        raise HTTPException(
            status_code=r.status_code,
            detail=f"Something went wrong.\nCould not write to Ledger.\n{error_json}",
        )
    return r


async def get_taa(controller):
    taa_response = await controller.ledger.get_taa()
    logger.info(f"taa_response:\n{taa_response}")
    if not taa_response["result"]:
        error_json = taa_response.json()
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not get TAA. {error_json}",
        )
    TAA = taa_response["result"]["taa_record"]
    TAA["mechanism"] = "service_agreement"
    return TAA


async def accept_taa(controller, TAA):
    accept_taa_response = await controller.ledger.accept_taa(TAA)
    logger.info(f"accept_taa_response: {accept_taa_response}")
    if accept_taa_response != {}:
        error_json = accept_taa_response.json()
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {error_json}",
        )
    return accept_taa_response


async def assign_pub_did(controller, did_object):
    assign_pub_did_response = await controller.wallet.assign_public_did(
        did_object["did"]
    )
    logger.info(f"assign_pub_did_response:\n{assign_pub_did_response}")
    if not assign_pub_did_response["result"] or assign_pub_did_response["result"] == {}:
        error_json = assign_pub_did_response.json()
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong.\nCould not assign DID. {error_json}",
        )
    return assign_pub_did_response


async def get_pub_did(controller):
    get_pub_did_response = await controller.wallet.get_public_did()
    logger.info(f"get_pub_did_response:\n{get_pub_did_response}")
    if not get_pub_did_response["result"] or get_pub_did_response["result"] == {}:
        error_json = get_pub_did_response.json()
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain public DID. {error_json}",
        )
    return get_pub_did_response


async def get_did_endpoint(controller, issuer_nym):
    issuer_endpoint = await controller.ledger.get_did_endpoint(issuer_nym)
    if not issuer_endpoint:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not obtain issuer endpoint.",
        )
    return issuer_endpoint


async def get_schema_attributes(schema_id):
    schema_resp = await aries_agent_controller.schema.get_by_id(schema_id)
    if not schema_resp:
        raise HTTPException(
            status_code=404,
            detail="Could not find schema from provided ID",
        )
    schema_attr = schema_resp["schema"]["attrNames"]
    return schema_attr


async def write_credential_def(schema_id):
    write_cred_response = await aries_agent_controller.definitions.write_cred_def(
        schema_id
    )
    if not write_cred_response:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
        )
    return write_cred_response


async def get_cred_def_id(credential_def):
    cred_def_id = credential_def["credential_definition_id"]
    if not cred_def_id:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not find credential definition id from the provided credential definition",
        )
    return cred_def_id


async def issue_credential(
    connection_id, schema_id, cred_def_id, credential_attributes
):
    record = await aries_agent_controller.issuer.send_credential(
        connection_id, schema_id, cred_def_id, credential_attributes, trace=False
    )
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Unable to issue credential.",
        )
    # TODO DO we want to return the credential or just SUCCESS ?
    return record


async def get_connection_id(aries_agent_controller):
    connection = await aries_agent_controller.connections.get_connections()
    if not connection:
        raise HTTPException(
            status_code=404,
             detail="Something went wrong. Could not obtain connections",
        )
    # TODO Return only the active connection id??
    return connection
