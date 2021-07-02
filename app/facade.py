import logging
import os
from fastapi import HTTPException
from typing import Generic, TypeVar, Callable
from contextlib import asynccontextmanager

import requests
from fastapi import HTTPException, Header
from utils import controller_factory, ControllerType


T_co = TypeVar("T_co", contravariant=True)
logger = logging.getLogger(__name__)

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", None)


def _yoma_factory(x_api_key: str = Header(None), authorization: str = None):
    # these two args are _required_ - this method is a factory method
    return controller_factory(
        controller_type=ControllerType.YOMA_AGENT, x_api_key=x_api_key
    )


def _member_factory(x_api_key: str = Header(None), authorization: str = None):
    # these two args are _required_ - this method is a factory method
    return controller_factory(
        ControllerType.MEMBER_AGENT,
        x_api_key=EMBEDDED_API_KEY,
        authorization_header=authorization,
    )


def _admin_member_factory(x_api_key: str = Header(None), authorization: str = None):
    # these two args are _required_ - this method is a factory method
    return controller_factory(
        ControllerType.MEMBER_ADMIN_AGENT,
        x_api_key=EMBEDDED_API_KEY,
        authorization_header=authorization,
    )


agent_creators = {
    ControllerType.MEMBER_AGENT: _member_factory,
    ControllerType.YOMA_AGENT: _yoma_factory,
    ControllerType.ECOSYSTEM_AGENT: _member_factory,
    ControllerType.MEMBER_ADMIN_AGENT: _admin_member_factory,
    ControllerType.ECOSYSTEM_ADMIN_AGENT: _admin_member_factory,
}


def agent_fun_creator(controller_type: ControllerType):
    # slightly unorthodox I know - the alternative is to have code duplication...
    async def create(x_api_key: str = Header(None), authorization: str = None):
        controller = None
        try:
            agent_creator = agent_creators[controller_type]
            controller = agent_creator(x_api_key, authorization)
            yield controller
        except Exception as e:
            # We can only log this here and not raise an HTTPExeption as
            # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
            logger.error("%s", e, exc_info=e)
            raise e
        finally:
            if controller:
                await controller.terminate()

    return create


yoma_agent = agent_fun_creator(ControllerType.YOMA_AGENT)
ecosystem_agent = agent_fun_creator(ControllerType.ECOSYSTEM_AGENT)
member_agent = agent_fun_creator(ControllerType.MEMBER_AGENT)
ecosystem_admin_agent = agent_fun_creator(ControllerType.ECOSYSTEM_ADMIN_AGENT)
member_admin_agent = agent_fun_creator(ControllerType.MEMBER_ADMIN_AGENT)
ecosystem_or_member_agent = None


async def agent_creator(
    controller_type: ControllerType,
    x_api_key: str = Header(None),
    authorization: str = None,
):
    try:
        if controller_type == ControllerType.MEMBER_AGENT:
            controller = controller_factory(
                controller_type=ControllerType.MEMBER_AGENT,
                x_api_key=EMBEDDED_API_KEY,
                authorization_header=authorization,
            )
        elif controller_type == ControllerType.ECOSYSTEM_AGENT:
            controller = controller_factory(
                controller_type=ControllerType.ECOSYSTEM_AGENT,
                x_api_key=EMBEDDED_API_KEY,
                authorization_header=authorization,
            )
        elif controller_type == ControllerType.YOMA_AGENT:
            controller = controller_factory(
                controller_type=ControllerType.YOMA_AGENT,
                x_api_key=x_api_key,
            )
        elif controller_type == ControllerType.ECOSYSTEM_ADMIN_AGENT:
            controller = controller_factory(
                controller_type=ControllerType.ECOSYSTEM_ADMIN_AGENT,
                x_api_key=x_api_key,
            )
        elif controller_type == ControllerType.MEMBER_ADMIN_AGENT:
            controller = controller_factory(
                controller_type=ControllerType.MEMBER_ADMIN_AGENT,
                x_api_key=x_api_key,
            )
        else:
            logger.error("unknown controller type")
            raise HTTPException(500, f"Unknown controller type {controller_type}")
        yield controller
    except Exception as e:
        # We can only log this here and not raise an HTTPExeption as
        # we are past the yield. See here: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#dependencies-with-yield-and-httpexception
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        if controller:
            await controller.terminate()


@asynccontextmanager
async def create_controller(
    controller_type: ControllerType,
    x_api_key=None,
    jwt_token=None,
) -> Generic[T_co]:

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
    controller = controller_factory(
        controller_type=controller_type, x_api_key=x_api_key
    )
    try:
        yield controller
    except Exception as e:
        logger.error("%s", e, exc_info=e)
        raise e
    finally:
        await controller.terminate()


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

    return response


async def remove_wallet(controller, wallet_id):

    response = await controller.multitenant.remove_subwallet_by_id(wallet_id)

    if not response:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not remove wallet."
        )
    return response


async def get_auth_token_by_id(controller, wallet_id):

    response = await controller.multitenant.get_subwallet_authtoken_by_id(wallet_id)

    if not response:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not get auth_token."
        )
    return response


async def update_subwallet_via_id(controller, wallet_id, payload):

    update = await controller.multitenant.update_subwallet_by_id(payload, wallet_id)

    if not update:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not update subwallet."
        )
    return update


async def get_subwallet_by_id(controller, wallet_id):

    subwallet = await controller.multitenant.get_single_subwallet_by_id(wallet_id)

    if not subwallet:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not obtain subwallet. "
        )

    return subwallet


async def query_subwallet_ids(controller, wallet_name):

    query = await controller.multitenant.query_subwallets(wallet_name)

    if not query:
        raise HTTPException(
            status_code=404, detail="Something went wrong. Could not query subwallets."
        )

    return query
