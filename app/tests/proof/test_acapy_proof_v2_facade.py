from typing import Optional, Any
from aries_cloudcontroller.model.v20_pres import V20Pres

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    AttachDecorator,
    AttachDecoratorData,
    AdminAPIMessageTracing,
    IndyProof,
    IndyProofProof,
    IndyProofRequest,
    IndyProofRequestedProof,
    V20PresExRecord,
    V20PresFormat,
    V20PresExRecordByFormat,
    V20PresProposalByFormat,
    V20PresProposalRequest,
    V20PresProposal,
    V20PresRequestByFormat,
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
        pres=V20Pres(
            formats=[V20PresFormat(attach_id="1234", format="indy")],
            presentationsattach=[
                AttachDecorator(
                    data=AttachDecoratorData(base64="kjbdvjbvekjvo"),
                )
            ],
            pres_ex_id="abcd",
            pres_proposal=V20PresProposal(
                formats=[V20PresFormat(attach_id="1234", format="indy")],
                proposalsattach=[
                    AttachDecorator(
                        data=AttachDecoratorData(base64="kjbdvjbvekjvo"),
                    )
                ],
            ),
        ),
        pres_request=None,
        role="prover",
        state=None,
        thread_id=None,
        trace=None,
        updated_at=None,
        verified="false",
    ),
]

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

proof_request_indy = V20PresRequestByFormat(
    dif=None,
    indy=IndyProofRequest(**proof_dict),
)


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).create_proof_request(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    created_proof_request = await ProofsV2.create_proof_request(
        controller=mock_agent_controller,
        proof_request=proof_request_indy,
        comment=None,
    )

    assert isinstance(created_proof_request, PresentationExchange)


@pytest.mark.asyncio
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

    created_proof_send_request = await ProofsV2.send_proof_request(
        controller=mock_agent_controller,
        proof_request=V20PresProposalRequest(
            connection_id="abc",
            presentation_proposal=V20PresProposalByFormat(**proof_request_indy.dict()),
        ),
    )

    assert isinstance(created_proof_send_request, PresentationExchange)

    with pytest.raises(NotImplementedError):
        await ProofsV2.send_proof_request(
            mock_agent_controller, proof_request="I am invalid"
        )


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v2_0).send_presentation(...).thenReturn(
        get(v20_presentation_exchange_records[0])
    )

    accepted_proof_request = await ProofsV2.accept_proof_request(
        mock_agent_controller,
        proof_id="v2-123",
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
        controller=mock_agent_controller, proof_id="v2-abc"
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
            controller=mock_agent_controller, proof_id="v2-abc"
        )
