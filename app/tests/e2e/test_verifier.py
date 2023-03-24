from aries_cloudcontroller import (
    IndyPresSpec,
    IndyRequestedCredsRequestedAttr,
)
import pytest
from assertpy import assert_that
from httpx import AsyncClient

from app.generic.verifier.models import (
    AcceptProofRequest,
    PresentProofProtocolVersion,
    RejectProofRequest,
    SendProofRequest,
)
from app.tests.util.ecosystem_personas import AcmeAliceConnect
from app.tests.util.webhooks import check_webhook_state
from app.tests.verifier.test_verifier_utils import indy_proof_request
from app.tests.e2e.test_fixtures import *
from shared_models.shared_models import CredentialExchange, PresentationExchange  # NOQA

import time

BASE_PATH = "/generic/verifier"


def create_send_request(
    connection_id: str, protocol_version: PresentProofProtocolVersion
) -> SendProofRequest:
    return SendProofRequest(
        protocol_version=protocol_version.value,
        connection_id=connection_id,
        proof_request=indy_proof_request,
    )


@pytest.mark.asyncio
async def test_accept_proof_request_v1(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: AsyncClient,
    acme_client: AsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
):
    response = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )
    response.raise_for_status()
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received"},
        topic="proofs",
        max_duration=240,
    )
    proof_records_alice = await alice_member_client.get(BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"/generic/verifier/proofs/{alice_proof_id}/credentials"
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=120,
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )

    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "done", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=240,
    )

    assert check_webhook_state(
        client=acme_client,
        filter_map={"state": "done", "proof_id": acme_proof_id},
        topic="proofs",
        max_duration=240,
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_accept_proof_request_oob_v1(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    acme_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
    acme_and_alice_connection: AcmeAliceConnect,
):
    # Create the proof request against aca-py
    response = await bob_member_client.post(
        BASE_PATH + "/create-request",
        json={
            "comment": "some comment",
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )
    response.raise_for_status()
    bob_exchange = response.json()

    bob_exchange["proof_id"] = bob_exchange["proof_id"]

    invitation_response = await bob_member_client.post(
        "/generic/oob/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [{"id": bob_exchange["proof_id"], "type": "present-proof"}],
        },
    )

    invitation_response.raise_for_status()

    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = (invitation_response.json())["invitation"]

    invitation["id"] = invitation.pop("@id")
    invitation["type"] = invitation.pop("@type")

    await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received"},
        topic="proofs",
        max_duration=240,
    )
    proof_records_alice = await alice_member_client.get(BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"/generic/verifier/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "presentation-sent", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=240,
    )

    # Add sleep of 5 seconds to ensure state change of proof response
    time.sleep(5)

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "done", "role": "verifier", "connection_id": None},
        topic="proofs",
        max_duration=240,
    )


@pytest.mark.asyncio
async def test_accept_proof_request_oob_v2(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    acme_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
    acme_and_alice_connection: AcmeAliceConnect,
):
    # Create the proof request against aca-py
    response = await bob_member_client.post(
        BASE_PATH + "/create-request",
        json={
            "comment": "some comment",
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )
    response.raise_for_status()
    bob_exchange = response.json()

    bob_exchange["proof_id"] = bob_exchange["proof_id"]

    invitation_response = await bob_member_client.post(
        "/generic/oob/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [{"id": bob_exchange["proof_id"], "type": "present-proof"}],
        },
    )

    invitation_response.raise_for_status()

    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = (invitation_response.json())["invitation"]

    invitation["id"] = invitation.pop("@id")
    invitation["type"] = invitation.pop("@type")

    await alice_member_client.post(
        "/generic/oob/accept-invitation",
        json={"invitation": invitation},
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received"},
        topic="proofs",
        max_duration=240,
    )
    proof_records_alice = await alice_member_client.get(BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"/generic/verifier/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "presentation-sent", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=240,
    )

    # Add sleep of 5 seconds to ensure state change of proof response
    time.sleep(5)

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "done", "role": "verifier", "connection_id": None},
        topic="proofs",
        max_duration=240,
    )


