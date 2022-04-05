from typing import Any, Optional

from app.error.cloud_api_error import CloudApiException

from app.generic.verifier.models import (
    AcceptProofRequest,
)
from shared_models import PresentationExchange
from unittest.mock import patch
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.facades.trust_registry import Actor
from app.generic.verifier.verifier_utils import (
    ed25519_verkey_to_did_key,
    get_connection_record,
    get_schema_ids,
    is_valid_schemas,
    is_verifier,
    check_tr_for_prover,
    check_tr_for_verifier,
    get_actor,
)

from mockito import when
import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    AttachDecorator,
    AttachDecoratorData,
    ConnRecord,
    CredInfoList,
    IndyCredInfo,
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
    IndyPresSpec,
    IndyProof,
    IndyProofProof,
    IndyProofReqAttrSpec,
    IndyProofRequest,
    IndyProofRequestNonRevoked,
    IndyProofRequestedProof,
    IndyRequestedCredsRequestedPred,
    IndyProofReqAttrSpecNonRevoked,
    IndyRequestedCredsRequestedAttr,
    V10PresentationExchange,
    V10PresentationProposalRequest,
    V20Pres,
    V20PresExRecord,
    V20PresExRecordByFormat,
    V20PresFormat,
    V20PresProposal,
)


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
        presentation_request=indy_proof_request,
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
    non_revoked=IndyProofRequestNonRevoked(from_=0, to=20),
    nonce="12345",
    requested_attributes={
        "0_speed_uuid": IndyProofReqAttrSpec(
            name="speed",
            non_revoked=IndyProofReqAttrSpecNonRevoked(from_=0, to=20),
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
            pres_request={"indy": indy_proof_request.dict()},
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


@pytest.mark.asyncio
async def test_is_valid_schemas():
    # schemas are valid
    schemas = {
        "schemas": [
            "NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3",
            "U8BpHgzm5H5WbmDqeQRnxh:2:test_schema:0.3",
            "WoWSMfxTHA14GR2FdJJcHk:2:test_schema:0.3",
        ]
    }
    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = schemas

        assert await is_valid_schemas(schema_ids=schemas["schemas"]) is True

    # has invalid schema
    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = schemas

        with pytest.raises(
            CloudApiException, match="Found schema unknown to trust registrty"
        ):
            assert await is_valid_schemas(schema_ids=schemas["schemas"][1])


@pytest.mark.asyncio
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
        get(conn_record)
    ), when(Verifier).get_proof_record(...).thenReturn(get(pres_exchange)), patch(
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


@pytest.mark.asyncio
async def test_get_schema_ids(mock_agent_controller: AcaPyClient):
    schemas = {"schemas": ["NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3"]}
    cred_ex_record = IndyCredInfo(schema_id="NR6Y28AiZ893utPSfoQRrz:2:test_schema:0.3")
    with when(mock_agent_controller.credentials).get_records(...).thenReturn(
        get(CredInfoList(results=[cred_ex_record]))
    ):
        got_schema_ids = await get_schema_ids(aries_controller=mock_agent_controller)
        assert got_schema_ids == schemas["schemas"]


@pytest.mark.asyncio
async def test_ed25519_verkey_to_did_key():
    got_key = ed25519_verkey_to_did_key(
        key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV"
    )
    assert got_key == "did:key:z6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As"


@pytest.mark.asyncio
async def test_is_verifier():
    # False
    actor = Actor(id="abcde", name="Flint", roles=["issuer"], did="did:sov:abcde")
    with pytest.raises(
        CloudApiException, match="Insufficient priviliges: Actor not a verifier."
    ):
        is_verifier(actor=actor)

    # True
    actor["roles"].append("verifier")
    assert is_verifier(actor=actor) is True


@pytest.mark.asyncio
async def test_get_actor():
    # gets actor
    actor = Actor(id="abcde", name="Flint", roles=["verifier"], did="did:sov:abcde")
    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = actor

        assert await get_actor(did=actor["did"]) == actor

    # no actor
    with patch("httpx.get") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.is_error = False
        mock_request.return_value.json.return_value = None

        with pytest.raises(
            CloudApiException, match=f"No actor with DID {actor['did']}"
        ):
            await get_actor(did=actor["did"]) == actor


@pytest.mark.asyncio
async def test_check_tr_for_prover(mock_agent_controller: AcaPyClient):
    conn_record = ConnRecord(
        connection_id="abcde",
        invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
    )
    actor = Actor(id="abcde", name="Flint", roles=["verifier"], did="did:sov:abcde")

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

    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_connection_from_proof",
        return_value="abcde",
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.ed25519_verkey_to_did_key",
        return_value="did:key:6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As",
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        assert (
            await check_tr_for_prover(
                aries_controller=mock_agent_controller,
                prover=Verifier,
                proof_request=AcceptProofRequest(protocol_version="v1"),
            )
            is True
        )

    # invalid
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_connection_from_proof",
        return_value="abcde",
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.ed25519_verkey_to_did_key",
        return_value="did:key:6MkvVT4kkAmhTb9srDHScsL1q7pVKt9cpUJUah2pKuYh4As",
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=False
    ):
        with pytest.raises(
            CloudApiException, match="Could not verify prover against trust registry"
        ):
            assert await check_tr_for_prover(
                aries_controller=mock_agent_controller,
                prover=Verifier,
                proof_request=AcceptProofRequest(protocol_version="v1"),
            )


@pytest.mark.asyncio
async def test_check_tr_for_verifier(mock_agent_controller: AcaPyClient):
    conn_record = ConnRecord(
        connection_id="abcde",
        invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
    )
    actor = Actor(id="abcde", name="Flint", roles=["verifier"], did="did:sov:abcde")

    # valid
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ):
        assert (
            await check_tr_for_verifier(
                aries_controller=mock_agent_controller,
                proof_request=AcceptProofRequest(
                    protocol_version="v1", connection_id="abcde"
                ),
            )
            is True
        )

    # invalid
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=False
    ):
        with pytest.raises(
            CloudApiException,
            match="Flint is not a valid verifier in the trust registry.",
        ):
            assert await check_tr_for_verifier(
                aries_controller=mock_agent_controller,
                proof_request=AcceptProofRequest(
                    protocol_version="v1", connection_id="abcde"
                ),
            )
