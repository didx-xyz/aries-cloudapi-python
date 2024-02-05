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

    clear_revoke_response = (
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {rev_reg_id: []}},
        )
    ).json()["revocation_registry_credential_map"]

    assert clear_revoke_response == {}

    for cred in issue_revocable_credentials_to_alice_and_revoke:

        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "issued"


@pytest.mark.anyio
async def test_clear_pending_revokes_no_map(
    faber_client: RichAsyncClient, issue_revocable_credentials_to_alice_and_revoke: list
):

    clear_revoke_response = (
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {}},
        )
    ).json()["revocation_registry_credential_map"]

    assert clear_revoke_response == {}

    for cred in issue_revocable_credentials_to_alice_and_revoke:

        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "issued"


@pytest.mark.anyio
async def test_clear_pending_revokes_bad_payload(
    faber_client: RichAsyncClient,
):
    with pytest.raises(HTTPException) as exc:

        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": "bad"},
        )

    assert_that(exc.value.status_code).is_equal_to(422)

    with pytest.raises(HTTPException) as exc:

        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {"bad": "bad"}},
        )

    assert_that(exc.value.status_code).is_equal_to(422)

    with pytest.raises(HTTPException) as exc:

        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={
                "revocation_registry_credential_map": {
                    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0": [
                        "bad"
                    ]
                }
            },
        )

    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_publish_all_revocations_for_rev_reg_id(
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

    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/publish-revocations",
        json={"revocation_registry_credential_map": {rev_reg_id: []}},
    )

    for cred in issue_revocable_credentials_to_alice_and_revoke:

        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "revoked"
