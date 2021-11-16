from typing import Any, Optional

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    AdminAPIMessageTracing,
    IndyProof,
    IndyProofProof,
    IndyProofRequest,
    IndyProofRequestedProof,
    V20PresExRecord,
    V20PresExRecordByFormat,
    V20PresProposalByFormat,
    V20PresProposalRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec
from fastapi.exceptions import HTTPException
from mockito import when

from app.generic.proof.facades.acapy_proof_v2 import ProofsV2
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

proof_request_indy = V20PresRequestByFormat(
    dif=None,
    indy=IndyProofRequest(
        name=None,
        non_revoked=None,
        nonce=None,
        requested_attributes=None,
        requested_predicates=None,
        version="0.0.1",
    ),
)

send_request_tracing = AdminAPIMessageTracing(trace=False)

v20_presentation_exchange_records = [
    V20PresExRecord(
        auto_present=False,
        by_format=V20PresExRecordByFormat(
            pres={},
            pres_proposal={},
            pres_request={},
        ),
        connection_id="abc",
        created_at="2021-09-15 13:49:47Z",
        error_msg=None,
        initiator="self",
        pres=None,
        pres_ex_id=None,
        pres_proposal=None,
        pres_request=None,
        role=None,
        state=None,
        thread_id=None,
        trace=None,
        updated_at=None,
        verified="false",
    ),
]


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).create_proof_request(...).thenReturn(
        get(PresentationExchange(v20=v20_presentation_exchange_records[0]))
    )

    created_proof_request = await ProofsV2.create_proof_request(
        controller=mock_agent_controller,
        proof=proof_request_indy,
        comment=None,
        trace=False,
    )

    assert isinstance(created_proof_request, PresentationExchange)
    assert isinstance(created_proof_request.v20, V20PresExRecord)
    assert created_proof_request.v10 is None


@pytest.mark.asyncio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # Mock different functions on AcaPy client present proof api
    # proof interface decides upon params which methods it calls on the client
    # so let's mock those methods out
    when(mock_agent_controller.present_proof_v2_0).send_request(...).thenReturn(
        get(PresentationExchange(v20=v20_presentation_exchange_records[0]))
    )
    when(mock_agent_controller.present_proof_v2_0).send_proposal(...).thenReturn(
        get(PresentationExchange(v20=v20_presentation_exchange_records[0]))
    )
    when(mock_agent_controller.present_proof_v2_0).send_request_free(...).thenReturn(
        get(PresentationExchange(v20=v20_presentation_exchange_records[0]))
    )

    created_proof_send_proposal = await ProofsV2.send_proof_request(
        controller=mock_agent_controller,
        presentation_request=send_request_tracing,
        pres_ex_id="abc",
        free=False,
    )

    assert isinstance(created_proof_send_proposal, PresentationExchange)
    assert isinstance(created_proof_send_proposal.v20, V20PresExRecord)
    assert created_proof_send_proposal.v10 is None

    created_proof_request_free = await ProofsV2.send_proof_request(
        controller=mock_agent_controller,
        presentation_request=V20PresSendRequestRequest(
            connection_id="abc", presentation_request=proof_request_indy
        ),
        pres_ex_id=None,
        free=True,
    )

    assert isinstance(created_proof_request_free, PresentationExchange)
    assert isinstance(created_proof_request_free.v20, V20PresExRecord)
    assert created_proof_request_free.v10 is None

    created_proof_send_request = await ProofsV2.send_proof_request(
        controller=mock_agent_controller,
        presentation_request=V20PresProposalRequest(
            connection_id="abc",
            presentation_proposal=V20PresProposalByFormat(**proof_request_indy.dict()),
        ),
        pres_ex_id="abc",
    )

    assert isinstance(created_proof_send_request, PresentationExchange)
    assert isinstance(created_proof_send_request.v20, V20PresExRecord)
    assert created_proof_send_request.v10 is None

    with pytest.raises(NotImplementedError):
        await ProofsV2.send_proof_request(
            mock_agent_controller, presentation_request="I am invalid"
        )


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).send_presentation(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    accepted_proof_request = await ProofsV2.accept_proof_request(
        mock_agent_controller,
        pres_ex_id="123",
        body=V20PresSpecByFormatRequest(
            dif=None,
            indy=IndyPresSpec(
                requested_predicates={},
                requested_attributes={},
                self_attested_attributes={},
            ),
        ),
    )

    assert isinstance(accepted_proof_request, PresentationExchange)
    assert isinstance(accepted_proof_request.v20, V20PresExRecord)
    assert accepted_proof_request.v10 is None


@pytest.mark.asyncio
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

    deleted_proof_request = await ProofsV2.reject_proof_request(
        controller=mock_agent_controller, pres_ex_id="abc"
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

    with pytest.raises(HTTPException):
        deleted_proof_request = await ProofsV2.reject_proof_request(
            controller=mock_agent_controller, pres_ex_id="abc"
        )
