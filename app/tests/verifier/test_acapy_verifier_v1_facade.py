import pytest
from aries_cloudcontroller import AcaPyClient, IndyPresSpec, IndyProofRequest
from mockito import when

from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)

from .test_verifier_utils import (
    get,
    proof_dict,
    v10_presentation_exchange_records,
    v10_presentation_proposal_request,
)

from shared_models import PresentationExchange


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).create_proof_request(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    created_proof_request = await VerifierV1.create_proof_request(
        controller=mock_agent_controller,
        proof_request=CreateProofRequest(
            proof_request=IndyProofRequest(**proof_dict), comment=None
        ),
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

    created_proof_send_proposal = await VerifierV1.send_proof_request(
        controller=mock_agent_controller,
        proof_request=SendProofRequest(
            connection_id="abcde",
            proof_id=None,
            proof_request=v10_presentation_proposal_request,
        ),
    )

    assert isinstance(created_proof_send_proposal, PresentationExchange)

    with pytest.raises(NotImplementedError):
        await VerifierV1.send_proof_request(
            mock_agent_controller, proof_request="I am invalid", free=False
        )


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        get(v10_presentation_exchange_records[0])
    )

    accepted_proof_request = await VerifierV1.accept_proof_request(
        mock_agent_controller,
        proof_request=AcceptProofRequest(
            proof_id="v1-123",
            presentation_spec=IndyPresSpec(
                requested_attributes=[],
                requested_predicates=[],
                self_attested_attributes=[],
            ),
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

    deleted_proof_request = await VerifierV1.reject_proof_request(
        controller=mock_agent_controller,
        proof_request=RejectProofRequest(proof_id="v1-abc"),
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

    with pytest.raises(AttributeError):
        deleted_proof_request = await VerifierV1.reject_proof_request(
            controller=mock_agent_controller,
            proof_request="v1-abc",
        )
