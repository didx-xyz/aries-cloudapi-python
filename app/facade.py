import logging
import os
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

import requests
from fastapi import Header, HTTPException
from utils import controller_factory

T_co = TypeVar("T_co", contravariant=True)

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def create_controller(req_header: Header) -> Generic[T_co]:
    """
    Instantiate an AriesAgentController or a TenantController
    based on header attributes

    Parameters:
    -----------
    req_header: Header
        The header object containing (wallet_id, jwt_token) or api_key

    Returns:
    --------
    controller: Generic type of aries_cloudcontroller instance
        The AsyncContextMananger instance of the cloudcontroller
    """
    controller = controller_factory(req_header)
    try:
        yield controller
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error(f"{e!r}")
    finally:
        await controller.terminate()


async def create_did(controller: Generic[T_co]):
    """
    Creates a DID against the ledger using an AriesController

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    generate_did_response: dict
        The response object from generating a DID on the ledger
    """
    generate_did_res = await controller.wallet.create_did()
    if not generate_did_res["result"]:
        logger.error(f"Failed to create DID:\n{generate_did_res}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
        )
    return generate_did_res


async def post_to_ledger(url: str, payload):
    """
    Post the did payload to the ledger

    Parameters:
    -----------
    url: str
        The url of the ledger to post to
    payload: dict
        The payload to be posted of the form:
        {
            "network": "stagingnet",
            "did": did_object["did"],
            "verkey": did_object["verkey"],
            "paymentaddr": "somestring",
        }

    Returns:
    --------
    post_to_ledger_resp: dict
        The response object of the post request
    """
    post_to_ledger_resp = requests.post(url, data=payload.json(), headers={})

    if post_to_ledger_resp.status_code != 200:
        error_json = post_to_ledger_resp.json()
        logger.error(f"Failed to write to ledger:\n{error_json}")
        raise HTTPException(
            status_code=post_to_ledger_resp.status_code,
            detail=f"Something went wrong.\nCould not write to Ledger.\n{error_json}",
        )

    ledger_post_res = {
        "status_code": post_to_ledger_resp.status_code,
        "headers": post_to_ledger_resp.headers,
        "res_obj": post_to_ledger_resp.json(),
    }
    return ledger_post_res


async def get_taa(controller):
    """
    Obtains the TAA from the ledger

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    taa: dict
        The TAA object
    """
    taa_response = await controller.ledger.get_taa()
    logger.info(f"taa_response:\n{taa_response}")
    if not taa_response["result"]:
        error_json = taa_response.json()
        logger.error("Failed to get TAA:\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not get TAA. {error_json}",
        )
    taa = taa_response["result"]["taa_record"]
    taa["mechanism"] = "service_agreement"
    return taa


async def accept_taa(controller, TAA):
    """
    Accept the TAA

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    TAA:
        The TAA object we want to agree to

    Returns:
    --------
    accept_taa_response: {}
        The response from letting the ledger know we accepted the response
    """
    accept_taa_response = await controller.ledger.accept_taa(TAA)
    logger.info(f"accept_taa_response: {accept_taa_response}")
    if accept_taa_response != {}:
        error_json = accept_taa_response.json()
        logger.error(f"Failed to accept TAA.\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not accept TAA. {error_json}",
        )
    return accept_taa_response


async def assign_pub_did(controller, did_object):
    """
    Assigns a publich did

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    did_object:
        The DID response object from creating a did

    Returns:
    --------
    assign_pub_did_response: dict
        The response obejct from assigning a a public did
    """
    assign_pub_did_response = await controller.wallet.assign_public_did(
        did_object["did"]
    )
    logger.info(f"assign_pub_did_response:\n{assign_pub_did_response}")
    if not assign_pub_did_response["result"] or assign_pub_did_response["result"] == {}:
        error_json = assign_pub_did_response.json()
        logger.error(f"Failed to assign public DID:\n{error_json}")
        raise HTTPException(
            status_code=500,
            detail=f"Something went wrong.\nCould not assign DID. {error_json}",
        )
    return assign_pub_did_response


