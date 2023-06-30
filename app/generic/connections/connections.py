from typing import List, Optional

from aries_cloudcontroller import (
    CreateInvitationRequest,
    InvitationResult,
    ReceiveInvitationRequest,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config.log_config import get_logger
from app.dependencies.auth import AcaPyAuth, acapy_auth, client_from_auth
from shared import Connection, conn_record_to_connection

logger = get_logger(__name__)

router = APIRouter(prefix="/generic/connections", tags=["connections"])


class ConnectToPublicDid(BaseModel):
    public_did: str


class CreateInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None


class AcceptInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: ReceiveInvitationRequest


@router.post("/create-invitation", response_model=InvitationResult)
async def create_invitation(
    body: Optional[CreateInvitation] = None,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Create connection invitation.
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Create invitation")
    if body is None:
        body = CreateInvitation()

    async with client_from_auth(auth) as aries_controller:
        invitation = await aries_controller.connection.create_invitation(
            alias=body.alias,
            auto_accept=True,
            multi_use=body.multi_use,
            public=body.use_public_did,
            body=CreateInvitationRequest(),
        )
    bound_logger.info("Successfully created invitation.")
    return invitation


@router.post("/accept-invitation", response_model=Connection)
async def accept_invitation(
    body: AcceptInvitation,
    auth: AcaPyAuth = Depends(acapy_auth),
) -> Connection:
    """
    Accept connection invitation.

    Parameters:
    ------------
    invitation: ReceiveInvitationRequest
        the invitation object obtained from create_invitation.
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Accept invitation")
    async with client_from_auth(auth) as aries_controller:
        connection_record = await aries_controller.connection.receive_invitation(
            body=body.invitation,
            auto_accept=True,
            alias=body.alias,
        )
    result = conn_record_to_connection(connection_record)
    bound_logger.info("Successfully accepted invitation.")
    return result


@router.get("", response_model=List[Connection])
async def get_connections(
    auth: AcaPyAuth = Depends(acapy_auth),
) -> List[Connection]:
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with connections (key), a list of connections (ids)
    """
    logger.info("GET request received: Get connections")

    async with client_from_auth(auth) as aries_controller:
        connections = await aries_controller.connection.get_connections()

        if connections.results:
            result = [
                conn_record_to_connection(connection)
                for connection in connections.results
            ]
            logger.info("Successfully returned connections.")
            return result

    logger.info("No connections returned.")
    return []


@router.get("/{connection_id}", response_model=Connection)
async def get_connection_by_id(
    connection_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Retrieve connection by id.

    Parameters:
    -----------
    connection_id: str

    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("GET request received: Get connection by ID")
    async with client_from_auth(auth) as aries_controller:
        connection = await aries_controller.connection.get_connection(
            conn_id=connection_id
        )
    result = conn_record_to_connection(connection)
    if result.connection_id:
        bound_logger.info("Successfully got connection by ID.")
    else:
        bound_logger.info("Could not get connection by ID.")
    return result


@router.delete("/{connection_id}")
async def delete_connection_by_id(
    connection_id: str,
    auth: AcaPyAuth = Depends(acapy_auth),
):
    """
    Delete connection by id.

    Parameters:
    -----------
    connection_id: str

    Returns:
    ------------
    Empty dict: {}
    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("DELETE request received: Delete connection by ID")

    async with client_from_auth(auth) as aries_controller:
        await aries_controller.connection.delete_connection(conn_id=connection_id)
    # TODO what if id not found?
    bound_logger.info("Successfully deleted connection by ID.")
    return {}
