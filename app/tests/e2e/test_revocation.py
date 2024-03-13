import time

import pytest
from assertpy import assert_that
from fastapi import HTTPException

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.issuer import router
from app.routes.verifier import router as verifier_router
from app.tests.util.ecosystem_connections import AcmeAliceConnect
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
async def test_clear_pending_revokes(
    faber_client: RichAsyncClient,
    issue_alice_creds_and_revoke_unpublished: list,
):
    faber_cred_ex_id = issue_alice_creds_and_revoke_unpublished[0][
        "credential_id"
    ][3:]
    response = (
        await faber_client.get(
            f"{CREDENTIALS_BASE_PATH}/revocation/record"
            + "?credential_exchange_id="
            + faber_cred_ex_id
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

    for cred in issue_alice_creds_and_revoke_unpublished:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "issued"

    # Test for cred_rev_id not pending
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {rev_reg_id: ["1"]}},
        )
    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_clear_pending_revokes_no_map(
    faber_client: RichAsyncClient,
    issue_alice_creds_and_revoke_unpublished: list,
):
    clear_revoke_response = (
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/clear-pending-revocations",
            json={"revocation_registry_credential_map": {}},
        )
    ).json()["revocation_registry_credential_map"]

    assert clear_revoke_response == {}

    for cred in issue_alice_creds_and_revoke_unpublished:
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
                    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0": []
                }
            },
        )

    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_publish_all_revocations_for_rev_reg_id(
    faber_client: RichAsyncClient,
    issue_alice_creds_and_revoke_unpublished: list,
):
    faber_cred_ex_id = issue_alice_creds_and_revoke_unpublished[0][
        "credential_id"
    ][3:]
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

    for cred in issue_alice_creds_and_revoke_unpublished:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "revoked"


@pytest.mark.anyio
async def test_publish_all_revocations_no_payload(
    faber_client: RichAsyncClient,
    issue_alice_creds_and_revoke_unpublished: list,
):
    await faber_client.post(
        f"{CREDENTIALS_BASE_PATH}/publish-revocations",
        json={"revocation_registry_credential_map": {}},
    )

    for cred in issue_alice_creds_and_revoke_unpublished:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
            )
        ).json()

        assert rev_record["state"] == "revoked"


@pytest.mark.anyio
async def test_publish_one_revocation(
    faber_client: RichAsyncClient,
    issue_alice_creds_and_revoke_unpublished: list,
):
    faber_cred_ex_id = issue_alice_creds_and_revoke_unpublished[0][
        "credential_id"
    ][3:]
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

    for cred in issue_alice_creds_and_revoke_unpublished:
        rev_record = (
            await faber_client.get(
                f"{CREDENTIALS_BASE_PATH}/revocation/record"
                + "?credential_exchange_id="
                + cred["credential_id"][3:]
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

    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
async def test_publish_revocations_bad_payload(
    faber_client: RichAsyncClient,
):
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={"revocation_registry_credential_map": "bad"},
        )

    assert_that(exc.value.status_code).is_equal_to(422)

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={"revocation_registry_credential_map": {"bad": "bad"}},
        )

    assert_that(exc.value.status_code).is_equal_to(422)

    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            f"{CREDENTIALS_BASE_PATH}/publish-revocations",
            json={
                "revocation_registry_credential_map": {
                    "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0": []
                }
            },
        )

    assert_that(exc.value.status_code).is_equal_to(404)


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_proof_revoked_credential(
    issue_alice_creds_and_revoke_published: list,  # pylint: disable=unused-argument
    acme_client: RichAsyncClient,
    acme_verifier: CreateTenantResponse,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    acme_and_alice_connection: AcmeAliceConnect,
    protocol_version: str,
):

    alice_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.wallet_id
    )
    acme_proofs_listener = SseListener(
        topic="proofs", wallet_id=acme_verifier.wallet_id
    )

    # Get current time
    unix_timestamp = int(time.time())

    # Do proof request
    acme_proof_exchange_id = (
        await acme_client.post(
            f"{VERIFIER_BASE_PATH}/send-request",
            json={
                "protocol_version": protocol_version,
                "comment": "Test proof of revocation",
                "type": "indy",
                "indy_proof_request": {
                    "name": "Proof of SPEED",
                    "version": "1.0",
                    "non_revoked": {"to": unix_timestamp},
                    "requested_attributes": {
                        "THE_SPEED": {
                            "name": "speed",
                            "restrictions": [],
                        }
                    },
                    "requested_predicates": {},
                },
                "save_exchange_record": True,
                "connection_id": acme_and_alice_connection.acme_connection_id,
            },
        )
    ).json()["proof_id"]

    await alice_proofs_listener.wait_for_state(
        desired_state="request-received",
        lookback_time=5,
    )

    # Get proof exchange id
    alice_proof_exchange_id = (
        await alice_member_client.get(f"{VERIFIER_BASE_PATH}/proofs")
    ).json()[0]["proof_id"]

    # Get referent
    referent = (
        await alice_member_client.get(
            f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_exchange_id}/credentials"
        )
    ).json()[0]["cred_info"]["referent"]

    # Send proof
    await alice_member_client.post(
        f"{VERIFIER_BASE_PATH}/accept-request",
        json={
            "proof_id": alice_proof_exchange_id,
            "type": "indy",
            "indy_presentation_spec": {
                "requested_attributes": {
                    "THE_SPEED": {"cred_id": referent, "revealed": True}
                },
                "requested_predicates": {},
                "self_attested_attributes": {},
            },
            "dif_presentation_spec": {},
        },
    )

    await alice_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=alice_proof_exchange_id,
        desired_state="done",
        lookback_time=5,
    )
    await acme_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=acme_proof_exchange_id,
        desired_state="done",
        lookback_time=5,
    )

    # Check proof
    proof = (
        await acme_client.get(f"{VERIFIER_BASE_PATH}/proofs/{acme_proof_exchange_id}")
    ).json()

    assert proof["verified"] is False
