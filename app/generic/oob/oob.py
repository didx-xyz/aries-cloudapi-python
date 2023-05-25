import logging
from typing import List, Optional

from aries_cloudcontroller import (AcaPyClient, InvitationMessage,
                                   InvitationRecord)
from aries_cloudcontroller.model.attachment_def import AttachmentDef
from aries_cloudcontroller.model.invitation_create_request import \
    InvitationCreateRequest
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import agent_selector
from shared_models import Connection, OobRecord, conn_record_to_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/oob", tags=["out-of-band"])


class ConnectToPublicDid(BaseModel):
    public_did: str


class CreateOobInvitation(BaseModel):
    alias: Optional[str] = None
    multi_use: Optional[bool] = None
    use_public_did: Optional[bool] = None
    attachments: Optional[List[AttachmentDef]] = None
    handshake_protocols: Optional[List[str]] = None
    create_connection: Optional[bool] = None


class AcceptOobInvitation(BaseModel):
    alias: Optional[str] = None
    use_existing_connection: Optional[bool] = None
    invitation: InvitationMessage


def strip_protocol_prefix(id: str):
    if id.startswith("v1-") or id.startswith("v2-"):
        return id[3:]
    else:
        return id


@router.post("/create-invitation", response_model=InvitationRecord)
async def create_oob_invitation(
    body: Optional[CreateOobInvitation] = None,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create connection invitation out-of-band.
    """
    if body is None:
        body = CreateOobInvitation()

    handshake_protocols = [
        "https://didcomm.org/didexchange/1.0",
        "https://didcomm.org/connections/1.0",
    ]

    if not body.create_connection and (
        not body.attachments or len(body.attachments) == 0
    ):
        raise HTTPException(
            400,
            "One or both of 'create_connection' and 'attachments' must be included",
        )

    if body.attachments:
        for item in body.attachments:
            item.id = strip_protocol_prefix(item.id)

    oob_body = InvitationCreateRequest(
        alias=body.alias,
        attachments=body.attachments,
        handshake_protocols=handshake_protocols if body.create_connection else None,
        use_public_did=body.use_public_did,
    )

    invitation = await aries_controller.out_of_band.create_invitation(
        multi_use=body.multi_use,
        body=oob_body,
        auto_accept=True,
    )
    # If the trust registry is not derived but an entity providing this information,
    # we should possibly write the (multi-use) invitation to the registry
    # We could also investigate storing the invitation URL with the OP's DID
    return invitation


@router.post("/accept-invitation", response_model=OobRecord)
async def accept_oob_invitation(
    body: AcceptOobInvitation,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Receive out-of-band invitation.
    """

    oob_record = await aries_controller.out_of_band.receive_invitation(
        auto_accept=True,
        use_existing_connection=body.use_existing_connection,
        alias=body.alias,
        body=body.invitation,
    )
    return oob_record


@router.post("/connect-public-did", response_model=Connection)
async def connect_to_public_did(
    body: ConnectToPublicDid,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Connect using public DID as implicit invitation.

    Parameters:
    ---
    their_public_did: str
        Public DID of target entity

    body: Optional[CreateConnFromDIDRequest]
        Additional request info

    Returns:
    ---
    ConnRecord
        The connection record
    """
    conn_record = await aries_controller.did_exchange.create_request(
        their_public_did=body.public_did
    )

    return conn_record_to_connection(conn_record)
