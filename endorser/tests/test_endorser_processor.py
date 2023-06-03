import json
from unittest.mock import Mock

import httpx
import pytest
from aries_cloudcontroller import AcaPyClient
from mockito import verify, when

from app.tests.util.mock import to_async
from endorser import endorser_processor as test_module
from endorser.endorser_processor import (
    Event,
    accept_endorsement,
    get_did_and_schema_id_from_cred_def_attachment,
    get_endorsement_request_attachment,
    is_credential_definition_transaction,
    is_governance_agent,
    is_valid_issuer,
    process_endorsement_event,
    should_accept_endorsement,
)
from shared import TRUST_REGISTRY_URL


@pytest.mark.anyio
async def test_accept_endorsement(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.endorse_transaction).endorse_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async())
    endorsement = Mock(transaction_id="the-tran-id")
    await accept_endorsement(mock_agent_controller, endorsement)

    verify(mock_agent_controller.endorse_transaction).endorse_transaction(
        tran_id="the-tran-id"
    )


def test_is_credential_definition_transaction():
    # operation type 102 is credential definition
    assert is_credential_definition_transaction({"operation": {"type": "102"}})

    assert not is_credential_definition_transaction({"operation": {"type": "100"}})
    assert not is_credential_definition_transaction({"random": "json"})


def test_get_endorsement_request_attachment():
    # valid string json data
    the_json_string = '{"the": "json"}'
    the_json_dict = {"the": "json"}
    transaction = Mock(messages_attach=[{"data": {"json": the_json_string}}])
    assert get_endorsement_request_attachment(transaction) == the_json_dict

    # valid dict json data
    transaction = Mock(messages_attach=[{"data": {"json": the_json_dict}}])
    assert get_endorsement_request_attachment(transaction) == the_json_dict

    # no attachment
    assert get_endorsement_request_attachment(Mock(messages_attach=None)) is None

    # exception
    assert get_endorsement_request_attachment(Mock(messages_attach={"a": "b"})) is None


@pytest.mark.anyio
async def test_get_did_and_schema_id_from_cred_def_attachment(
    mock_agent_controller: AcaPyClient,
):
    attachment = {"identifier": "123", "operation": {"ref": "456"}}

    schema = Mock(schema_=Mock(id="the-schema-id"))

    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        to_async(schema)
    )

    (did, schema_id) = await get_did_and_schema_id_from_cred_def_attachment(
        mock_agent_controller, attachment
    )

    assert did == "did:sov:123"
    assert schema_id == "the-schema-id"

    verify(mock_agent_controller.schema).get_schema(schema_id="456")


@pytest.mark.anyio
async def test_get_did_and_schema_id_from_cred_def_attachment_err_no_schema_id(
    mock_agent_controller: AcaPyClient,
):
    attachment = {"identifier": "123", "operation": {"ref": "456"}}

    schema = Mock(schema_=Mock(id=None))

    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        to_async(schema)
    )

    with pytest.raises(
        Exception, match="Could not extract schema id from schema response"
    ):
        await get_did_and_schema_id_from_cred_def_attachment(
            mock_agent_controller, attachment
        )

    verify(mock_agent_controller.schema).get_schema(schema_id="456")


def test_is_governance_agent():
    assert is_governance_agent(
        Event(origin="governance", payload={}, wallet_id="something")
    )
    assert not is_governance_agent(
        Event(origin="random", payload={}, wallet_id="something")
    )


