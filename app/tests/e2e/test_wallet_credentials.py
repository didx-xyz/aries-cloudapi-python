import logging
from typing import List

import pytest
from fastapi import HTTPException

from app.routes.wallet.credentials import router
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

WALLET_CREDENTIALS_PATH = router.prefix

logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_get_credentials(alice_member_client: RichAsyncClient):
    # Assert empty list is returned for empty wallet when fetching all credentials
    response = await alice_member_client.get(WALLET_CREDENTIALS_PATH)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_and_delete_credential_record(
    alice_member_client: RichAsyncClient,
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
):
    credentials_response = await alice_member_client.get(WALLET_CREDENTIALS_PATH)

    assert credentials_response.status_code == 200
    credentials_response = credentials_response.json()["results"]

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

    # Assert referent is no longer in credentials list
    credentials_response = (
        await alice_member_client.get(WALLET_CREDENTIALS_PATH)
    ).json()["results"]
    for cred in credentials_response:
        assert cred["referent"] != credential_id

    # Assert fetching deleted credential yields 404
    with pytest.raises(HTTPException) as exc:
        credentials_response = await alice_member_client.get(
            f"{WALLET_CREDENTIALS_PATH}/{credential_id}"
        )
    assert exc.value.status_code == 404


@pytest.mark.anyio
async def test_get_credential_record_with_limit(
    alice_member_client: RichAsyncClient,
    issue_alice_creds_non_revoke: List[  # pylint: disable=unused-argument
        CredentialExchange
    ],
):

    credentials_1 = (
        await alice_member_client.get(f"{WALLET_CREDENTIALS_PATH}?limit=5")
    ).json()

    assert len(credentials_1["results"]) == 5

    credentials_2 = (
        await alice_member_client.get(f"{WALLET_CREDENTIALS_PATH}?limit=5&offset=5")
    ).json()

    assert len(credentials_2["results"]) == 5
    assert credentials_1 != credentials_2

    credentials_3 = (
        await alice_member_client.get(f"{WALLET_CREDENTIALS_PATH}?limit=5")
    ).json()

    assert len(credentials_3["results"]) == 5
    assert credentials_1 == credentials_3
