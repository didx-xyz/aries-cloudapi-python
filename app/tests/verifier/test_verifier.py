import pytest
from aries_cloudcontroller import (AcaPyClient, ConnRecord, IndyCredInfo,
                                   IndyCredPrecis)
from mockito import verify, when

import app.generic.verifier.verifier as test_module
from app.facades.trust_registry import Actor
from app.generic.verifier import verifier_utils
from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import PresentProofProtocolVersion
from app.tests.verifier.test_verifier_utils import (indy_pres_spec,
                                                    indy_proof_request)
from shared_models import PresentationExchange
from tests.util.mock import get

presentation_exchange_record_1 = PresentationExchange(
    connection_id="abcde",
    created_at="2021-11-22 11:37:45.179595Z",
    updated_at="2021-11-22 11:37:45.179595Z",
    proof_id="abcde",
    protocol_version=PresentProofProtocolVersion.v1.value,
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
    protocol_version=PresentProofProtocolVersion.v2.value,
    presentation={},
    role="prover",
    state="presentation-sent",
    verified=False,
)

actor = Actor(
    id="abcde",
    name="Flint",
    roles=["verifier"],
    did="did:sov:2cpBmR3FqGKWi5EyUbpRY8",
    didcomm_invitation=None,
)
conn_record = ConnRecord(
    connection_id="abcde",
    invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
)


