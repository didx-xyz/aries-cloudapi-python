from aries_cloudcontroller import (
    IndyPresSpec,
    IndyRequestedCredsRequestedAttr,
    SchemaSendResult,
)
import pytest
from httpx import AsyncClient

from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    ProofRequestProtocolVersion,
    RejectProofRequest,
    SendProofRequest,
)
from app.tests.util.event_loop import event_loop
from app.tests.util.trust_registry import register_verifier
from app.tests.util.webhooks import check_webhook_state
from app.tests.util.member_personas import (
    BobAliceConnect,
)
from app.tests.verifier.test_verifier_utils import indy_proof_request
from app.tests.e2e.test_fixtures import *
from shared_models.shared_models import CredentialExchange, PresentationExchange  # NOQA

BASE_PATH = "/generic/verifier"


def create_send_request(connection_id: str, protocol_version: str) -> SendProofRequest:
    return SendProofRequest(
        protocol_version=protocol_version,
        connection_id=connection_id,
        proof_request=indy_proof_request,
    )


@pytest.mark.asyncio
async def test_send_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
    bob_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        connection_id=bob_and_alice_connection["bob_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )

    await register_verifier(bob_member_client, schema_id=schema_definition.schema_id)

    response = await bob_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    result = response.json()

    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value
    response = await bob_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]


@pytest.mark.asyncio
async def test_create_proof_request(
    bob_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
):
    # V1
    proof_request_v1 = CreateProofRequest(
        proof_request=indy_proof_request,
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    await register_verifier(bob_member_client, schema_id=schema_definition.schema_id)

    response = await bob_member_client.post(
        BASE_PATH + "/create-request",
        json=proof_request_v1.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v1-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value
    response = await bob_member_client.post(
        BASE_PATH + "/create-request",
        json=proof_request_v2.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]


@pytest.mark.asyncio
async def test_accept_proof_request(
    issue_credential_to_bob: CredentialExchange,
    alice_bob_connect_multi: BobAliceConnect,
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
):
    # V1
    proof_request_v1 = create_send_request(
        alice_bob_connect_multi["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = alice_bob_connect_multi["alice_connection_id"]

    await register_verifier(alice_member_client, schema_id=schema_definition.schema_id)

    await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
        max_duration=30,
    )
    proof_records_bob = await bob_member_client.get(BASE_PATH + "/proofs")
    proof_id = proof_records_bob.json()[0]["proof_id"]

    requested_credentials = await bob_member_client.get(
        f"/generic/verifier/credentials/{proof_id}"
    )

    referent = requested_credentials.json()[0]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await bob_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )
    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
        max_duration=30,
    )

    result = response.json()

    pres_excheange_result = PresentationExchange(**result)
    assert isinstance(pres_excheange_result, PresentationExchange)
    assert response.status_code == 200

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof_v2_0",
    )

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="present_proof_v2_0",
    )
    proof_records_bob = (await bob_member_client.get(BASE_PATH + "/proofs")).json()
    proof_id = proof_records_bob[-1]["proof_id"]

    requested_credentials = (
        await bob_member_client.get(f"/generic/verifier/credentials/{proof_id}")
    ).json()

    referent = requested_credentials[0]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        protocol_version=ProofRequestProtocolVersion.v2.value,
        proof_id=proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await bob_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )
    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="present_proof_v2_0",
        max_duration=30,
    )

    result = response.json()

    pres_excheange_result = PresentationExchange(**result)
    assert isinstance(pres_excheange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reject_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    response = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    reject_proof_request_v1 = RejectProofRequest(
        proof_id=response.json()["proof_id"], problem_report=None
    )

    response = await alice_member_client.post(
        BASE_PATH + "/reject-request", json=reject_proof_request_v1.dict()
    )
    result = response.json()
    assert result is None


@pytest.mark.asyncio
async def test_get_proof_single(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v1.dict(),
    )

    proof_id = proof_req_res.json()["proof_id"]
    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs/{proof_id}",
    )
    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "presentation_request" in result

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = proof_req_res.json()["proof_id"]

    response = await alice_member_client.get(
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
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v1.dict(),
    )

    response = await alice_member_client.get(
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
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v2.dict(),
    )

    response = await alice_member_client.get(
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
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None


@pytest.mark.asyncio
async def test_get_credentials_for_request(
    alice_member_client: AsyncClient,
    bob_and_alice_connection: BobAliceConnect,
    bob_member_client: AsyncClient,
    issue_credential_to_bob: CredentialExchange,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="present_proof",
    )
    proof_records_bob = await bob_member_client.get(BASE_PATH + "/proofs")
    proof_id = proof_records_bob.json()[0]["proof_id"]

    response = await bob_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()[0]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referant", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]

    # # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof_v2_0",
    )

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="present_proof_v2_0",
    )
    proof_records_bob = await bob_member_client.get(BASE_PATH + "/proofs")
    proof_id = proof_records_bob.json()[-1]["proof_id"]

    response = await bob_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()[0]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referant", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]
