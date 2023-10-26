from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    AttachDecorator,
    AttachDecoratorData,
    ConnRecord,
    IndyCredInfo,
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
    IndyPresSpec,
    IndyProof,
    IndyProofProof,
    IndyProofReqAttrSpec,
    IndyProofRequest,
    IndyProofRequestedProof,
    IndyProofRequestNonRevoked,
    IndyRequestedCredsRequestedAttr,
    IndyRequestedCredsRequestedPred,
    V10PresentationExchange,
    V10PresentationProposalRequest,
    V20Pres,
    V20PresExRecord,
    V20PresExRecordByFormat,
    V20PresFormat,
    V20PresProposal,
)
from assertpy import assert_that
from httpx import Response
from mockito import mock, when

from app.exceptions.cloud_api_error import CloudApiException
from app.models.trust_registry import Actor
from app.routes.verifier import AcceptProofRequest, SendProofRequest
from app.services.verifier.acapy_verifier import Verifier
from app.tests.util.mock import to_async
from app.util.acapy_verifier_utils import (
    are_valid_schemas,
    assert_valid_prover,
    assert_valid_verifier,
    ed25519_verkey_to_did_key,
    get_actor,
    get_connection_record,
    get_schema_ids,
    is_verifier,
)
from shared.models.protocol import PresentProofProtocolVersion
from shared.models.topics import PresentationExchange

sample_actor = Actor(
    id="abcde",
    name="Flint",
    roles=["verifier"],
    did="did:sov:abcde",
    didcomm_invitation=None,
)

indy_proof = IndyProof(
    identifiers=[],
    proof=IndyProofProof(aggregated_proof=None, proofs=None),
    requested_proof=IndyProofRequestedProof(),
)

