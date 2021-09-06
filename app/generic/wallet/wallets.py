import logging

from fastapi import APIRouter, Depends
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.model.did_endpoint_with_type import DIDEndpointWithType

from schemas import (
    DidCreationResponse,
)
from acapy_ledger_facade import create_pub_did
from dependencies import agent_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/create-pub-did", tags=["did"], response_model=DidCreationResponse)
async def create_public_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Parameters:
    -----------
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    return await create_pub_did(aries_controller)


@router.get("/create-local-did")
async def create_local_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Create Local DID
    """

    return await aries_controller.wallet.create_did(body={})


@router.get("/list-dids")
async def list_dids(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Retrieve list of DIDs.
    """
    return await aries_controller.wallet.get_dids()


@router.get("/fetch-current-did")
async def fetch_current_did(
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Fetch the current public DID.
    """
    return await aries_controller.wallet.get_public_did()


@router.patch("/rotate-keypair")
async def rotate_keypair(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):

    return await aries_controller.wallet.rotate_keypair(did)


@router.get("/get-did-endpoint/{did}")
async def get_did_endpoint(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Get DID endpoint.
    """
    return await aries_controller.wallet.get_did_endpoint(did=did)


@router.get("/assign-pub-did")
async def assign_pub_did(
    did: str,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Assign the current public DID

    Parameter:
    ----------
    did: str
    """
    return await aries_controller.wallet.set_public_did(did=did)


@router.post("/set-did-endpoint")
async def set_did_endpoint(
    did: str,
    endpoint: str,
    endpoint_type="Endpoint",
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Update Endpoint in wallet and on ledger if posted to it.

    Parameters:
    ------------
    did: str
    endpoint: str
    """
    return await aries_controller.wallet.set_did_endpoint(
        body=DIDEndpointWithType(
            did=did, endpoint=endpoint, endpoint_type=endpoint_type
        )
    )
