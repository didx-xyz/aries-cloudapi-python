import logging

from aries_cloudcontroller import AcaPyClient, CredentialDefinitionSendRequest
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from pydantic import BaseModel

from app.dependencies import agent_selector
from app.facades.trust_registry import TrustRegistryException, assert_valid_issuer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generic/defintions", tags=["definitions"])


class CreateCredentialDefinition(BaseModel):
    schema_id: str
    tag: str


@router.post("/credential")
async def create_credential_definition(
    definition: CreateCredentialDefinition,
    aries_controller: AcaPyClient = Depends(agent_selector),
):
    """
    Request for a credential defintion to be endorsed for writing to the ledger.

    Parameters:
    ------------
    definition: CreateCredentialDefinition
        credential defintion template

    Returns:
    --------
    The response object from creating a credential definition
    """

    # Assert the agent has a public did
    # TODO: extract to wallet (also duplicated in issuer)
    public_did = await aries_controller.wallet.get_public_did()
    if not public_did.result or not public_did.result.did:
        raise HTTPException(
            403,
            "Unable to create credential defintion without public did. Make sure to set the public did before creating a credential definition.",
        )

    # Make sure we are allowed to issue according to trust registry rules
    await assert_valid_issuer(f"did:sov:{public_did.result.did}", definition.schema_id)

    await aries_controller.credential_definition.publish_cred_def(
        create_transaction_for_endorser=True,
        body=CredentialDefinitionSendRequest(
            support_revocation=False, schema_id=definition.schema_id, tag=definition.tag
        ),
    )