indy_proof_request_empty = IndyProofRequest(
    name=None,
    non_revoked=None,
    nonce=None,
    requested_attributes={},
    requested_predicates={},
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
        presentation_request=indy_proof_request_empty,
        presentation_request_dict=None,
        role="prover",
        state="proposal_sent",
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

indy_proof_request = IndyProofRequest(
    name="string",
    non_revoked=IndyProofRequestNonRevoked(var_from=0, to=20),
    nonce="12345",
    requested_attributes={
        "0_speed_uuid": IndyProofReqAttrSpec(
            name="speed",
            restrictions=None,
        )
    },
    requested_predicates={},
    version="1.0",
)


v20_presentation_exchange_records = [
    V20PresExRecord(
        auto_present=False,
        by_format=V20PresExRecordByFormat(
            pres={"indy": {"hello": "world"}},
            pres_proposal={"indy": {"hello": "world"}},
            pres_request={"indy": indy_proof_request.to_dict()},
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
        state="proposal-sent",
        thread_id=None,
        trace=None,
        updated_at=None,
        verified="false",
    ),
]


indy_pres_spec = IndyPresSpec(
    requested_attributes={
        "0_string_uuid": IndyRequestedCredsRequestedAttr(cred_id="0_string_uuid")
    },
    requested_predicates={
        "0_string_GE_uuid": IndyRequestedCredsRequestedPred(cred_id="0_string_GE_uuid")
    },
    self_attested_attributes={"sth": "sth_else"},
)


@pytest.mark.anyio
async def test_are_valid_schemas(mock_async_client):
    # schemas are valid
    schemas = {
        [
            "NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3",
            "U8BpHgzm5H5WbmDqeQRnxh:2:test_schema:0.3",
            "WoWSMfxTHA14GR2FdJJcHk:2:test_schema:0.3",
        ]
    }
    mock_async_client.get = AsyncMock(return_value=Response(200, json=schemas))

    assert await are_valid_schemas(schema_ids=schemas) is True

    # has invalid schema
    mock_async_client.get = AsyncMock(return_value=Response(200, json=schemas))

    assert (
        await are_valid_schemas(schema_ids=["SomeRandomDid:2:test_schema:0.3"]) is False
    )


@pytest.mark.anyio
async def test_get_connection_record(mock_agent_controller: AcaPyClient):
    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(connection_id=pres_exchange.connection_id)
    with when(mock_agent_controller.connection).get_connection(...).thenReturn(
        to_async(conn_record)
    ), when(Verifier).get_proof_record(...).thenReturn(pres_exchange), patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ):
        assert (
            await get_connection_record(
                aries_controller=mock_agent_controller,
                connection_id=conn_record.connection_id,
            )
            == conn_record
        )
    # todo: mocking of get_proof_record does nothing


@pytest.mark.anyio
async def test_get_schema_ids(mock_agent_controller: AcaPyClient):
    first_cred_record = IndyCredInfo(
        schema_id="NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3"
    )
    second_cred_record = IndyCredInfo(
        schema_id="NR6Y28AiZ893utPSfoQRrz:2:another_schema:0.3"
    )

    presentation = IndyPresSpec(
        self_attested_attributes={},
        requested_attributes={
            "group_name": IndyRequestedCredsRequestedAttr(
                revealed=False, cred_id="first-unrevealed-cred-id"
            ),
            "another_group_name": IndyRequestedCredsRequestedAttr(
                revealed=True, cred_id="first-revealed-cred-id"
            ),
        },
        requested_predicates={
            "pred_group_name": IndyRequestedCredsRequestedPred(
                cred_id="first-revealed-pred-cred-id"
            )
        },
    )

    with when(mock_agent_controller.credentials).get_record(
        credential_id="first-revealed-cred-id"
    ).thenReturn(to_async(first_cred_record)), when(
        mock_agent_controller.credentials
    ).get_record(
        credential_id="first-revealed-pred-cred-id"
    ).thenReturn(
        to_async(second_cred_record)
    ):
        got_schema_ids = await get_schema_ids(
            aries_controller=mock_agent_controller, presentation=presentation
        )

        assert_that(got_schema_ids).contains_only(
            "NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3",
            "NR6Y28AiZ893utPSfoQRrz:2:another_schema:0.3",
        )


@pytest.mark.anyio
async def test_ed25519_verkey_to_did_key():
    got_key = ed25519_verkey_to_did_key(
        key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
    )
    assert got_key == "did:key:z6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As"


@pytest.mark.anyio
async def test_is_verifier():
    # False
    actor = Actor(
        id="abcde",
        name="Flint",
        roles=["issuer"],
        did="did:sov:abcde",
        didcomm_invitation=None,
    )
    assert is_verifier(actor=actor) is False

    # True
    actor["roles"].append("verifier")
    assert is_verifier(actor=actor) is True


@pytest.mark.anyio
async def test_get_actor(mock_async_client):
    # gets actor
    actor = Actor(id="abcde", name="Flint", roles=["verifier"], did="did:sov:abcde")
    mock_async_client.get = AsyncMock(return_value=Response(200, json=actor))

    assert await get_actor(did=actor["did"]) == actor

    # no actor
    mock_async_client.get = AsyncMock(return_value=Response(200, json={}))

    with pytest.raises(CloudApiException, match=f"No actor with DID {actor['did']}"):
        await get_actor(did=actor["did"])


@pytest.mark.anyio
async def test_assert_valid_prover_invitation_key(mock_agent_controller: AcaPyClient):
    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(
        connection_id=pres_exchange.connection_id,
        invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
    )

    presentation = IndyPresSpec(
        self_attested_attributes={},
        requested_attributes={
            "group_name": IndyRequestedCredsRequestedAttr(
                revealed=False, cred_id="first-unrevealed-cred-id"
            ),
            "another_group_name": IndyRequestedCredsRequestedAttr(
                revealed=True, cred_id="first-revealed-cred-id"
            ),
        },
        requested_predicates={
            "pred_group_name": IndyRequestedCredsRequestedPred(
                cred_id="first-revealed-pred-cred-id"
            )
        },
    )

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))
    when(mock_agent_controller.connection).get_connection(
        conn_id=pres_exchange.connection_id
    ).thenReturn(to_async(conn_record))

    with patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids",
        return_value=["did:schema:123"],
    ), patch(
        "app.generic.verifier.verifier_utils.get_trust_registry_schemas",
        return_value=["did:schema:123"],
    ):
        # Should not throw
        await assert_valid_prover(
            aries_controller=mock_agent_controller,
            presentation=AcceptProofRequest(
                proof_id=pres_exchange.proof_id, indy_presentation_spec=presentation
            ),
            verifier=verifier,
        )


