import logging
import os
from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    ConnectionList,
    ConnRecord,
    CreateInvitationRequest,
    InvitationMessage,
    InvitationRecord,
    InvitationResult,
    ReceiveInvitationRequest,
)
from aries_cloudcontroller.model.invitation_create_request import (
    InvitationCreateRequest,
)
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import agent_selector

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "adminApiKey")


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/generic/connections", tags=["connections"])


class CreateConnFromDIDRequest(BaseModel):
    mediation_id: Optional[str] = None
    my_endpoint: Optional[str] = None
    my_label: Optional[str] = None
    use_public_did: Optional[bool] = None


# TODO this should be a post request
@router.get("/create-invite", response_model=InvitationResult)
async def create_invite(
    alias: Optional[str] = None,
    auto_accept: Optional[bool] = None,
    multi_use: Optional[bool] = None,
    public: Optional[bool] = None,
    create_invitation_request: Optional[CreateInvitationRequest] = {},
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invite.
    """
    invite = await aries_controller.connection.create_invitation(
        alias=alias,
        auto_accept=auto_accept,
        multi_use=multi_use,
        public=public,
        body=create_invitation_request,
    )
    return invite


@router.post("/accept-invite", response_model=ConnRecord)
async def accept_invite(
    invite: ReceiveInvitationRequest,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Accept connection invite.

    Parameters:
    ------------
    invite: ReceiveInvitationRequest
        the invitation object obtained from create_invite.
    """

    conn_record = await aries_controller.connection.receive_invitation(body=invite)
    return conn_record


@router.get("/", response_model=ConnectionList)
async def get_connections(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve list of connections.

    Returns:
    ---------
    JSON object with “connections” (key), a list of connections (ids)
    """
    connections = await aries_controller.connection.get_connections()
    return connections


@router.get("/{conn_id}", response_model=ConnRecord)
async def get_connection_by_id(
    conn_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve connection by id.

    Parameters:
    -----------
    conn_id: str

    """
    connection = await aries_controller.connection.get_connection(conn_id=conn_id)
    return connection


@router.delete("/{conn_id}")
async def delete_connection_by_id(
    conn_id: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
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
    remove_res = await aries_controller.connection.delete_connection(conn_id=conn_id)
    return remove_res


@router.post("/oob/create-invite", response_model=InvitationRecord)
async def create_invite_oob(
    alias: Optional[str] = None,
    auto_accept: Optional[bool] = None,
    multi_use: Optional[bool] = None,
    public: Optional[bool] = False,
    body: Optional[InvitationCreateRequest] = {},
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invite out-of-band.
    """
    body["alias"] = alias
    body["public"] = public
    body["use_public_did"] = False
    if "handshake_protocols" not in body.keys():
        body["handshake_protocols"] = [
            "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/didexchange/1.0"
        ]

    invite = await aries_controller.out_of_band.create_invitation(
        auto_accept=auto_accept,
        multi_use=multi_use,
        body=body,  # InvitationCreateRequest().dict(),
    )
    # If the trust registry is not derived but an entity providing this information,
    # we should possibly write the (multi-use) invite to the registry
    # We could also investigate storing the invitation URL with the OP's DID
    return invite


@router.post("/oob/receive-invite", response_model=ConnRecord)
async def receive_invite_oob(
    alias: Optional[str] = None,
    auto_accept: Optional[bool] = None,
    mediation_id: Optional[str] = None,
    use_existing_connection: Optional[bool] = None,
    body: Optional[InvitationMessage] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Receive connection invite out-of-band.
    """
    conn_record = await aries_controller.out_of_band.receive_invitation(
        alias=alias,
        auto_accept=auto_accept,
        mediation_id=mediation_id,
        use_existing_connection=use_existing_connection,
        body=body,
    )
    return conn_record


@router.post("/oob/connect-pub-did", response_model=ConnRecord)
async def oob_connect_via_pubdid(
    their_public_did: str,
    body: Optional[CreateConnFromDIDRequest] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Use a public DID as implicit invitation and connect.

    Parameters:
    -----------
    their_public_did: str
        The public did of the entity you want to connect to

    body: CreateConnFromDIDRequest (optional)
        Extra information about the connection request

    Returns:
    ------------
    ConnRecord
        The connection record
    """
    return await aries_controller.did_exchange.create_request(
        their_public_did=their_public_did, **body
    )
