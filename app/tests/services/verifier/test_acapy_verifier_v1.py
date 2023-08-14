import pytest
from aries_cloudcontroller import AcaPyClient, IndyPresSpec
from mockito import when

from app.routes.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from app.services.verifier.acapy_verifier_v1 import VerifierV1
from app.tests.util.mock import to_async
from app.tests.verifier.utils import (
    indy_proof_request,
    v10_presentation_exchange_records,
)
from shared.models.protocol import PresentProofProtocolVersion
from shared.models.topics import PresentationExchange


@pytest.mark.anyio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).create_proof_request(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    created_proof_request = await VerifierV1.create_proof_request(
        controller=mock_agent_controller,
        create_proof_request=CreateProofRequest(
            proof_request=indy_proof_request,
            comment=None,
            protocol_version=PresentProofProtocolVersion.v1,
        ),
    )

    assert isinstance(created_proof_request, PresentationExchange)


@pytest.mark.anyio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # Mock different functions on AcaPy client present proof api
    # proof interface decides upon params which methods it calls on the client
    # so let's mock those methods out
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        v10_presentation_exchange_records[0]
    )  # todo: all of the mocks with to_async removed are unnecessary and have no effect
    when(mock_agent_controller.present_proof_v1_0).send_proposal(...).thenReturn(
        v10_presentation_exchange_records[0]
    )
    when(mock_agent_controller.present_proof_v1_0).send_request(...).thenReturn(
        v10_presentation_exchange_records[0]
    )
    when(mock_agent_controller.present_proof_v1_0).send_request_free(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    created_proof_send_proposal = await VerifierV1.send_proof_request(
        controller=mock_agent_controller,
        send_proof_request=SendProofRequest(
            connection_id="abcde",
            proof_request=indy_proof_request,
            protocol_version=PresentProofProtocolVersion.v1,
        ),
    )

    assert isinstance(created_proof_send_proposal, PresentationExchange)


@pytest.mark.anyio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    accepted_proof_request = await VerifierV1.accept_proof_request(
        mock_agent_controller,
        accept_proof_request=AcceptProofRequest(
            proof_id="v1-123",
            presentation_spec=IndyPresSpec(
                requested_attributes={},
                requested_predicates={},
                self_attested_attributes={},
            ),
        ),
    )

    assert isinstance(accepted_proof_request, PresentationExchange)


@pytest.mark.anyio
async def test_reject_proof_reject(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        to_async({})
    )
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn(
        {}  # todo: all of the mocks with to_async removed are unnecessary and have no effect
    )
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        v10_presentation_exchange_records[0]
    )

    deleted_proof_request = await VerifierV1.reject_proof_request(
        controller=mock_agent_controller,
        reject_proof_request=RejectProofRequest(proof_id="v1-abc"),
    )

    assert deleted_proof_request is None

    # Test exception handling when delete record returns rubbish
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        "Something went wrong"
    )
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn({})
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        v10_presentation_exchange_records[0]
    )

    with pytest.raises(AttributeError):
        deleted_proof_request = await VerifierV1.reject_proof_request(
            controller=mock_agent_controller,
            reject_proof_request="v1-abc",
        )
