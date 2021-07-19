import pytest
from admin.governance.dids import get_trusted_partner, get_trusted_registry

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/admin/governance/dids"


@pytest.mark.asyncio
async def test_get_trusted_registry(async_client_yoma):

    public_did = await async_client_yoma.get("/wallet/create-pub-did")
    print(str(public_did))
    response = await async_client_yoma.get(
        BASE_PATH + "/trusted-registry",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    assert response.status_code == 200
    result = response.json()
    expected_keys = ["did", "posture", "verkey"]
    print(str(result))
    assert [list(res.keys()) == expected_keys for res in result]
    assert len(result) > 0
    assert 1 == 0


@pytest.mark.asyncio
async def test_get_trusted_partner(async_client, yoma_agent_mock):

    # Create a public did
    did_response = await async_client.get(
        "/wallet/create-pub-did",
        headers={
            "x-api-key": "adminApiKey",
            "x-role": "yoma",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    res_json = did_response.json()
    did_created = res_json["did_object"]["did"]

    # try retrieve the created did from the ledger
    response = await async_client.get(
        BASE_PATH + f"/trusted-registry/{did_created}",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )

    # check the did is public and on the ledger
    assert response.status_code == 200
    result = response.json()
    expected_keys = ["did", "endpoint"]
    assert list(result.keys()) == expected_keys
    assert result["endpoint"] != ""
    assert result["did"] == did_created

    res_method = await get_trusted_partner(
        partner_did=f"{did_created}", aries_controller=yoma_agent_mock
    )
    assert res_method == result
