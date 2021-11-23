from typing import Any, Optional

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
    IndyProof,
    IndyPresSpec,
    IndyProofProof,
    IndyProofRequest,
    IndyProofRequestedProof,
    V10PresentationExchange,
    V10PresentationSendRequestRequest,
    V10PresentationProposalRequest,
)
from fastapi.exceptions import HTTPException
from mockito import when

from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.models import PresentationExchange


# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response


indy_proof = IndyProof(
    identifiers=[],
    proof=IndyProofProof(aggregated_proof=None, proofs=None),
    requested_proof=IndyProofRequestedProof(),
)

indy_proof_request = IndyProofRequest(
    name=None,
    non_revoked=None,
    nonce=None,
    requested_attributes=None,
    requested_predicates=None,
    version="0.0.1",
)

v10_presentation_exchange_records = [
    V10PresentationExchange(
        auto_present=False,
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        error_msg=None,
        initiator="self",
        presentation=indy_proof,
        presentation_exchange_id="dabc8f4e-164a-410f-bd10-471b090f65a5",
        presentation_proposal_dict=None,
        presentation_request=indy_proof_request,
        presentation_request_dict=None,
        role="prover",
        state=None,
        thread_id=None,
        trace=False,
        updated_at=None,
        verified="false",
    ),
]

v10_presentation_proposal_request = V10PresentationProposalRequest(
    connection_id="xyz",
    presentation_proposal=IndyPresPreview(
        attributes=[IndyPresAttrSpec(name="abc")],
        predicates=[IndyPresPredSpec(name="abc", predicate=">", threshold=1)],
    ),
    auto_present=True,
)

proof_dict = dict(
    {
        "connection_id": "string",
        "proof_request": {
            "name": "string",
            "non_revoked": {"from_": 0, "to": 0},
            "nonce": "12345",
            "requested_attributes": {
                "0_string_uuid": {
                    "name": "string",
                    "names": ["string"],
                    "non_revoked": {"from_": 0, "to": 0},
                    "restrictions": None,
                },
            },
            "requested_predicates": {
                "0_string_GE_uuid": {
                    "name": "string",
                    "p_type": "<",
                    "p_value": 0,
                    "non_revoked": {"from_": 0, "to": 0},
                    "restrictions": None,
                },
            },
            "version": "0.1",
        },
        "comment": "string",
        "trace": True,
    }
)


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).create_proof_request(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    created_proof_request = await ProofsV1.create_proof_request(
        controller=mock_agent_controller,
        proof_request=IndyProofRequest(**proof_dict),
        comment=None,
    )

    assert isinstance(created_proof_request, PresentationExchange)


@pytest.mark.asyncio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # Mock different functions on AcaPy client present proof api
    # proof interface decides upon params which methods it calls on the client
    # so let's mock those methods out
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )
    when(mock_agent_controller.present_proof_v1_0).send_proposal(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )
    when(mock_agent_controller.present_proof_v1_0).send_request(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )
    when(mock_agent_controller.present_proof_v1_0).send_request_free(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    created_proof_send_proposal = await ProofsV1.send_proof_request(
        controller=mock_agent_controller,
        proof_request=v10_presentation_proposal_request,
        proof_id=None,
    )

    assert isinstance(created_proof_send_proposal, PresentationExchange)

    created_proof_request_free = await ProofsV1.send_proof_request(
        controller=mock_agent_controller,
        proof_request=V10PresentationSendRequestRequest(
            connection_id="abc",
            proof_request=indy_proof_request,
        ),
        proof_id=None,
    )

    assert isinstance(created_proof_request_free, PresentationExchange)

    with pytest.raises(NotImplementedError):
        await ProofsV1.send_proof_request(
            mock_agent_controller, proof_request="I am invalid"
        )


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    accepted_proof_request = await ProofsV1.accept_proof_request(
        mock_agent_controller,
        proof_id="v1-123",
        body=IndyPresSpec(
            requested_attributes=[],
            requested_predicates=[],
            self_attested_attributes=[],
        ),
    )

    assert isinstance(accepted_proof_request, PresentationExchange)


@pytest.mark.asyncio
async def test_reject_proof_reject(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    deleted_proof_request = await ProofsV1.reject_proof_request(
        controller=mock_agent_controller, proof_id="v1-abc"
    )

    assert deleted_proof_request is None

    # Test exception handling when delete record returns rubbish
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        get("Something went wrong")
    )
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    with pytest.raises(HTTPException):
        deleted_proof_request = await ProofsV1.reject_proof_request(
            controller=mock_agent_controller, proof_id="v1-abc"
        )
