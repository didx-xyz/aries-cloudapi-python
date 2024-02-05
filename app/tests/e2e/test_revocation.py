from fastapi import HTTPException

import pytest
from shared import RichAsyncClient
from assertpy import assert_that
from app.routes.issuer import router

CREDENTIALS_BASE_PATH = router.prefix


@pytest.mark.anyio
async def test_clear_pending_revokes(
    faber_client: RichAsyncClient, issue_revocable_credentials_to_alice_and_revoke: list
):

    response = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/revocation/record"
            + "?credential_exchange_id="
            + issue_revocable_credentials_to_alice_and_revoke[0]["credential_id"][3:]
        )
    ).json()

    rev_reg_id = response["rev_reg_id"]
    clear_revoke_response = (
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {rev_reg_id: ["1"]}},
        )
    ).json()["revocation_registry_credential_map"]

    for key in clear_revoke_response:
        assert len(clear_revoke_response[key]) == 2
