import time
from typing import List

import pytest

from app.models.tenants import CreateTenantResponse
from app.routes.issuer import router
from app.routes.verifier import router as verifier_router
from app.services.event_handling.sse_listener import SseListener
from app.tests.util.ecosystem_connections import AcmeAliceConnect
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_proof_revoked_credential(
    issue_alice_creds_and_revoke_published: List[  # pylint: disable=redefined-outer-name
        CredentialExchange
    ],
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
