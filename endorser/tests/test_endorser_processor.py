import json
from aries_cloudcontroller import AcaPyClient
import httpx
import pytest

from mockito import verify, when

from endorser.constants import TRUST_REGISTRY_URL
from ..endorser_processor import (
    Event,
    accept_endorsement,
    get_endorsement_request_attachment,
    is_credential_definition_transaction,
    get_did_and_schema_id_from_cred_def_attachment,
    is_governance_agent,
    is_valid_issuer,
    process_endorsement_event,
    should_accept_endorsement,
)
from .. import endorser_processor as test_module
from asynctest import MagicMock

from tests.util.mock import get


@pytest.mark.asyncio
async def test_accept_endorsement(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.endorse_transaction).endorse_transaction(
        tran_id="the-tran-id"
    ).thenReturn(get())
    endorsement = MagicMock(transaction_id="the-tran-id")
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
    # valid
    the_json = '{"the": "json"}'
    transaction = MagicMock(messages_attach=[{"data": {"json": the_json}}])
    assert get_endorsement_request_attachment(transaction) == json.loads(the_json)

    # no attachment
    assert get_endorsement_request_attachment(MagicMock()) == None

    # exception
    assert (
        get_endorsement_request_attachment(MagicMock(messages_attach={"no": "array"}))
        == None
    )


@pytest.mark.asyncio
async def test_get_did_and_schema_id_from_cred_def_attachment(
    mock_agent_controller: AcaPyClient,
):
    attachment = {"identifier": "123", "operation": {"ref": "456"}}

    schema = MagicMock(schema_=MagicMock(id="the-schema-id"))

    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        get(schema)
    )

    (did, schema_id) = await get_did_and_schema_id_from_cred_def_attachment(
        mock_agent_controller, attachment
    )

    assert did == "did:sov:123"
    assert schema_id == "the-schema-id"

    verify(mock_agent_controller.schema).get_schema(schema_id="456")


@pytest.mark.asyncio
async def test_get_did_and_schema_id_from_cred_def_attachment_err_no_schema_id(
    mock_agent_controller: AcaPyClient,
):
    attachment = {"identifier": "123", "operation": {"ref": "456"}}

    schema = MagicMock(schema_=MagicMock(id=None))

    when(mock_agent_controller.schema).get_schema(schema_id="456").thenReturn(
        get(schema)
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


@pytest.mark.asyncio
async def test_is_valid_issuer():
    did = "did:sov:123"
    schema_id = "the-schema-id"

    actor_res = MagicMock(
        status_code=200,
        is_error=False,
        json=MagicMock(return_value={"roles": ["issuer"]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}").thenReturn(
        actor_res
    )

    schema_res = MagicMock(
        status_code=200,
        is_error=False,
        json=MagicMock(return_value={"schemas": [schema_id]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/schemas").thenReturn(schema_res)

    assert await is_valid_issuer(did, schema_id)

    verify(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}")
    verify(httpx).get(f"{TRUST_REGISTRY_URL}/registry/schemas")


@pytest.mark.asyncio
async def test_is_valid_issuer_x_res_errors():
    did = "did:sov:123"
    schema_id = "the-schema-id"

    actor_res = MagicMock(
        status_code=200,
        is_error=True,
        json=MagicMock(return_value={"roles": ["issuer"]}),
    )
    when(httpx).get(f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}").thenReturn(
        actor_res
    )

    schema_res = MagicMock(
        status_code=200,
        is_error=False,
        json=MagicMock(return_value={"schemas": [schema_id]}),
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
    actor_res.json = MagicMock(
        return_value={"roles": ["verifier"], "id": "the-actor-id"}
    )
    assert not await is_valid_issuer(did, schema_id)

    # schema not registered
    actor_res.json = MagicMock(return_value={"roles": ["issuer"]})
    schema_res.json = MagicMock(return_value={"schemas": ["another-schema-id"]})
    assert not await is_valid_issuer(did, schema_id)

    # Back to valid again
    schema_res.json = MagicMock(return_value={"schemas": [schema_id]})
    assert await is_valid_issuer(did, schema_id)


@pytest.mark.asyncio
async def test_should_accept_endorsement(mock_agent_controller: AcaPyClient):
    transaction = MagicMock(
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
        get(MagicMock(schema_=MagicMock(id="the-schema-id")))
    )
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(get(transaction))
    when(test_module).is_valid_issuer("did:sov:123", "the-schema-id").thenReturn(
        get(True)
    )

    endorsement = MagicMock(transaction_id="the-tran-id")
    assert await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.asyncio
async def test_should_accept_endorsement_invalid_state(
    mock_agent_controller: AcaPyClient,
):
    transaction = MagicMock(state="done")
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(get(transaction))

    endorsement = MagicMock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.asyncio
async def test_should_accept_endorsement_no_attachment(
    mock_agent_controller: AcaPyClient,
):
    transaction = MagicMock(state="request_received")
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(get(transaction))

    endorsement = MagicMock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.asyncio
async def test_should_accept_endorsement_no_cred_def_operation(
    mock_agent_controller: AcaPyClient,
):
    transaction = MagicMock(
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
    ).thenReturn(get(transaction))

    endorsement = MagicMock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.asyncio
async def test_should_accept_endorsement_not_valid_issuer(
    mock_agent_controller: AcaPyClient,
):
    transaction = MagicMock(
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
        get(MagicMock(schema_=MagicMock(id="the-schema-id")))
    )
    when(mock_agent_controller.endorse_transaction).get_transaction(
        tran_id="the-tran-id"
    ).thenReturn(get(transaction))
    when(test_module).is_valid_issuer("did:sov:123", "the-schema-id").thenReturn(
        get(False)
    )

    endorsement = MagicMock(transaction_id="the-tran-id")
    assert not await should_accept_endorsement(mock_agent_controller, endorsement)


@pytest.mark.asyncio
async def test_process_endorsement_event(
    mock_agent_controller: AcaPyClient,
):
    data = json.dumps(
        {
            "origin": "governance",
            "wallet_id": "admin",
            "payload": {"transaction_id": "tran-id", "state": "request_received"},
        }
    )

    when(test_module).should_accept_endorsement(...).thenReturn(get(True))

    when(test_module).accept_endorsement(...).thenReturn(get())

    await process_endorsement_event(data, "endorsements")

    verify(test_module).accept_endorsement(...)
    verify(test_module).should_accept_endorsement(...)
