import logging

import pytest
from fastapi import HTTPException

from app.routes.wallet.credentials import router
from shared import RichAsyncClient
from shared.models.topics.base import CredentialExchange

WALLET_CREDENTIALS_PATH = router.prefix

logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_get_credentials(alice_member_client: RichAsyncClient):
    # Assert empty list is returned for empty wallet when fetching all credentials
    response = await alice_member_client.get(WALLET_CREDENTIALS_PATH)

    assert response.status_code == 200
    response = response.json()
    logger.info("response: %s", response)
    assert response == {"results": []}


@pytest.mark.anyio
async def test_get_and_delete_credential_record(
    alice_member_client: RichAsyncClient, issue_credential_to_alice: CredentialExchange
):
    credentials_response = await alice_member_client.get(WALLET_CREDENTIALS_PATH)

    assert credentials_response.status_code == 200
    credentials_response = credentials_response.json()["results"]

    assert len(credentials_response) == 1

    credential_id = credentials_response[0]["referent"]
    # While in the broader context of Aries and credentials, referent can refer to specific attributes,
    # when dealing with the wallet's stored credentials, the referent becomes synonymous with a credential_id
    # specific to the wallet. It's how the wallet references and retrieves that particular credential record.

    fetch_response = await alice_member_client.get(
        f"{WALLET_CREDENTIALS_PATH}/{credential_id}"
    )
    assert fetch_response.status_code == 200
    fetch_response = fetch_response.json()
    logger.info("fetch_response: %s", fetch_response)

    # Assert we can delete this credential
    delete_response = await alice_member_client.delete(
        f"{WALLET_CREDENTIALS_PATH}/{credential_id}"
    )
    assert delete_response.status_code == 204

    # Assert credential list is now empty
    credentials_response = await alice_member_client.get(WALLET_CREDENTIALS_PATH)
    assert credentials_response.status_code == 200
    assert credentials_response.json() == {"results": []}

    # Assert fetching deleted credential yields 404
    with pytest.raises(HTTPException) as exc:
        credentials_response = await alice_member_client.get(
            f"{WALLET_CREDENTIALS_PATH}/{credential_id}"
        )
    assert exc.value.status_code == 404
