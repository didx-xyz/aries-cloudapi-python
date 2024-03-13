import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    V10PresentationSendRequestRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
)
from fastapi import HTTPException

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.verifier import router as verifier_router
from app.tests.util.ecosystem_connections import AcmeAliceConnect
from shared.util.rich_async_client import RichAsyncClient

VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize(
    "name, version, protocol_version",
    [
        ("Proof", None, "v1"),
        (None, "1.0", "v1"),
        (None, None, "v1"),
        ("Proof", None, "v2"),
        (None, "1.0", "v2"),
        (None, None, "v2"),
    ],
)
async def test_proof_model(
    issue_credential_to_alice: list,  # pylint: disable=unused-argument
    acme_acapy_client: AcaPyClient,
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    name: str,
    version: str,
    protocol_version: str,
):

    acme_connection_id = acme_and_alice_connection.acme_connection_id
    alice_listener = SseListener(topic="proofs", wallet_id=alice_tenant.wallet_id)

    if protocol_version == "v1":
        await acme_acapy_client.present_proof_v1_0.send_request_free(
            body=V10PresentationSendRequestRequest(
                auto_remove=False,
                connection_id=acme_connection_id,
                comment="Test proof",
                proof_request={
                    "name": name,
                    "version": version,
                    "requested_attributes": {
                        "THE_SPEED": {
                            "name": "speed",
                            "restrictions": [],
                        }
                    },
                    "requested_predicates": {},
                },
                auto_verify=True,
            )
        )
    else:
        await acme_acapy_client.present_proof_v2_0.send_request_free(
            body=V20PresSendRequestRequest(
                auto_remove=False,
                connection_id=acme_connection_id,
                comment="Test proof",
                presentation_request=V20PresRequestByFormat(
                    indy={
                        "name": name,
                        "version": version,
                        "requested_attributes": {
                            "THE_SPEED": {
                                "name": "speed",
                                "restrictions": [],
                            }
                        },
                        "requested_predicates": {},
                    },
                ),
                auto_verify=True,
            )
        )

    await alice_listener.wait_for_state(
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

    with pytest.raises(HTTPException) as exc:
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

    assert exc.value.status_code == 500
    assert ("Input error [missing field `version`]" in exc.value.detail) or (
        "Input error [missing field `name`]" in exc.value.detail
    )
