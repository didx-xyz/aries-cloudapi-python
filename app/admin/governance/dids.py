import logging

from aries_cloudcontroller import AriesAgentControllerBase
from dependencies import yoma_agent
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/governance/dids", tags=["Admin: Public Dids"])


@router.get("/trusted-registry")
async def get_trusted_registry(
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Retrieve Trusted partner list from Trust Registry

    Parameters:
    -----------
    api_key: Header(None)
        The admin API key

    Returns:
    --------
    trusted_partners: [dict/JSON]
        List of unique trusted partners
    """
    all_dids_on_ledger = await aries_controller.wallet.get_dids()
    public_dids = []
    if len(all_dids_on_ledger["results"]) >= 1:
        public_dids = [
            r
            for r in all_dids_on_ledger["results"]
            if r["posture"] in ("public", "posted")
        ]
    return public_dids


@router.get("/trusted-registry/{partner_did}")
async def get_trusted_partner(
    partner_did: str,
    aries_controller: AriesAgentControllerBase = Depends(yoma_agent),
):
    """
    Retrieve Trusted partner from Trust Registry

    Parameters:
    -----------
    api_key: Header(None)
        The admin API key

    Returns:
    --------
    trusted_partner: dict/JSON
        Unique trusted partner endpoint and DID
    """
    return await aries_controller.wallet.get_did_endpoint(partner_did)


# TODO how do we want to delete a partner from the registry?
# Delete their wallet? Delte all their schemas?
# @router.delete("/trusted-registry/{partner_id}", tags=["did"])

# TODO update a partner on registry? Howto? Update their wallet? How or their schema(s)?
# If it's their schemas it should come from another endpoint
# @router.post("/trusted-registry/{partner_id}", tags=["did"])

# TODO Determine what (or even if) should be updated/whether that makes sense
# baceause what's written to the ledger si there
# @router.put("/trusted-registry/{partner_id}", tags=["did"])
