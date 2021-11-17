import asyncio
from typing import Optional, Any, Dict
import time
import json

from aries_cloudcontroller import (
    AcaPyClient,
    IndyProofRequest,
    IndyProofReqAttrSpec,
    IndyRequestedCredsRequestedAttr,
    IndyRequestedCredsRequestedPred,
)
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec
from aries_cloudcontroller.model.v10_presentation_send_request_request import (
    V10PresentationSendRequestRequest,
)
from httpx import AsyncClient
import pytest

from app.facades.acapy_ledger import create_pub_did
from app.admin.governance.schemas import SchemaDefinition, create_schema
from app.dependencies import MEMBER_AGENT_URL
from app.tests.utils_test import get_random_string

BASE_PATH = "/generic/proof"


async def get(response: Optional[Any] = None):
    if response:
        return response


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

    public_did = await create_pub_did(yoma_agent_module_scope)
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
        "/generic/issuer/credentials",
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


indy_proof_request = IndyProofRequest(
    name="Proof Request",
    non_revoked=None,
    nonce=None,
    requested_attributes={
        "0_string_uuid": {
            "name": "string",
            "names": ["string"],
            "non_revoked": {"from_": 0, "to": 0},
            "restrictions": None,
        },
    },
    requested_predicates={
        "0_string_GE_uuid": {
            "name": "string",
            "p_type": "<",
            "p_value": 0,
            "non_revoked": {"from_": 0, "to": 0},
            "restrictions": None,
        },
    },
    version="0.3",
)


@pytest.mark.asyncio
async def test_send_proof_request(
    alice_connection_id: str,
    async_client_alice_module_scope: AsyncClient,
):
    response = await async_client_alice_module_scope.post(
        BASE_PATH + f"/send-request?connection_id={alice_connection_id}",
        data=json.dumps(proof_dict),
    )

    result = response.json()
    assert result["v10"] is None
    assert "auto_present" in result["v20"].keys()
    assert "created_at" in result["v20"].keys()
    assert "pres_request" in result["v20"].keys()


@pytest.mark.asyncio
async def test_create_proof_request(
    async_client_alice_module_scope: AsyncClient,
):
    response = await async_client_alice_module_scope.post(
        BASE_PATH
        + "/create-request?connection_id={alice_connection_id}&protocol_version=2",
        data=json.dumps(proof_dict),
    )

    result = response.json()
    assert result["v10"] is None
    assert result["v20"]
    assert "auto_present" in result["v20"].keys()
    assert "created_at" in result["v20"].keys()
    assert "pres_request" in result["v20"].keys()


@pytest.mark.asyncio
async def test_accept_proof_request(
    alice_connection_id,
    async_client,
    async_client_bob_module_scope: AsyncClient,
    async_client_alice_module_scope: AsyncClient,
):
    # proof_dict['connection_id'] = alice_connection_id
    # proof_req_res = await async_client_alice_module_scope.post(
    #     BASE_PATH + f"/send-request?connection_id={alice_connection_id}",
    #     data=json.dumps(proof_dict),
    # )
    # print(proof_req_res.json())
    # assert proof_req_res.json() == ""
    # presentation_exchange_id = proof_req_res.json()["v20"]["pres_ex_id"]
    # print(f"\n\n\n {presentation_exchange_id} \n\n\n")
    # WALLET_HEADERS = {
    #     "content-type": "application/json",
    #     "x-role": "yoma",
    #     "x-api-key": "adminApiKey",
    # }
    # response = await async_client.post(
    #     BASE_PATH + f"/accept-request?pres_ex_id={presentation_exchange_id}",
    #     data=json.dumps(IndyPresSpec(**{
    #             "requested_attributes": {
    #                 "additionalProp1": {"cred_id": "string", "revealed": True},
    #             },
    #             "requested_predicates": {
    #                 "additionalProp1": {"cred_id": "string", "timestamp": 0},
    #             },
    #             "self_attested_attributes": {
    #                 "additionalProp1": "string",
    #             },
    #             "trace": True,
    #         }).dict()),
    #     headers=WALLET_HEADERS,
    # )
    # result = response.json()
    # assert result == ""
    pass


@pytest.mark.asyncio
async def test_reject_proof_request(
    async_client,
    alice_connection_id: str,
    async_client_alice_module_scope: AsyncClient,
):
    # response = await async_client_alice_module_scope.post(
    #     BASE_PATH
    #     + "/create-request?connection_id={alice_connection_id}&protocol_version=2",
    #     data=json.dumps(proof_dict),
    # )
    response = await async_client_alice_module_scope.post(
        BASE_PATH + f"/send-request?connection_id={alice_connection_id}",
        data=json.dumps(proof_dict),
    )

    print(f"\n\n\n {response.json()} \n\n\n")
    pres_ex_id = response.json()["v20"]["pres_ex_id"]

    response = await async_client.post(
        BASE_PATH + f"/reject-request?pres_ex_id={pres_ex_id}",
    )
    result = response.json()
    assert result == ""