async def get_pub_did(controller):
    """
    Obtains the public DID

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    --------
    get_pub_did_response: dict
        The response from getting the public DID from the ledger
    """
    get_pub_did_response = await controller.wallet.get_public_did()
    logger.info(f"get_pub_did_response:\n{get_pub_did_response}")
    if not get_pub_did_response["result"] or get_pub_did_response["result"] == {}:
        error_json = get_pub_did_response.json()
        logger.error(f"Failed to get public DID:\n{error_json}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain public DID. {error_json}",
        )
    return get_pub_did_response


async def get_did_endpoint(controller, issuer_nym):
    """
    Obtains the public DID endpoint

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object
    issuer_nym: str
        The issuer's Verinym

    Returns:
    --------
    issuer_endpoint_response: dict
        The response from getting the public endpoint associated with
        the issuer's Verinym from the ledger
    """
    issuer_endpoint_response = await controller.ledger.get_did_endpoint(issuer_nym)
    if not issuer_endpoint_response:
        logger.error(f"Failed to get DID endpoint:\n{issuer_endpoint_response}")
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong. Could not obtain issuer endpoint.{issuer_endpoint_response}",
        )
    return issuer_endpoint_response


async def get_schema_attributes(controller, schema_id):
    """
    Obtains Schema Attributes

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns
    -------
    schema_attr :dict
    """

    schema_resp = await controller.schema.get_by_id(schema_id)
    if not schema_resp:
        raise HTTPException(
            status_code=404, detail="Could not find schema from provided ID"
        )
    schema_attr = schema_resp["schema"]["attrNames"]
    return schema_attr


async def write_credential_def(controller, schema_id):
    """
    Writes Credential Definition to the ledger

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    Schema id

    Returns:
    -------
    write_cred_response :dict
    """

    write_cred_response = await controller.definitions.write_cred_def(schema_id)
    if not write_cred_response:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not write credential definition to the ledger",
        )
    return write_cred_response


async def get_cred_def_id(controller, credential_def):
    """
    Obtains the credential definition id

    Parameters:
    ----------
    controller: AriesController
        The aries_cloudcontroller object

    credential_def : The credential definition whose id we wish to obtain

    Returns:
    -------
    cred_def_id : dict
        The credential definition id
    """

    # TODO Determine what is funky here?!
    cred_def_id = credential_def["credential_definition_id"]
    if not cred_def_id:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not find credential definition id from the provided credential definition",
        )
    return cred_def_id


async def issue_credentials(
    controller, connection_id, schema_id, cred_def_id, credential_attributes
):
    record = await controller.issuer.send_credential(
        connection_id, schema_id, cred_def_id, credential_attributes, trace=False
    )
    if not record:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Unable to issue credential."
        )
    # TODO DO we want to return the credential or just SUCCESS ?
    return record


async def get_connection_id(controller):
    """
    Obtains list existing connection ids

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns:
    -------
    connections: dict
        List of existing connections in
    """
    connections = await controller.connections.get_connections()
    if not connections:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain connections"
        )
    # TODO Return only the active connection id??
    return connections


async def get_schema_list(controller):
    """
    Obtains list of existing schemas

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    Returns
    -------
    created_schemas : dict
        List of schemas
    """
    created_schemas = await controller.schema.get_created_schema()
    if not created_schemas:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain schema list"
        )
    return created_schemas


async def write_schema_definition(controller, schema_definition_request):
    """
    Writes schema definition to the ledger

    Parameters:
    -----------
    controller: AriesController
        The aries_cloudcontroller object

    schema_definition_request : Contains the schema name,schema version, schema attributes

    Returns:
    --------
    write_schema_resp : dict

    """
    write_schema_resp = await controller.schema.write_schema(
        schema_definition_request.schema_name,
        schema_definition_request.schema_attrs,
        schema_definition_request.schema_version,
    )

    if not write_schema_resp or write_schema_resp == {}:
        raise HTTPException(
            status_code=404,
            detail=f"Something went wrong.\n Could not write schema to ledger.\n{schema}",
        )
    return write_schema_resp


# Need to rename this?
async def verify_proof_req(controller, presentation_exchange_id):

    verify = await controller.proofs.verify_presentation(presentation_exchange_id)

    if not verify:
        raise HTTPException(
            status_code=404,
            detail="Something went wrong. Could not verify proof request",
        )

    return verify


async def send_proof_request(controller, proof_request_web_request):

    response = await controller.proofs.send_request(proof_request_web_request)

    if not response:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not send proof request"
        )