@pytest.mark.anyio
async def test_assert_valid_prover_public_did(mock_agent_controller: AcaPyClient):
    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(
        connection_id=pres_exchange.connection_id, their_public_did="did:sov:123"
    )

    presentation = IndyPresSpec(
        self_attested_attributes={},
        requested_attributes={
            "group_name": IndyRequestedCredsRequestedAttr(
                revealed=False, cred_id="first-unrevealed-cred-id"
            ),
            "another_group_name": IndyRequestedCredsRequestedAttr(
                revealed=True, cred_id="first-revealed-cred-id"
            ),
        },
        requested_predicates={
            "pred_group_name": IndyRequestedCredsRequestedPred(
                cred_id="first-revealed-pred-cred-id"
            )
        },
    )

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))
    when(mock_agent_controller.connection).get_connection(
        conn_id=pres_exchange.connection_id
    ).thenReturn(to_async(conn_record))

    with patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids",
        return_value=["did:schema:123"],
    ), patch(
        "app.generic.verifier.verifier_utils.get_trust_registry_schemas",
        return_value=["did:schema:123"],
    ):
        # Should not throw
        await assert_valid_prover(
            aries_controller=mock_agent_controller,
            presentation=AcceptProofRequest(
                proof_id=pres_exchange.proof_id, indy_presentation_spec=presentation
            ),
            verifier=verifier,
        )


@pytest.mark.anyio
async def test_assert_valid_prover_x_no_public_did_no_invitation_key(
    mock_agent_controller: AcaPyClient,
):
    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(connection_id=pres_exchange.connection_id)

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))
    when(mock_agent_controller.connection).get_connection(
        conn_id=pres_exchange.connection_id
    ).thenReturn(to_async(conn_record))

    with pytest.raises(
        CloudApiException, match="Could not determine did of the verifier"
    ):
        await assert_valid_prover(
            aries_controller=mock_agent_controller,
            presentation=AcceptProofRequest(
                proof_id=pres_exchange.proof_id, indy_presentation_spec=indy_pres_spec
            ),
            verifier=verifier,
        )


@pytest.mark.anyio
async def test_assert_valid_prover_x_actor_invalid_role(
    mock_agent_controller: AcaPyClient,
):
    actor = Actor(
        id="abcde",
        name="Flint",
        roles=["issuer"],
        did="did:sov:abcde",
        didcomm_invitation=None,
    )

    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(
        connection_id=pres_exchange.connection_id, their_public_did="xxx"
    )

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))
    when(mock_agent_controller.connection).get_connection(
        conn_id=pres_exchange.connection_id
    ).thenReturn(to_async(conn_record))

    # valid
    with patch("app.generic.verifier.verifier_utils.get_actor", return_value=actor):
        with pytest.raises(
            CloudApiException, match="Actor is missing required role 'verifier'"
        ):
            await assert_valid_prover(
                aries_controller=mock_agent_controller,
                presentation=AcceptProofRequest(
                    proof_id=pres_exchange.proof_id,
                    indy_presentation_spec=indy_pres_spec,
                ),
                verifier=verifier,
            )


@pytest.mark.anyio
async def test_assert_valid_prover_x_invalid_schemas(
    mock_agent_controller: AcaPyClient,
):
    pres_exchange = PresentationExchange(
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )
    conn_record = ConnRecord(
        connection_id=pres_exchange.connection_id, their_public_did="xxx"
    )

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))
    when(mock_agent_controller.connection).get_connection(
        conn_id=pres_exchange.connection_id
    ).thenReturn(to_async(conn_record))

    with patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids",
        return_value=["did:schema:456"],
    ), patch(
        "app.generic.verifier.verifier_utils.get_trust_registry_schemas",
        return_value=["did:schema:123"],
    ):
        with pytest.raises(
            CloudApiException,
            match="Presentation is using schemas not registered in trust registry",
        ):
            await assert_valid_prover(
                aries_controller=mock_agent_controller,
                presentation=AcceptProofRequest(
                    proof_id=pres_exchange.proof_id,
                    indy_presentation_spec=indy_pres_spec,
                ),
                verifier=verifier,
            )


