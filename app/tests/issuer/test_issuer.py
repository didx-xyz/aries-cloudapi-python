import asyncio
import json
import time
from typing import Any, Dict, Optional

import pytest
from aries_cloudcontroller import DID, AcaPyClient, DIDResult
from httpx import AsyncClient
from mockito import when, mock

import app.generic.issuer.issuer as test_module
from app.generic.issuer.facades.acapy_issuer_v1 import IssuerV1
from app.generic.issuer.models import CredentialExchange, IssueCredentialProtocolVersion


# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response


@pytest.mark.asyncio
async def test_send_credential(mock_agent_controller: AcaPyClient):
    did = "WgWxqztrNooG92RXvxSTWv"
    cred_ex = mock(CredentialExchange)

    when(test_module).assert_valid_issuer(...).thenReturn(get(True))
    when(test_module).write_credential_def(...).thenReturn(get("cred_def_id"))
    when(IssuerV1).send_credential(...).thenReturn(get(cred_ex))
    when(mock_agent_controller.wallet).get_public_did().thenReturn(
        get(DIDResult(result=DID(did=did)))
    )

    credential = test_module.SendCredential(
        protocol_version=IssueCredentialProtocolVersion.v1,
        connection_id="conn_id",
        schema_id="schema_id",
        attributes={"name": "John", "age": "23"},
    )


@pytest.yield_fixture(scope="module")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def schema_definition(yoma_agent_module_scope: AcaPyClient) -> Dict[str, Any]:
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["speed"]
    )

    public_did = await acapy_ledger_facade.create_pub_did(yoma_agent_module_scope)
    print(f"created did: {public_did}")

    schema_definition_result = await create_schema(definition, yoma_agent_module_scope)
    print(schema_definition_result)

    print(f"created schema {str(schema_definition_result)}")
    return (schema_definition_result).dict()


@pytest.fixture(scope="module")
async def credential_definition_id(
    async_client_bob_module_scope: AsyncClient, schema_definition: Dict[str, Any]
) -> str:
    # when
    response = await async_client_bob_module_scope.post(
        MEMBER_AGENT_URL + "/admin/governance/credential-definitions",
        data=json.dumps(
            {
                "support_revocation": False,
                "schema_id": schema_definition["schema_id"],
                "tag": get_random_string(5),
            }
        ),
    )
    result = response.json()

    print(f"created definition {str(result)}")
    return result["credential_definition_id"]


@pytest.fixture(scope="module")
async def credential_exchange_id(
    async_client_bob_module_scope: AsyncClient,
    alice_connection_id: str,
    schema_definition: Dict[str, Any],
    bob_connection_id: str,
    async_client_alice_module_scope: AsyncClient,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_connection_id,
        "schema_id": schema_definition["schema_id"],
        "attributes": {"speed": "average"},
    }

    response = await async_client_bob_module_scope.post(
        BASE_PATH,
        data=json.dumps(credential),
    )
    credential_exchange = response.json()
    credential_exchange_id = credential_exchange["credential_id"]
    assert credential_exchange["protocol_version"] == "v1"

    time.sleep(5)
    response = await async_client_alice_module_scope.get(
        BASE_PATH, params={"connection_id": alice_connection_id}
    )
    records = response.json()
    assert len(records) > 0

    return credential_exchange_id


@pytest.mark.asyncio
async def test_send_credential(
    async_client_bob_module_scope: AsyncClient,
    schema_definition: Dict[str, Any],
    bob_connection_id: str,
    alice_connection_id: str,
    async_client_alice_module_scope: AsyncClient,
):
    credential = {
        "protocol_version": "v1",
        "connection_id": bob_connection_id,
        "schema_id": schema_definition["schema_id"],
        "attributes": {"speed": "average"},
    }

    response = await async_client_alice_module_scope.get(
        BASE_PATH, params={"connection_id": alice_connection_id}
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0

    response = await async_client_bob_module_scope.post(
        BASE_PATH,
        data=json.dumps(credential),
    )

    credential["protocol_version"] = "v2"
    response = await async_client_bob_module_scope.post(
        BASE_PATH,
        data=json.dumps(credential),
    )

    time.sleep(5)
    response = await async_client_alice_module_scope.get(
        BASE_PATH, params={"connection_id": alice_connection_id}
    )
    records = response.json()

    assert len(records) == 2

    # Expect one v1 record, one v2 record
    assert_that(records).extracting("protocol_version").contains("v1", "v2")


@pytest.mark.asyncio
async def test_get_records(async_client_alice_module_scope: AsyncClient):
    records = (await async_client_alice_module_scope.get(BASE_PATH)).json()
    assert records
    assert len(records) >= 1


@pytest.mark.asyncio
async def test_send_credential_request(
    async_client_bob_module_scope: AsyncClient, credential_exchange_id: str
):
    time.sleep(10)
    response = await async_client_bob_module_scope.post(
        f"{BASE_PATH}/{credential_exchange_id}/request"
    )

    # This returns an error - the correct one because the credential is in state received.
    # For this to return another response we'd have to have state offer_received
    result = response.json()

    assert result["error_message"]
    assert "Credential exchange" in result["error_message"]
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_store_credential(
    async_client_bob_module_scope: AsyncClient, credential_exchange_id: str
):
    # TODO check for the correct response when state is credential_received
    # We can't complete this with auto accept enabled
    time.sleep(5)
    response = await async_client_bob_module_scope.post(
        f"{BASE_PATH}/{credential_exchange_id}/store"
    )

    result = response.json()

    print(result)

    assert result["error_message"]
    assert ("Credential exchange" and "state (must be credential_received).") in result[
        "error_message"
    ]
    assert response.status_code == 400
