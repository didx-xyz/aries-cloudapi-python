from aries_cloudcontroller.model.did import DID
from aries_cloudcontroller.model.did_result import DIDResult

import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    ConnRecord,
    IndyProofRequest,
    IndyCredPrecis,
)
from mockito import verify, when
from unittest.mock import patch as patch

from app.facades.trust_registry import Actor
import app.generic.verifier.verifier as test_module
from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import (
    PresentationExchange,
    ProofRequestProtocolVersion,
)
from app.tests.verifier.test_verifier_utils import proof_dict, get, indy_pres_spec

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

actor = Actor(
    id="abcde",
    name="Flint",
    roles=["verifier"],
    did="did:sov:2cpBmR3FqGKWi5EyUbpRY8",
)
conn_record = ConnRecord(
    connection_id="abcde",
    invitation_key="H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
)


@pytest.mark.asyncio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.send_proof_request(
            proof_request=test_module.SendProofRequest(
                connection_id="abcde",
                proof_request=IndyProofRequest(**proof_dict),
                protocol_version="v1",
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_1
        verify(VerifierV1).send_proof_request(...)

    # V2
    when(VerifierV2).send_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.send_proof_request(
            proof_request=test_module.SendProofRequest(
                connection_id="abcde",
                proof_request=IndyProofRequest(**proof_dict),
                protocol_version="v2",
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_2
        verify(VerifierV2).send_proof_request(...)


@pytest.mark.asyncio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.create_proof_request(
            proof_request=test_module.CreateProofRequest(
                protocol_version="v1", proof_request=IndyProofRequest(**proof_dict)
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_1
        verify(VerifierV1).create_proof_request(...)

    # V2
    when(VerifierV2).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )
    when(VerifierV2).create_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.create_proof_request(
            proof_request=test_module.CreateProofRequest(
                protocol_version="v2", proof_request=IndyProofRequest(**proof_dict)
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_2
        verify(VerifierV2).create_proof_request(...)


@pytest.mark.asyncio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_1)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )
    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.accept_proof_request(
            proof_request=test_module.AcceptProofRequest(
                proof_id="1234",
                presentation_spec=indy_pres_spec,
                protocol_version="v1",
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_1
        verify(VerifierV1).accept_proof_request(...)

    # V2
    when(VerifierV2).accept_proof_request(...).thenReturn(
        get(presentation_exchange_record_2)
    )
    when(mock_agent_controller.wallet).get_public_did(...).thenReturn(
        get(DIDResult(result=DID(did=actor["did"])))
    )

    with patch(
        "app.generic.verifier.verifier_utils.get_connection_record",
        return_value=conn_record,
    ), patch(
        "app.generic.verifier.verifier_utils.get_actor", return_value=actor
    ), patch(
        "app.generic.verifier.verifier_utils.is_verifier", return_value=True
    ), patch(
        "app.generic.verifier.verifier_utils.get_credential_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.get_schema_ids", return_value=["abcde"]
    ), patch(
        "app.generic.verifier.verifier_utils.is_valid_schemas", return_value=True
    ):
        result = await test_module.accept_proof_request(
            proof_request=test_module.AcceptProofRequest(
                proof_id="v2-1234",
                presentation_spec=indy_pres_spec,
                protocol_version="v2",
            ),
            aries_controller=mock_agent_controller,
        )

        assert result is presentation_exchange_record_2
        verify(VerifierV2).accept_proof_request(...)


@pytest.mark.asyncio
async def test_reject_proof_request(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).reject_proof_request(...).thenReturn(get(None))

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(
            protocol_version="v1", proof_id="1234"
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(VerifierV1).reject_proof_request(...)

    # V2
    when(VerifierV2).reject_proof_request(...).thenReturn(get(None))

    result = await test_module.reject_proof_request(
        proof_request=test_module.RejectProofRequest(
            protocol_version="v2", proof_id="1234"
        ),
        aries_controller=mock_agent_controller,
    )

    assert result is None
    verify(VerifierV2).reject_proof_request(...)


@pytest.mark.asyncio
async def test_delete_proof(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).delete_proof(...).thenReturn(get(None))

    result = await test_module.delete_proof(
        proof_id="v1-1234", aries_controller=mock_agent_controller
    )

    assert result is None
    verify(VerifierV1).delete_proof(...)

    # V2
    when(VerifierV2).delete_proof(...).thenReturn(get(None))

    result = await test_module.delete_proof(
        proof_id="v2-1234", aries_controller=mock_agent_controller
    )

    assert result is None
    verify(VerifierV2).delete_proof(...)


@pytest.mark.asyncio
async def test_get_proof_record(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).get_proof_record(...).thenReturn(
        get(presentation_exchange_record_1)
    )

    result = await test_module.get_proof_record(
        proof_id="v1-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == presentation_exchange_record_1
    verify(VerifierV1).get_proof_record(...)

    # V2
    when(VerifierV2).get_proof_record(...).thenReturn(
        get(presentation_exchange_record_2)
    )

    result = await test_module.get_proof_record(
        proof_id="v2-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == presentation_exchange_record_2
    verify(VerifierV2).get_proof_record(...)


@pytest.mark.asyncio
async def test_get_proof_records(mock_agent_controller: AcaPyClient):
    # V1 and V2
    with when(VerifierV1).get_proof_records(...).thenReturn(
        get([presentation_exchange_record_1])
    ), when(VerifierV2).get_proof_records(...).thenReturn(
        get([presentation_exchange_record_2])
    ):

        result = await test_module.get_proof_records(
            aries_controller=mock_agent_controller
        )

        assert result == [
            presentation_exchange_record_1,
            presentation_exchange_record_2,
        ]
        verify(VerifierV1).get_proof_records(...)


@pytest.mark.asyncio
async def test_get_credentials_for_request(mock_agent_controller: AcaPyClient):
    # V1
    when(VerifierV1).get_credentials_for_request(...).thenReturn(
        get([IndyCredPrecis()])
    )

    result = await test_module.get_credentials_for_request(
        proof_id="v1-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == [IndyCredPrecis()]
    verify(VerifierV1).get_credentials_for_request(...)

    # V2
    when(VerifierV2).get_credentials_for_request(...).thenReturn(
        get([IndyCredPrecis()])
    )

    result = await test_module.get_credentials_for_request(
        proof_id="v2-abcd",
        aries_controller=mock_agent_controller,
    )

    assert result == [IndyCredPrecis()]
    verify(VerifierV2).get_credentials_for_request(...)
