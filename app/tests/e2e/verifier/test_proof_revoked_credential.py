import time
from typing import List

import pytest

from app.routes.issuer import router
from app.routes.verifier import router as verifier_router
from app.tests.util.ecosystem_connections import AcmeAliceConnect
from app.tests.util.verifier import send_proof_request
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

CREDENTIALS_BASE_PATH = router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_proof_revoked_credential(
    issue_alice_creds_and_revoke_published: List[  # pylint: disable=unused-argument
        CredentialExchange
    ],
    acme_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
    protocol_version: str,
):
    # Get current time
    unix_timestamp = int(time.time())

    # Do proof request
    request_body = {
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
    }
    send_proof_response = await send_proof_request(acme_client, request_body)
    acme_proof_exchange_id = send_proof_response["proof_id"]

    await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        look_back=5,
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

    await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": alice_proof_exchange_id,
        },
        look_back=5,
    )

    await check_webhook_state(
        client=acme_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": acme_proof_exchange_id,
        },
        look_back=5,
    )

    # Check proof
    proof = (
        await acme_client.get(f"{VERIFIER_BASE_PATH}/proofs/{acme_proof_exchange_id}")
    ).json()

    assert proof["verified"] is False