@pytest.mark.anyio
async def test_assert_valid_prover_x_no_connection_id(
    mock_agent_controller: AcaPyClient,
):
    pres_exchange = PresentationExchange(
        created_at="2021-09-15 13:49:47Z",
        proof_id="v1-abcd",
        presentation=None,
        presentation_request=indy_proof_request,
        role="prover",
        state="proposal-sent",
        protocol_version="v1",
        updated_at=None,
        verified="false",
    )

    verifier = mock(Verifier)

    when(verifier).get_proof_record(
        controller=mock_agent_controller, proof_id=pres_exchange.proof_id
    ).thenReturn(to_async(pres_exchange))

    with pytest.raises(
        CloudApiException, match="No connection id associated with proof request."
    ):
        assert await assert_valid_prover(
            aries_controller=mock_agent_controller,
            presentation=AcceptProofRequest(
                proof_id=pres_exchange.proof_id, indy_presentation_spec=indy_pres_spec
            ),
            verifier=verifier,
        )


@pytest.mark.anyio
async def test_assert_valid_verifier_invitation_key(mock_agent_controller: AcaPyClient):
    conn = ConnRecord(
        connection_id="a-connection-id",
        invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
    )

    when(mock_agent_controller.connection).get_connection(
        conn_id="a-connection-id"
    ).thenReturn(to_async(conn))

    # valid
    with patch(
        "app.generic.verifier.verifier_utils.assert_public_did",
        side_effect=Exception("Error"),
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ):
        await assert_valid_verifier(
            aries_controller=mock_agent_controller,
            proof_request=SendProofRequest(
                protocol_version=PresentProofProtocolVersion.v1,
                connection_id="a-connection-id",
                indy_proof_request=indy_proof_request,
            ),
        )


@pytest.mark.anyio
async def test_assert_valid_verifier_public_did(mock_agent_controller: AcaPyClient):
    # valid
    with patch(
        "app.generic.verifier.verifier_utils.assert_public_did",
        return_value="did:sov:something",
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ):
        await assert_valid_verifier(
            aries_controller=mock_agent_controller,
            proof_request=SendProofRequest(
                protocol_version=PresentProofProtocolVersion.v1,
                connection_id="abcde",
                indy_proof_request=indy_proof_request,
            ),
        )


@pytest.mark.anyio
async def test_assert_valid_verifier_x_no_public_did_no_invitation_key(
    mock_agent_controller: AcaPyClient,
):
    conn = ConnRecord(
        connection_id="a-connection-id",
    )

    when(mock_agent_controller.connection).get_connection(
        conn_id="a-connection-id"
    ).thenReturn(to_async(conn))

    # valid
    with patch(
        "app.generic.verifier.verifier_utils.assert_public_did",
        side_effect=Exception("Error"),
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=sample_actor
    ):
        with pytest.raises(CloudApiException, match="Connection has no invitation key"):
            await assert_valid_verifier(
                aries_controller=mock_agent_controller,
                proof_request=SendProofRequest(
                    protocol_version=PresentProofProtocolVersion.v1,
                    connection_id="a-connection-id",
                    indy_proof_request=indy_proof_request,
                ),
            )


@pytest.mark.anyio
async def test_assert_valid_verifier_x_not_verifier(
    mock_agent_controller: AcaPyClient,
):
    actor = Actor(
        id="abcde",
        name="Flint",
        roles=["issuer"],
        did="did:sov:abcde",
        didcomm_invitation=None,
    )

    conn = ConnRecord(
        connection_id="a-connection-id",
        invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
    )

    when(mock_agent_controller.connection).get_connection(
        conn_id="a-connection-id"
    ).thenReturn(to_async(conn))

    # valid
    with patch(
        "app.generic.verifier.verifier_utils.assert_public_did",
        side_effect=Exception("Error"),
    ), patch("app.generic.verifier.verifier_utils.get_actor", return_value=actor):
        with pytest.raises(
            CloudApiException,
            match="Flint is not a valid verifier in the trust registry.",
        ):
            await assert_valid_verifier(
                aries_controller=mock_agent_controller,
                proof_request=SendProofRequest(
                    protocol_version=PresentProofProtocolVersion.v1,
                    connection_id="a-connection-id",
                    indy_proof_request=indy_proof_request,
                ),
            )