@pytest.mark.anyio
async def test_send_proof_request_v1(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    when(mock_agent_controller.connection).get_connection(conn_id="abcde").thenReturn(
        get(conn_record)
    )

    when(verifier_utils).get_actor(
        did="did:key:z6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As"
    ).thenReturn(get(actor))

    send_proof_request = test_module.SendProofRequest(
        connection_id="abcde",
        proof_request=indy_proof_request,
        protocol_version="v1",
    )

    result = await test_module.send_proof_request(
        proof_request=send_proof_request,
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_1
    verify(VerifierV1).send_proof_request(
        controller=mock_agent_controller, proof_request=send_proof_request
    )


@pytest.mark.anyio
async def test_send_proof_request_v2(mock_agent_controller: AcaPyClient):
    # V2
    when(VerifierV2).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    when(mock_agent_controller.connection).get_connection(conn_id="abcde").thenReturn(
        get(conn_record)
    )

    when(verifier_utils).get_actor(
        did="did:key:z6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As"
    ).thenReturn(get(actor))

    send_proof_request = test_module.SendProofRequest(
        connection_id="abcde",
        proof_request=indy_proof_request,
        protocol_version="v2",
    )

    result = await test_module.send_proof_request(
        proof_request=send_proof_request,
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_2
    verify(VerifierV2).send_proof_request(
        controller=mock_agent_controller, proof_request=send_proof_request
    )


@pytest.mark.anyio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    #  V1
    when(VerifierV1).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )
    result = await test_module.create_proof_request(
        proof_request=test_module.CreateProofRequest(
            protocol_version="v1",
            proof_request=indy_proof_request,
            connection_id="abcde",
        ),
        aries_controller=mock_agent_controller,
    )
    assert result is presentation_exchange_record_1

    #  V2
    when(VerifierV2).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )
    result = await test_module.create_proof_request(
        proof_request=test_module.CreateProofRequest(
            protocol_version="v2",
            proof_request=indy_proof_request,
            connection_id="abcde",
        ),
        aries_controller=mock_agent_controller,
    )
    assert result is presentation_exchange_record_2


@pytest.mark.anyio
async def test_accept_proof_request_v1(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )
    when(VerifierV1).get_proof_record(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    presentation = test_module.AcceptProofRequest(
        proof_id="v1-1234", presentation_spec=indy_pres_spec
    )

    when(test_module).assert_valid_prover(
        aries_controller=mock_agent_controller,
        prover=VerifierV1,
        presentation=presentation,
    ).thenReturn(get())

    result = await test_module.accept_proof_request(
        presentation=presentation,
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_1
    verify(VerifierV1).accept_proof_request(...)


@pytest.mark.anyio
async def test_accept_proof_request_v2(mock_agent_controller: AcaPyClient):
    # V2
    when(VerifierV2).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )
    when(VerifierV2).get_proof_record(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    presentation = test_module.AcceptProofRequest(
        proof_id="v2-1234", presentation_spec=indy_pres_spec
    )

    when(test_module).assert_valid_prover(
        aries_controller=mock_agent_controller,
        prover=VerifierV2,
        presentation=presentation,
    ).thenReturn(get())

    result = await test_module.accept_proof_request(
        presentation=presentation,
        aries_controller=mock_agent_controller,
    )

    assert result is presentation_exchange_record_2
    verify(VerifierV2).accept_proof_request(...)


@pytest.mark.anyio
async def test_reject_proof_request(mock_agent_controller: AcaPyClient):
    proof_request_v1 = test_module.RejectProofRequest(proof_id="v1-1234")
    # V1
    when(VerifierV1).reject_proof_request(
        controller=mock_agent_controller, proof_request=proof_request_v1
    ).thenReturn(get(None))
    presentation_exchange_record_1.state = "request-received"
    when(VerifierV1).get_proof_record(
        controller=mock_agent_controller, proof_id=proof_request_v1.proof_id
    ).thenReturn(get(presentation_exchange_record_1))

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(proof_id="v1-1234"),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(VerifierV1).reject_proof_request(
        controller=mock_agent_controller, proof_request=proof_request_v1
    )
    verify(VerifierV1).get_proof_record(
        controller=mock_agent_controller, proof_id=proof_request_v1.proof_id
    )

    proof_request_v2 = test_module.RejectProofRequest(proof_id="v2-1234")

    # V2
    when(VerifierV2).reject_proof_request(
        controller=mock_agent_controller, proof_request=proof_request_v2
    ).thenReturn(get(None))
    presentation_exchange_record_2.state = "request-received"
    when(VerifierV2).get_proof_record(
        controller=mock_agent_controller, proof_id=proof_request_v2.proof_id
    ).thenReturn(get(presentation_exchange_record_2))

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(proof_id="v2-1234"),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(VerifierV2).reject_proof_request(
        controller=mock_agent_controller, proof_request=proof_request_v2
    )
    verify(VerifierV2).get_proof_record(
        controller=mock_agent_controller, proof_id=proof_request_v2.proof_id
    )


@pytest.mark.anyio
async def test_delete_proof(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).delete_proof(
        controller=mock_agent_controller, proof_id="v1-1234"
    ).thenReturn(get(None))

    result = await test_module.delete_proof(
        proof_id="v1-1234", aries_controller=mock_agent_controller
    )

    assert result is None
    verify(VerifierV1).delete_proof(
        controller=mock_agent_controller, proof_id="v1-1234"
    )

    # V2
    when(VerifierV2).delete_proof(
        controller=mock_agent_controller, proof_id="v2-1234"
    ).thenReturn(get(None))

    result = await test_module.delete_proof(
        proof_id="v2-1234", aries_controller=mock_agent_controller
    )

    assert result is None
    verify(VerifierV2).delete_proof(
        controller=mock_agent_controller, proof_id="v2-1234"
    )


@pytest.mark.anyio
async def test_get_proof_record(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).get_proof_record(
        controller=mock_agent_controller, proof_id="v1-abcd"
    ).thenReturn(get(presentation_exchange_record_1))

    result = await test_module.get_proof_record(
        proof_id="v1-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == presentation_exchange_record_1
    verify(VerifierV1).get_proof_record(
        controller=mock_agent_controller, proof_id="v1-abcd"
    )

    # V2
    when(VerifierV2).get_proof_record(
        controller=mock_agent_controller, proof_id="v2-abcd"
    ).thenReturn(get(presentation_exchange_record_2))

    result = await test_module.get_proof_record(
        proof_id="v2-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == presentation_exchange_record_2
    verify(VerifierV2).get_proof_record(
        controller=mock_agent_controller, proof_id="v2-abcd"
    )


@pytest.mark.anyio
async def test_get_proof_records(mock_agent_controller: AcaPyClient):
    # V1 and V2
    with when(VerifierV1).get_proof_records(
        controller=mock_agent_controller
    ).thenReturn(get([presentation_exchange_record_1])), when(
        VerifierV2
    ).get_proof_records(
        controller=mock_agent_controller
    ).thenReturn(
        get([presentation_exchange_record_2])
    ):

        result = await test_module.get_proof_records(
            aries_controller=mock_agent_controller
        )

        assert result == [
            presentation_exchange_record_1,
            presentation_exchange_record_2,
        ]
        verify(VerifierV1).get_proof_records(controller=mock_agent_controller)
        verify(VerifierV2).get_proof_records(controller=mock_agent_controller)


@pytest.mark.anyio
async def test_get_credentials_for_request(mock_agent_controller: AcaPyClient):
    cred_precis = IndyCredPrecis(
        cred_info=IndyCredInfo(cred_def_id="WgWxqztrNooG92RXvxSTWv:3:CL:20:tag")
    )
    # V1
    when(VerifierV1).get_credentials_for_request(
        controller=mock_agent_controller, proof_id="v1-abcd"
    ).thenReturn(get([cred_precis]))

    result = await test_module.get_credentials_for_request(
        proof_id="v1-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == [cred_precis]
    verify(VerifierV1).get_credentials_for_request(
        controller=mock_agent_controller, proof_id="v1-abcd"
    )

    # V2
    when(VerifierV2).get_credentials_for_request(
        controller=mock_agent_controller, proof_id="v2-abcd"
    ).thenReturn(get([cred_precis]))

    result = await test_module.get_credentials_for_request(
        proof_id="v2-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == [cred_precis]
    verify(VerifierV2).get_credentials_for_request(
        controller=mock_agent_controller, proof_id="v2-abcd"
    )
