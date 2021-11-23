from typing import Any, Optional
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec
from aries_cloudcontroller.model.indy_proof_request import IndyProofRequest

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    IndyRequestedCredsRequestedAttr,
    IndyRequestedCredsRequestedPred,
)
from mockito import verify, when
from app.generic.proof.models import PresentationExchange, ProofRequestProtocolVersion

import app.generic.proof.proof as test_module
from app.generic.proof.facades.acapy_proof_v1 import ProofsV1
from app.generic.proof.facades.acapy_proof_v2 import ProofsV2

indy_pres_spec = IndyPresSpec(
    requested_attributes={
        "0_string_uuid": IndyRequestedCredsRequestedAttr(cred_id="0_string_uuid")
    },
    requested_predicates={
        "0_string_GE_uuid": IndyRequestedCredsRequestedPred(cred_id="0_string_GE_uuid")
    },
    self_attested_attributes={"sth": "sth_else"},
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

presentation_exchange_record_1 = PresentationExchange(
    connection_id="abcde",
    created_at="2021-11-22 11:37:45.179595Z",
    updated_at="2021-11-22 11:37:45.179595Z",
    proof_id="abcde",
    protocol_version=ProofRequestProtocolVersion.v10.value,
    presentation={},
    role="prover",
    state="presentation-sent",
    verified=False,
)

presentation_exchange_record_2 = PresentationExchange(
    connection_id="abcde",
    created_at="2021-11-22 11:37:45.179595Z",
    updated_at="2021-11-22 11:37:45.179595Z",
    proof_id="abcde",
    protocol_version=ProofRequestProtocolVersion.v20.value,
    presentation={},
    role="prover",
    state="presentation-sent",
    verified=False,
)


# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response


@pytest.mark.asyncio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(ProofsV1).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    result = await test_module.send_proof_request(
        proof_request=test_module.SendProofRequest(
            connection_id="abcde",
            proof_request=IndyProofRequest(**proof_dict),
            protocol_version="v1",
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_1
    verify(ProofsV1).send_proof_request(...)

    # V2
    when(ProofsV2).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    result = await test_module.send_proof_request(
        proof_request=test_module.SendProofRequest(
            connection_id="abcde",
            proof_request=IndyProofRequest(**proof_dict),
            protocol_version="v2",
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_2
    verify(ProofsV2).send_proof_request(...)


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(ProofsV1).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    result = await test_module.create_proof_request(
        proof_request=test_module.CreateProofRequest(
            protocol_version="v1", proof_request=IndyProofRequest(**proof_dict)
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_1
    verify(ProofsV1).create_proof_request(...)

    # V2
    when(ProofsV2).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    result = await test_module.create_proof_request(
        proof_request=test_module.CreateProofRequest(
            protocol_version="v2", proof_request=IndyProofRequest(**proof_dict)
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_2
    verify(ProofsV2).create_proof_request(...)


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(ProofsV1).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    result = await test_module.accept_proof_request(
        proof_request=test_module.AcceptProofRequest(
            proof_id="1234",
            presentation_spec=indy_pres_spec,
            protocol_version="v1",
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_1
    verify(ProofsV1).accept_proof_request(...)

    # V2
    when(ProofsV2).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    result = await test_module.accept_proof_request(
        proof_request=test_module.AcceptProofRequest(
            proof_id="1234",
            presentation_spec=indy_pres_spec,
            protocol_version="v2",
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_2
    verify(ProofsV2).accept_proof_request(...)


@pytest.mark.asyncio
async def test_reject_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(ProofsV1).reject_proof_request(...).thenReturn(get(None))

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(
            protocol_version="v1", proof_id="1234"
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(ProofsV1).reject_proof_request(...)

    # V2
    when(ProofsV2).reject_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(
            protocol_version="v2", proof_id="1234"
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(ProofsV2).reject_proof_request(...)
