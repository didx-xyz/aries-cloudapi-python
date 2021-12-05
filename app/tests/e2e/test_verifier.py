import pytest
from aries_cloudcontroller import (
    IndyProofRequest,
)
from httpx import AsyncClient

from app.generic.verifier.models import ProofRequestProtocolVersion
from app.generic.verifier.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from app.tests.verifier.test_verifier_utils import proof_dict, indy_pres_spec
from app.tests.e2e.test_fixtures import *  # NOQA

BASE_PATH = "/generic/verifier"


def create_send_request(connection_id: str, protocol_version: str) -> SendProofRequest:
    return SendProofRequest(
        protocol_version=protocol_version,
        connection_id=connection_id,
        proof_request=IndyProofRequest(**proof_dict["proof_request"]),
    )


@pytest.mark.asyncio
async def test_send_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        connection_id=bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v10.value,
    )
    response = await alice_member_client.post(
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
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v20.value
    response = await alice_member_client.post(
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
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = CreateProofRequest(
        proof_request=IndyProofRequest(**proof_dict["proof_request"]),
        protocol_version=ProofRequestProtocolVersion.v10.value,
    )
    response = await alice_member_client.post(
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
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v20.value
    response = await alice_member_client.post(
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
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v10.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    accept_proof_request_v1 = AcceptProofRequest(
        protocol_version="v1",
        proof_id=proof_req_res.json()["proof_id"],
        presentation_spec=indy_pres_spec,
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=accept_proof_request_v1.dict(),
    )
    # TODO check for the correct response when state is request_received
    result = response.json()
    assert result["error_message"]
    assert ("Presentation exchange" and "state (must be request_received)") in result[
        "error_message"
    ]
    assert response.status_code == 400

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v20.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    accept_proof_request_v2 = AcceptProofRequest(
        protocol_version="v2",
        proof_id=proof_req_res.json()["proof_id"],
        presentation_spec=indy_pres_spec,
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=accept_proof_request_v2.dict(),
    )
    # TODO check for the correct response when state is request_received
    result = response.json()
    assert result["error_message"]
    assert ("Presentation exchange" and "state (must be request-received)") in result[
        "error_message"
    ]
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reject_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v10.value,
    )
    response = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    reject_proof_request_v1 = RejectProofRequest(
        proof_id=response.json()["proof_id"], problem_report=None
    )

    response = await alice_member_client.post(
        BASE_PATH + "/reject-request", json=reject_proof_request_v1.dict()
    )
    result = response.json()
    assert result is None