@pytest.mark.asyncio
async def test_accept_proof_request_v2(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: AsyncClient,
    acme_client: AsyncClient,
    alice_tenant: Any,
    acme_tenant: Any,
    credential_definition_id: str,
    acme_and_alice_connection: AcmeAliceConnect,
):
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )

    response = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            # Custom proof request because v2 doesn't support proof request without restrictions
            # see: https://github.com/hyperledger/aries-cloudagent-python/issues/1755
            "proof_request": {
                "name": "Proof Request",
                "version": "1.0.0",
                "requested_attributes": {
                    "0_speed_uuid": {
                        "name": "speed",
                        "restrictions": [{"cred_def_id": credential_definition_id}],
                    }
                },
                "requested_predicates": {},
            },
        },
    )
    response.raise_for_status()
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    payload = await wait_for_event(
        filter_map={
            "state": "request-received",
            "connection_id": acme_and_alice_connection["alice_connection_id"],
        }
    )

    alice_proof_id = payload["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"/generic/verifier/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=acme_tenant["tenant_id"]
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )

    await wait_for_event(
        filter_map={"proof_id": acme_proof_id, "state": "done", "verified": True}
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_send_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: AsyncClient,
    acme_client: AsyncClient,
    alice_tenant: Any,
):
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )
    response = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )

    result = response.json()

    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    # Wait for request received
    await wait_for_event(
        filter_map={
            "connection_id": acme_and_alice_connection["alice_connection_id"],
            "state": "request-received",
            "protocol_version": "v1",
        }
    )

    # V2
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )
    response = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]

    # Wait for request received
    await wait_for_event(
        filter_map={
            "connection_id": acme_and_alice_connection["alice_connection_id"],
            "state": "request-received",
            "protocol_version": "v2",
        }
    )


@pytest.mark.asyncio
async def test_reject_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: AsyncClient,
    alice_tenant: Any,
    acme_client: AsyncClient,
):
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )

    # V1
    response = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )
    response.raise_for_status()

    # Wait for request received
    alice_exchange = await wait_for_event(
        filter_map={
            "connection_id": acme_and_alice_connection["alice_connection_id"],
            "state": "request-received",
            "protocol_version": "v1",
        }
    )

    reject_proof_request_v1 = RejectProofRequest(
        proof_id=alice_exchange["proof_id"], problem_report=None
    )

    response = await alice_member_client.post(
        BASE_PATH + "/reject-request", json=reject_proof_request_v1.dict()
    )
    result = response.json()
    response.raise_for_status()
    assert result is None


@pytest.mark.asyncio
async def test_get_proof_single(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: AsyncClient
):
    # V1
    proof_req_res = await acme_client.post(
        f"{BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )

    proof_id = proof_req_res.json()["proof_id"]
    response = await acme_client.get(
        f"{BASE_PATH}/proofs/{proof_id}",
    )
    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "presentation_request" in result

    # V2
    proof_req_res = await acme_client.post(
        f"{BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )

    proof_id = proof_req_res.json()["proof_id"]

    response = await acme_client.get(
        f"{BASE_PATH}/proofs/{proof_id}",
    )

    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.asyncio
async def test_get_proofs_multi(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: AsyncClient
):
    # V1
    await acme_client.post(
        f"{BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )

    response = await acme_client.get(
        f"{BASE_PATH}/proofs",
    )

    result = response.json()[0]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v1-" in result["proof_id"]
    assert "presentation_request" in result

    # V2
    await acme_client.post(
        f"{BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )

    response = await acme_client.get(
        BASE_PATH + "/proofs",
    )

    result = response.json()[-1]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.asyncio
async def test_delete_proof(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: AsyncClient
):
    # V1
    proof_req_res = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await acme_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None

    # V2
    proof_req_res = await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await acme_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None


@pytest.mark.asyncio
async def test_get_credentials_for_request(
    acme_and_alice_connection: AcmeAliceConnect,
    acme_client: AsyncClient,
    alice_tenant: Any,
    alice_member_client: AsyncClient,
):
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )
    # V1
    await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v1",
            "proof_request": indy_proof_request.dict(),
        },
    )

    # Wait for request received
    alice_exchange = await wait_for_event(
        filter_map={
            "connection_id": acme_and_alice_connection["alice_connection_id"],
            "state": "request-received",
            "protocol_version": "v1",
        }
    )

    proof_id = alice_exchange["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs/{proof_id}/credentials",
    )

    result = response.json()[-1]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referent", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]

    # V2
    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=alice_tenant["tenant_id"]
    )
    await acme_client.post(
        BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection["acme_connection_id"],
            "protocol_version": "v2",
            "proof_request": indy_proof_request.dict(),
        },
    )

    # Wait for request received
    alice_exchange = await wait_for_event(
        filter_map={
            "connection_id": acme_and_alice_connection["alice_connection_id"],
            "state": "request-received",
            "protocol_version": "v2",
        }
    )
    proof_id = alice_exchange["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs/{proof_id}/credentials",
    )

    result = response.json()[-1]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referent", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]
