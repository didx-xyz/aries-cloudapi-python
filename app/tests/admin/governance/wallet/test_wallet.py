import pytest
import json
from admin.governance.wallet import (
    create_pub_did,
    create_wallet,
    remove_wallet_by_id,
    get_subwallet_auth_token,
    update_subwallet,
    get_subwallet,
    query_subwallet,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/admin/governance/wallet"

# @pytest.mark.asyncio
# async def test_create_pub_did(async_client, yoma_agent_mock):
#     response = await async_client.get(
#         "/wallets/create-pub-did",
#         headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
#     )

#     assert response.status_code == 200
#     response = response.json()
#     # assert response == ''
#     assert response["did_object"] and response["did_object"]!= {}
#     assert response["issuer_verkey"] and response["issuer_verkey"] != {}
#     assert response["issuer_endpoint"] and response["issuer_endpoint"] != {}

#     assert response["did_object"]["posture"] == "public"


# @pytest.mark.asyncio
# async def test_get_subwallet_auth_token(async_client, member_admin_agent_mock):

#     wallet_response = await async_client.post(
#         "/wallets/create-wallet",
#         headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
#         data=json.dumps(
#             {
#                 "image_url": "https://aries.ca/images/sample.png",
#                 "key_management_mode": "managed",
#                 "label": "YOMA",
#                 "wallet_dispatch_type": "default",
#                 "wallet_key": "MySecretKey1234",
#                 "wallet_name": "YOMAWallet",
#                 "wallet_type": "indy",
#             }
#         ),
#     )
#     wallet_response = wallet_response.json()

#     wallet_id = wallet_response["wallet_id"]

#     response = await async_client.get(
#         f"/wallets/get-subwallet-auth-token/{wallet_id}",
#         headers={
#             "x-api-key": "adminApiKey",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )

#     response = response.json()
#     assert response["token"] and type(response["token"]) == str
# #     assert response["token"] != ""

#     res_method = await get_subwallet_auth_token(
#         wallet_id, aries_controller=member_admin_agent_mock
#     )
#     assert res_method == response

#     remove_response = await async_client.get(
#         f"/wallets/remove-wallet/{wallet_id}",
#         headers={"x-api-key": "adminApiKey"},
#     )
#     assert remove_response.status_code == 200
#     assert remove_response.json() == "Successfully removed wallet"


@pytest.mark.asyncio
async def test_get_subwallet(async_client, member_admin_agent_mock):
    wallet_response = await async_client.post(
        "/wallets/create-wallet",
        headers={"x-api-key": "adminApiKey", **APPLICATION_JSON_CONTENT_TYPE},
        data=json.dumps(
            {
                "image_url": "https://aries.ca/images/sample.png",
                "key_management_mode": "managed",
                "label": "YOMA",
                "wallet_dispatch_type": "default",
                "wallet_key": "MySecretKey1234",
                "wallet_name": "YOMAWallet23456789",
                "wallet_type": "indy",
            }
        ),
    )
    wallet_response = wallet_response.json()

    wallet_id = wallet_response["wallet_id"]
    response = await async_client.get(
        f"/wallet/get-subwallet-by-id/{wallet_id}",
        headers={
            "x-api-key": "adminApiKey",
            **APPLICATION_JSON_CONTENT_TYPE,
        },
    )
    response = response.json()
    assert response == ""
    assert response["wallet_id"] and response["wallet_id"] != {}
    assert response["key_management_mode"] and response["key_management_mode"] != {}
    assert response["settings"] and response["settings"] != {}
    res_method = await get_subwallet(aries_controller=member_admin_agent_mock)
    assert res_method == response


# @pytest.mark.asyncio
# async def test_create_wallet(
#     async_client, member_admin_agent_mock
# ):

#     response = await async_client.get(
#         "/wallet/create-wallet"
#     )

#     response = response.json()

#     assert response.wallet_id
#     assert response.key_management_mode
#     assert response.settings
#     assert response.token
#     res_method =await create_wallet(aries_controller=member_admin_agent_mock)
#     assert res_method == response

# @pytest.mark.asyncio
# async def test_remove_by_id(
#     async_client, member_admin_agent_mock
# ):

#     wallet_response = await async_client.get(
#         "/wallet/create-wallet"
#     )

#     response = await async_client.get(
#         "/wallet/remove-wallet"
#     )

#     assert response.
