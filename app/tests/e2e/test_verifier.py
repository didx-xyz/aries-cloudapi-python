from atexit import register
import time
from aries_cloudcontroller import IndyPresSpec, SchemaSendResult
import pytest
from assertpy import assert_that
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
from app.tests.verifier.test_verifier_utils import indy_pres_spec, indy_proof_request
from app.tests.e2e.test_fixtures import *
from shared_models.shared_models import CredentialExchange  # NOQA

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
    bob_and_alice_connection: BobAliceConnect,
    issue_credential_to_bob: CredentialExchange,
    alice_bob_connect_multi: BobAliceConnect,
    alice_member_client: AsyncClient,
    bob_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = alice_bob_connect_multi["alice_connection_id"]

    await register_verifier(alice_member_client, schema_id=schema_definition.schema_id)

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    # accept_proof_request_v1 = AcceptProofRequest(
    #     protocol_version="v1",
    #     proof_id=proof_req_res.json()["proof_id"],
    #     presentation_spec=indy_pres_spec,
    # )

    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "request-received"},
        topic="present_proof",
    )
    # TODO: fix this when merged with the webhooks stuff so we can properly fix this test
    proof_records_bob = await bob_member_client.get(BASE_PATH + "/proofs")
    proof_id = proof_records_bob.json()[0]["proof_id"]
    # assert proof_records_bob.json() == ""
    proof_record_bob = await alice_member_client.get(BASE_PATH + f"/proofs/{proof_id}")
    # assert proof_record_alice.json() == ""
    assert check_webhook_state(
        client=bob_member_client,
        filter_map={"state": "credential-acked"},
        topic="issue_credential",
    )
    bob_credentials = await bob_member_client.get("/generic/issuer/credentials")
    # assert bob_credentials.json() == ""
    bob_credential = bob_credentials.json()[0]
    # assert bob_credential == ""
    cred_id = bob_credential["credential_id"]
    print(f"\n\n\n\n Credential ID\n\n\n {cred_id} \n\n\n\n proof_id \n{proof_id}")
    proof_accept = AcceptProofRequest(
        proof_id=proof_id,
        presentation_spec=IndyPresSpec(
            requested_attributes={"speed": {"cred_id": cred_id}},
            requested_predicates={"speed": {"cred_id": cred_id}},
            self_attested_attributes={}
            # ** proof_record_alice.json()["presentation_request"],
        ),
    )
    # proof_accept.proof_id = proof_id

    response = await bob_member_client.post(
        BASE_PATH + "/accept-request",
        json=proof_accept.dict(),
    )
    # TODO check for the correct response when state is request_received
    result = response.json()

    print("\n\n\n\n\n SLEEEEEP \n\n\n\n\n")
    print(f"\n\n\n\n\n {bob_credential} \n\n\n\n\n")
    # time.sleep(300)
    assert result == ""
    assert response.status_code != 400
    # assert_that(result).contains("detail")
    # assert ("Presentation exchange" and "state (must be request_received)") in result[
    #     "detail"
    # ]

    # V2
    # proof_request_v2 = proof_request_v1
    # proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    # proof_req_res = await alice_member_client.post(
    #     BASE_PATH + "/send-request",
    #     json=proof_request_v2.dict(),
    # )

    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "request-sent"},
    #     topic="present_proof",
    # )

    # accept_proof_request_v2 = AcceptProofRequest(
    #     protocol_version="v2",
    #     proof_id=proof_req_res.json()["proof_id"],
    #     presentation_spec=indy_pres_spec,
    # )

    # response = await alice_member_client.post(
    #     BASE_PATH + "/accept-request",
    #     json=accept_proof_request_v2.dict(),
    # )

    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "request-sent"},
    #     topic="present_proof",
    # )

    # # TODO check for the correct response when state is request_received
    # result = response.json()
    # assert response.status_code == 400
    # assert_that(result).contains("detail")
    # assert ("Presentation exchange" and "state (must be request-received)") in result[
    #     "detail"
    # ]


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

    response = await alice_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()
    assert result == []

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()
    assert result == []
