from typing import Optional

import pytest
from aries_cloudcontroller import AcaPyClient
from assertpy import assert_that
from fastapi import HTTPException

from app.routes.connections import router
from app.services import acapy_wallet
from app.tests.util.webhooks import get_wallet_id_from_async_client
from app.util.did import qualified_did_sov
from shared import RichAsyncClient

BASE_PATH = router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize(
    "use_did,use_did_method,use_public_did",
    [
        (None, None, False),
        (True, None, False),
        (None, "did:peer:2", False),
        (None, "did:peer:4", False),
        (True, "did:peer:4", False),
        (None, None, True),
    ],
)
async def test_create_did_exchange_request(
    alice_member_client: RichAsyncClient,
    alice_acapy_client: AcaPyClient,
    faber_acapy_client: AcaPyClient,
    use_did: Optional[str],
    use_did_method: Optional[str],
    use_public_did: bool,
):
    faber_public_did = await acapy_wallet.get_public_did(controller=faber_acapy_client)

    request_data = {"their_public_did": qualified_did_sov(faber_public_did.did)}

    if use_did:
        new_did = await acapy_wallet.create_did(controller=alice_acapy_client)
        request_data["use_did"] = new_did.did

    if use_did_method:
        request_data["use_did_method"] = use_did_method

    if use_public_did:
        request_data["use_public_did"] = use_public_did

    if use_public_did:  # Alice doesn't have a public DID
        with pytest.raises(HTTPException) as exc_info:
            response = await alice_member_client.post(
                f"{BASE_PATH}/create-did-request", params=request_data
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == """{"detail":"No public DID configured."}"""

    elif use_did and use_did_method:
        with pytest.raises(HTTPException) as exc_info:
            response = await alice_member_client.post(
                f"{BASE_PATH}/create-did-request", params=request_data
            )
        assert exc_info.value.status_code == 400
        assert (
            exc_info.value.detail
            == """{"detail":"Cannot specify both use_did and use_did_method."}"""
        )
    else:
        response = await alice_member_client.post(
            f"{BASE_PATH}/create-did-request", params=request_data
        )
        assert response.status_code == 200
        connection_record = response.json()
        assert_that(connection_record).contains("connection_id", "state")
        assert_that(connection_record["state"]).is_equal_to("request-sent")


# @pytest.mark.anyio
# async def test_accept_did_exchange_invitation(
#     alice_member_client: RichAsyncClient,
#     faber_client: RichAsyncClient,
#     tenant_admin_client: RichAsyncClient,
#     faber_acapy_client: AcaPyClient,
# ):
#     faber_public_did = await acapy_wallet.get_public_did(controller=faber_acapy_client)

#     # Disable auto-accept invites for Faber
#     faber_wallet_id = await get_wallet_id_from_async_client(controller=faber_client)
#     await tenant_admin_client.put(
#         f"/tenants/{faber_wallet_id}",
#         json={"extra_settings": {"ACAPY_AUTO_ACCEPT_INVITES": False}},
#     )

#     # Create an invitation from Faber
#     invitation_response = await faber_acapy_client.connection.create_invitation()
#     invitation = invitation_response.invitation

#     # Alice accepts the invitation
#     response = await alice_member_client.post(
#         f"{BASE_PATH}/accept-invitation",
#         json={"invitation": invitation},
#     )
#     assert response.status_code == 200
#     connection_record = response.json()
#     assert_that(connection_record).contains("connection_id", "state")
#     assert_that(connection_record["state"]).is_equal_to("request-sent")
