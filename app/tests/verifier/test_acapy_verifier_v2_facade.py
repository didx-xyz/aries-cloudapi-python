import pytest
from aries_cloudcontroller import AcaPyClient
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec
from mockito import when

from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)

from .test_verifier_utils import (
    get,
    indy_proof_request,
    v20_presentation_exchange_records,
)

from shared_models import PresentationExchange


@pytest.mark.anyio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).create_proof_request(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    created_proof_request = await VerifierV2.create_proof_request(
        controller=mock_agent_controller,
        proof_request=CreateProofRequest(
            protocol_version="v2", proof_request=indy_proof_request
        ),
    )

    assert isinstance(created_proof_request, PresentationExchange)


@pytest.mark.anyio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # Mock different functions on AcaPy client present proof api
    # proof interface decides upon params which methods it calls on the client
    # so let's mock those methods out
    when(mock_agent_controller.present_proof_v2_0).send_request(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )
    when(mock_agent_controller.present_proof_v2_0).send_proposal(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )
    when(mock_agent_controller.present_proof_v2_0).send_request_free(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    created_proof_send_request = await VerifierV2.send_proof_request(
        controller=mock_agent_controller,
        proof_request=SendProofRequest(
            protocol_version="v2",
            connection_id="abcde",
            proof_request=indy_proof_request,
        ),
    )

    assert isinstance(created_proof_send_request, PresentationExchange)

    with pytest.raises(AttributeError):
        await VerifierV2.send_proof_request(
            mock_agent_controller, proof_request="I am invalid"
        )


@pytest.mark.anyio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).send_presentation(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    accepted_proof_request = await VerifierV2.accept_proof_request(
        mock_agent_controller,
        proof_request=AcceptProofRequest(
            protocol_version="v2",
            proof_id="v2-abcd",
            presentation_spec=IndyPresSpec(
                requested_predicates={},
                requested_attributes={},
                self_attested_attributes={},
            ),
        ),
    )

    assert isinstance(accepted_proof_request, PresentationExchange)


@pytest.mark.anyio
async def test_reject_proof_reject(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).delete_record(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v2_0).report_problem(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v2_0).get_record(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    deleted_proof_request = await VerifierV2.reject_proof_request(
        controller=mock_agent_controller,
        proof_request=RejectProofRequest(
            protocol_version="v2", proof_id="v2-abc", problem_report=None
        ),
    )

    assert deleted_proof_request is None

    # Test exception handling when delete record returns rubbish
    when(mock_agent_controller.present_proof_v2_0).delete_record(...).thenReturn(
        get("Something went wrong")
    )
    when(mock_agent_controller.present_proof_v2_0).report_problem(...).thenReturn(
        get({})
    )
    when(mock_agent_controller.present_proof_v2_0).get_record(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    with pytest.raises(AttributeError):
        deleted_proof_request = await VerifierV2.reject_proof_request(
            controller=mock_agent_controller, proof_request="abc"
        )
