from typing import List

import pytest
from fastapi import HTTPException

from app.routes.issuer import router
from app.routes.verifier import router as verifier_router
from app.tests.util.regression_testing import TestMode
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix

skip_regression_test_reason = "Skip publish-revocations in regression mode"


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_clear_pending_revokes(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    faber_cred_ex_id = revoke_alice_creds[0].credential_exchange_id
    revocation_record_response = await faber_client.get(
        f"{CREDENTIALS_BASE_PATH}/revocation/record"
        + "?credential_exchange_id="
        + faber_cred_ex_id
    )

    rev_reg_id = revocation_record_response.json()["rev_reg_id"]
    cred_rev_id = revocation_record_response.json()["cred_rev_id"]

    clear_revoke_response = await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
        json={"revocation_registry_credential_map": {rev_reg_id: [cred_rev_id]}},
    )
    revocation_registry_credential_map = clear_revoke_response.json()[
        "revocation_registry_credential_map"
    ]

    for key in revocation_registry_credential_map:
        assert (
            len(revocation_registry_credential_map[key]) >= 2
        ), "We expect at least two cred_rev_ids per rev_reg_id after revoking one"

    clear_revoke_response = await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
        json={"revocation_registry_credential_map": {rev_reg_id: []}},
    )
    revocation_registry_credential_map = clear_revoke_response.json()[
        "revocation_registry_credential_map"
    ]

    # assert revocation_registry_credential_map == {} #todo: aca-py now provides response

    for cred in revoke_alice_creds:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred.credential_exchange_id
            )
        ).json()

        assert rev_record["state"] == "issued"

    # Test for cred_rev_id not pending
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {rev_reg_id: [cred_rev_id]}},
        )
    assert exc.value.status_code == 404


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_clear_pending_revokes_no_map(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    # clear_revoke_response = (
    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
        json={"revocation_registry_credential_map": {}},
    )
    # ).json()["revocation_registry_credential_map"]

    # assert clear_revoke_response == {} #todo: aca-py now provides response

    for cred in revoke_alice_creds:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred.credential_exchange_id
            )
        ).json()

        assert rev_record["state"] == "issued"


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_clear_pending_revokes_bad_payload(
    faber_client: RichAsyncClient,
):
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": "bad"},
        )

    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {"bad": "bad"}},
        )

    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={
                "revocation_registry_credential_map": {
                    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0": []
                }
            },
        )

    assert exc.value.status_code == 404


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_publish_all_revocations_for_rev_reg_id(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    faber_cred_ex_id = revoke_alice_creds[0].credential_exchange_id
    response = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/revocation/record"
            + "?credential_exchange_id="
            + faber_cred_ex_id
        )
    ).json()

    rev_reg_id = response["rev_reg_id"]

    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/publish-revocations",
        json={"revocation_registry_credential_map": {rev_reg_id: []}},
    )

    for cred in revoke_alice_creds:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred.credential_exchange_id
            )
        ).json()

        assert rev_record["state"] == "revoked"


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_publish_all_revocations_no_payload(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/publish-revocations",
        json={"revocation_registry_credential_map": {}},
    )

    for cred in revoke_alice_creds:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred.credential_exchange_id
            )
        ).json()

        assert rev_record["state"] == "revoked"


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_publish_one_revocation(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    faber_cred_ex_id = revoke_alice_creds[0].credential_exchange_id
    response = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/revocation/record"
            + "?credential_exchange_id="
            + faber_cred_ex_id
        )
    ).json()

    rev_reg_id = response["rev_reg_id"]
    cred_rev_id = response["cred_rev_id"]
    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/publish-revocations",
        json={"revocation_registry_credential_map": {rev_reg_id: [cred_rev_id]}},
    )

    for cred in revoke_alice_creds:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred.credential_exchange_id
            )
        ).json()

        if rev_record["cred_rev_id"] == cred_rev_id:
            assert rev_record["state"] == "revoked"
        else:
            assert rev_record["state"] == "issued"

    # Test for cred_rev_id not pending
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={"revocation_registry_credential_map": {rev_reg_id: [cred_rev_id]}},
        )

    assert exc.value.status_code == 404


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_publish_revocations_bad_payload(
    faber_client: RichAsyncClient,
):
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={"revocation_registry_credential_map": "bad"},
        )

    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={"revocation_registry_credential_map": {"bad": "bad"}},
        )

    assert exc.value.status_code == 422

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={
                "revocation_registry_credential_map": {
                    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0": []
                }
            },
        )

    assert exc.value.status_code == 404


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_get_pending_revocations(
    faber_client: RichAsyncClient,
    revoke_alice_creds: List[CredentialExchange],
):
    faber_cred_ex_id = revoke_alice_creds[0].credential_exchange_id
    revocation_record_response = await faber_client.get(
        f"{CREDENTIALS_BASE_PATH}/revocation/record"
        + "?credential_exchange_id="
        + faber_cred_ex_id
    )

    rev_reg_id = revocation_record_response.json()["rev_reg_id"]

    pending_revocations = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/get-pending-revocations/{rev_reg_id}"
        )
    ).json()["pending_cred_rev_ids"]

    assert (
        len(pending_revocations) >= 3
    )  # we expect at least 3 cred_rev_ids can be more if whole module is run

    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
        json={"revocation_registry_credential_map": {}},
    )

    pending_revocations = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/get-pending-revocations/{rev_reg_id}"
        )
    ).json()["pending_cred_rev_ids"]

    assert pending_revocations == []


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason=skip_regression_test_reason,
)
async def test_get_pending_revocations_bad_payload(
    faber_client: RichAsyncClient,
):
    with pytest.raises(HTTPException) as exc:
        await faber_client.get(f"{CREDENTIALS_BASE_PATH}/get-pending-revocations/bad")

    assert exc.value.status_code == 422