@pytest.mark.anyio
async def test_is_valid_issuer():
    did = "did:sov:123"
    schema_id = "the-schema-id"

    actor_res = Mock(
        status_code=200,
        is_error=False,
        json=Mock(return_value={"roles": ["issuer"]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}").thenReturn(
        actor_res
    )

    schema_res = Mock(
        status_code=200,
        is_error=False,
        json=Mock(return_value={"schemas": [schema_id]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/schemas").thenReturn(schema_res)

    assert await is_valid_issuer(did, schema_id)

    verify(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}")
    verify(httpx).get(f"{TRUST_REGISTRY_URL}/registry/schemas")


@pytest.mark.anyio
async def test_is_valid_issuer_x_res_errors():
    did = "did:sov:123"
    schema_id = "the-schema-id"

    actor_res = Mock(
        status_code=200,
        is_error=True,
        json=Mock(return_value={"roles": ["issuer"]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}").thenReturn(
        actor_res
    )

    schema_res = Mock(
        status_code=200,
        is_error=False,
        json=Mock(return_value={"schemas": [schema_id]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/schemas").thenReturn(schema_res)

    # Error actor res
    assert not await is_valid_issuer(did, schema_id)

    # Error schema res
    actor_res.is_error = False
    schema_res.is_error = True
    assert not await is_valid_issuer(did, schema_id)

    # Back to valid again
    schema_res.is_error = False
    assert await is_valid_issuer(did, schema_id)

    # Invalid role
    actor_res.json = Mock(return_value={"roles": ["verifier"], "id": "the-actor-id"})
    assert not await is_valid_issuer(did, schema_id)

    # schema not registered
    actor_res.json = Mock(return_value={"roles": ["issuer"]})
    schema_res.json = Mock(return_value={"schemas": ["another-schema-id"]})
    assert not await is_valid_issuer(did, schema_id)

    # Back to valid again
    schema_res.json = Mock(return_value={"schemas": [schema_id]})
    assert await is_valid_issuer(did, schema_id)


@pytest.mark.anyio
async def test_should_accept_endorsement(mock_agent_controller: AcaPyClient):
    transaction = Mock(
        state="request_received",
        messages_attach=[
            {
                "data": {
                    "json": json.dumps(
                        {
                            "identifier": "123",  # did
                            "operation": {
                                "type": "102",  # cred def operation
                                "ref": "456",  # schema id
                            },
                        }
                    )
                }
            }
        ],
    )
    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        to_async(Mock(schema_=Mock(id="the-schema-id")))
    )
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async(transaction))
    when(test_module).is_valid_issuer("did:sov:123", "the-schema-id").thenReturn(
        to_async(True)
    )

    endorsement = Mock(transaction_id="the-tran-id")
    assert await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.anyio
async def test_should_accept_endorsement_invalid_state(
    mock_agent_controller: AcaPyClient,
):
    transaction = Mock(state="done")
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async(transaction))

    endorsement = Mock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.anyio
async def test_should_accept_endorsement_no_attachment(
    mock_agent_controller: AcaPyClient,
):
    transaction = Mock(state="request_received")
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async(transaction))

    endorsement = Mock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.anyio
async def test_should_accept_endorsement_no_cred_def_operation(
    mock_agent_controller: AcaPyClient,
):
    transaction = Mock(
        state="request_received",
        messages_attach=[
            {
                "data": {
                    "json": json.dumps(
                        {
                            "identifier": "123",  # did
                            "operation": {
                                "type": "1045",  # not cred def operation
                                "ref": "456",  # schema id
                            },
                        }
                    )
                }
            }
        ],
    )
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async(transaction))

    endorsement = Mock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.anyio
async def test_should_accept_endorsement_not_valid_issuer(
    mock_agent_controller: AcaPyClient,
):
    transaction = Mock(
        state="request_received",
        messages_attach=[
            {
                "data": {
                    "json": json.dumps(
                        {
                            "identifier": "123",  # did
                            "operation": {
                                "type": "102",  # cred def operation
                                "ref": "456",  # schema id
                            },
                        }
                    )
                }
            }
        ],
    )
    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        to_async(Mock(schema_=Mock(id="the-schema-id")))
    )
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(to_async(transaction))
    when(test_module).is_valid_issuer("did:sov:123", "the-schema-id").thenReturn(
        to_async(False)
    )

    endorsement = Mock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.anyio
async def test_process_endorsement_event():
    data = json.dumps(
        {
            "origin": "governance",
            "wallet_id": "admin",
            "payload": {"transaction_id": "tran-id", "state": "request-received"},
        }
    )

    when(test_module).should_accept_endorsement(...).thenReturn(to_async(True))

    when(test_module).accept_endorsement(...).thenReturn(to_async())

    await process_endorsement_event(data, "endorsements")

    verify(test_module).accept_endorsement(...)
    verify(test_module).should_accept_endorsement(...)
