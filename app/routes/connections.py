from typing import List, Optional

from aries_cloudcontroller import CreateInvitationRequest, InvitationResult
from fastapi import APIRouter, Depends

from app.dependencies.acapy_clients import client_from_auth
from app.dependencies.auth import AcaPyAuth, acapy_auth_from_header
from app.exceptions import handle_acapy_call
from app.models.connections import AcceptInvitation, CreateInvitation
from shared.log_config import get_logger
from shared.models.connection_record import (
    Connection,
    Protocol,
    Role,
    State,
    conn_record_to_connection,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/connections", tags=["connections"])


@router.post("/create-invitation", response_model=InvitationResult)
async def create_invitation(
    body: Optional[CreateInvitation] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> InvitationResult:
    """
    Create connection invitation.
    -----------------------------
    This endpoint creates a new connection invitation.
    The other party can use this invitation to establish a connection.

    The multi_use parameter determines whether the invitation can be used multiple times.
    If multi_use is set to true, the invitation can be used multiple times, but the connection id
    will be different for each connection created using the invitation.

    The use_public_did parameter determines whether to use a public did for the invitation.
    If use_public_did is set to true, the tenant, that is creating the connection, needs a public did to create the invitation.

    Parameters:
    ------------
        alias: Optional[str]
            Alias for the connection invitation.
        multi_use: bool
            Whether the invitation can be used multiple times.
        use_public_did: bool
            Whether to use a public did for the invitation.

    Returns:
    ---------
        InvitationResult
            The invitation object.
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Create invitation")
    if body is None:
        body = CreateInvitation()

    async with client_from_auth(auth) as aries_controller:
        invitation = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.connection.create_invitation,
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
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> Connection:
    """
    Accept connection invitation.
    -----------------------------
    Tenants can use this endpoint to accept a connection invitation.
    The invitation object is obtained from the create_invitation endpoint.

    The invitation_url object in the invitation object can also be used to accept the invitation.
    The base64 encoded string just needs to be decoded into the invitation object.

    Parameters:
    ------------
        invitation: AcceptInvitation
            the invitation object obtained from create_invitation.

    Returns:
    ---------
        Connection
            The connection record.
    """
    bound_logger = logger.bind(body=body)
    bound_logger.info("POST request received: Accept invitation")
    async with client_from_auth(auth) as aries_controller:
        connection_record = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.connection.receive_invitation,
            body=body.invitation,
            auto_accept=True,
            alias=body.alias,
        )
    result = conn_record_to_connection(connection_record)
    bound_logger.info("Successfully accepted invitation.")
    return result


@router.get("", response_model=List[Connection])
async def get_connections(
    alias: Optional[str] = None,
    connection_protocol: Optional[Protocol] = None,
    invitation_key: Optional[str] = None,
    invitation_msg_id: Optional[str] = None,
    my_did: Optional[str] = None,
    state: Optional[State] = None,
    their_did: Optional[str] = None,
    their_public_did: Optional[str] = None,
    their_role: Optional[Role] = None,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> List[Connection]:
    """
    Retrieve list of connections records.
    --------------------------------------
    This endpoint retrieves a list of connection records.
    The connection records can be filtered by the parameters provided.

    Parameters:
    -----------
        alias: Optional[str]
        connection_protocol: Optional[Protocol]: "connections/1.0", "didexchange/1.0"
        invitation_key: Optional[str]
        invitation_msg_id: Optional[str]
        my_did: Optional[str]
        state: Optional[State]: "active", "response", "request", "start",
                                "completed", "init", "error", "invitation", "abandoned"
        their_did: Optional[str]
        their_public_did: Optional[str]
        their_role: Optional[Role]: "invitee", "requester", "inviter", "responder"

    Returns:
    ---------
        List[Connection]
            A list of connection records.
    """
    logger.info("GET request received: Get connections")

    async with client_from_auth(auth) as aries_controller:
        connections = await handle_acapy_call(
            logger=logger,
            acapy_call=aries_controller.connection.get_connections,
            alias=alias,
            connection_protocol=connection_protocol,
            invitation_key=invitation_key,
            invitation_msg_id=invitation_msg_id,
            my_did=my_did,
            state=state,
            their_did=their_did,
            their_public_did=their_public_did,
            their_role=their_role,
        )

    if connections.results:
        result = [
            conn_record_to_connection(connection) for connection in connections.results
        ]
        logger.info("Successfully returned connections.")
        return result

    logger.info("No connections returned.")
    return []


@router.get("/{connection_id}", response_model=Connection)
async def get_connection_by_id(
    connection_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
) -> Connection:
    """
    Retrieve connection record by id.
    ----------------------------------
    This endpoint retrieves a connection record by id.

    Parameters:
    -----------
        connection_id: str

    Returns:
    ---------
        Connection.
            A connection object.

    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("GET request received: Get connection by ID")
    async with client_from_auth(auth) as aries_controller:
        connection = await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.connection.get_connection,
            conn_id=connection_id,
        )

    result = conn_record_to_connection(connection)
    if result.connection_id:
        bound_logger.info("Successfully got connection by ID.")
    else:
        bound_logger.info("Could not get connection by ID.")
    return result


@router.delete("/{connection_id}", status_code=200)
async def delete_connection_by_id(
    connection_id: str,
    auth: AcaPyAuth = Depends(acapy_auth_from_header),
):
    """
    Delete connection record by id.
    -------------------------------
    This endpoint deletes a connection record by id.

    Parameters:
    -----------
        connection_id: str
    """
    bound_logger = logger.bind(body={"connection_id": connection_id})
    bound_logger.info("DELETE request received: Delete connection by ID")

    async with client_from_auth(auth) as aries_controller:
        await handle_acapy_call(
            logger=bound_logger,
            acapy_call=aries_controller.connection.delete_connection,
            conn_id=connection_id,
        )

    bound_logger.info("Successfully deleted connection by ID.")
    return {}  # todo change to 204 in next breaking release
