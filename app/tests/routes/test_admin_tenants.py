from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from aries_cloudcontroller import CreateWalletResponse, CreateWalletTokenRequest
from fastapi import HTTPException

from app.dependencies.acapy_clients import TENANT_ADMIN_AUTHED
from app.exceptions import CloudApiException, TrustRegistryException
from app.models.tenants import CreateTenantRequest, UpdateTenantRequest
from app.routes.admin.tenants import (
    create_tenant,
    delete_tenant_by_id,
    get_tenant,
    get_tenants,
    get_wallet_auth_token,
    update_tenant,
)

wallet_id = "some_wallet_id"
wallet_name = "some_wallet_name"

create_wallet_response = CreateWalletResponse(
    key_management_mode="managed",
    wallet_id=wallet_id,
    created_at="2024-02-27T09:48:39.508826Z",
    updated_at="2024-02-27T09:48:39.508826Z",
    token="abc",
)
create_tenant_body = CreateTenantRequest(
    wallet_label="Test Wallet",
    wallet_name=wallet_name,
    roles=["issuer"],
    group_id="test_group",
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "roles", [[], ["issuer"], ["verifier"], ["issuer", "verifier"]]
)
async def test_create_tenant_success(roles):
    # Mock the dependencies
    mock_admin_controller = AsyncMock()
    mock_admin_controller.multitenancy.create_wallet = AsyncMock(
        return_value=create_wallet_response
    )
    mock_onboard_tenant = AsyncMock()
    mock_register_actor = AsyncMock()

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.onboard_tenant", mock_onboard_tenant
    ), patch(
        "app.routes.admin.tenants.register_actor", mock_register_actor
    ), patch(
        "app.routes.admin.tenants.assert_actor_name", return_value=False
    ):
        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            mock_admin_controller
        )

        response = await create_tenant(
            body=create_tenant_body.model_copy(update={"roles": roles}),
            admin_auth=TENANT_ADMIN_AUTHED,
        )

        assert response.wallet_label == create_tenant_body.wallet_label
        assert response.group_id == create_tenant_body.group_id
        mock_admin_controller.multitenancy.create_wallet.assert_awaited()

        if roles:
            mock_onboard_tenant.assert_awaited()
            mock_register_actor.assert_awaited()


@pytest.mark.anyio
async def test_create_tenant_fail_trust_registry_error():
    with patch(
        "app.routes.admin.tenants.assert_actor_name",
        side_effect=TrustRegistryException("Error"),
    ), pytest.raises(
        CloudApiException,
        match="An error occurred when trying to register actor. Please try again",
    ) as exc:
        await create_tenant(body=Mock(), admin_auth=TENANT_ADMIN_AUTHED)
    assert exc.value.status_code == 500


@pytest.mark.anyio
@pytest.mark.parametrize(
    "roles",
    [[], ["issuer"], ["verifier"], ["issuer", "verifier"]],
)
async def test_create_tenant_fail_actor_exists(roles):
    wallet_label = "abc"
    with patch(
        "app.routes.admin.tenants.assert_actor_name",
        return_value=True,
    ), pytest.raises(
        HTTPException,
        match=(
            f"Can't create Tenant. The label `{wallet_label}` may not "
            "be re-used because it exists on the trust registry."
        ),
    ) as exc:
        await create_tenant(
            body=create_tenant_body.model_copy(
                update={"roles": roles, "wallet_label": wallet_label}
            ),
            admin_auth=TENANT_ADMIN_AUTHED,
        )
    assert exc.value.status_code == 409


@pytest.mark.anyio
@pytest.mark.parametrize(
    "roles",
    [[], ["issuer"], ["verifier"], ["issuer", "verifier"]],
)
async def test_create_tenant_fail_wallet_name_exists(roles):
    with patch(
        "app.routes.admin.tenants.handle_acapy_call",
        side_effect=CloudApiException(status_code=400, detail="already exists"),
    ), patch(
        "app.routes.admin.tenants.assert_actor_name",
        return_value=False,
    ), pytest.raises(
        HTTPException,
        match=(
            f"A wallet with name `{wallet_name}` already exists. "
            "The wallet name must be unique."
        ),
    ) as exc:
        await create_tenant(
            body=create_tenant_body.model_copy(update={"roles": roles}),
            admin_auth=TENANT_ADMIN_AUTHED,
        )
    assert exc.value.status_code == 409


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_msg", ["Error1", "Error2"])
@pytest.mark.parametrize(
    "roles",
    [[], ["issuer"], ["verifier"], ["issuer", "verifier"]],
)
async def test_create_tenant_fail_wallet_creation(status_code, error_msg, roles):
    # Create tenant should raise the same error message / status code of create wallet failure
    with patch(
        "app.routes.admin.tenants.handle_acapy_call",
        side_effect=CloudApiException(status_code=status_code, detail=error_msg),
    ), patch(
        "app.routes.admin.tenants.assert_actor_name", return_value=False
    ), pytest.raises(
        HTTPException, match=error_msg
    ) as exc:
        await create_tenant(
            body=create_tenant_body.model_copy(update={"roles": roles}),
            admin_auth=TENANT_ADMIN_AUTHED,
        )
    assert exc.value.status_code == status_code


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exception",
    [HTTPException(status_code=500, detail="Error"), Exception("Error")],
)
@pytest.mark.parametrize(
    "roles",
    [["issuer"], ["verifier"], ["issuer", "verifier"]],
)
async def test_create_tenant_fail_onboard_exception(exception, roles):
    mock_admin_controller = AsyncMock()
    mock_admin_controller.multitenancy.create_wallet = AsyncMock(
        return_value=create_wallet_response
    )
    mock_admin_controller.multitenancy.delete_wallet = AsyncMock()

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.onboard_tenant",
        side_effect=exception,
    ) as mock_onboard, patch(
        "app.routes.admin.tenants.assert_actor_name",
        return_value=False,
    ), pytest.raises(
        type(exception), match="Error"
    ):
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            mock_admin_controller
        )
        await create_tenant(
            body=create_tenant_body.model_copy(update={"roles": roles}),
            admin_auth=TENANT_ADMIN_AUTHED,
        )

    # Assert created wallet is deleted if something went wrong in onboarding
    mock_onboard.assert_awaited_once()
    mock_admin_controller.multitenancy.delete_wallet.assert_awaited_once_with(
        wallet_id=wallet_id
    )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_delete_tenant_by_id_success(group_id):
    # Mock the structure of admin_controller -> multitenancy -> delete_wallet
    multitenancy_mock = AsyncMock(delete_wallet=AsyncMock())
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_wallet_and_assert_valid_group",
        return_value=AsyncMock(),
    ) as mock_assert_valid_group, patch(
        "app.routes.admin.tenants.fetch_actor_by_id", return_value=None
    ), patch(
        "app.routes.admin.tenants.remove_actor_by_id", return_value=AsyncMock()
    ), patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await delete_tenant_by_id(
            wallet_id=wallet_id, group_id=group_id, admin_auth=TENANT_ADMIN_AUTHED
        )

        mock_assert_valid_group.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            group_id=group_id,
            logger=ANY,
        )

        # Assert that delete_wallet was called with the correct wallet_id
        admin_controller_mock.multitenancy.delete_wallet.assert_awaited_once_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_delete_tenant_by_id_success_actor(group_id):
    # Mock the structure of admin_controller -> multitenancy -> delete_wallet
    multitenancy_mock = AsyncMock(delete_wallet=AsyncMock())
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_wallet_and_assert_valid_group",
        return_value=AsyncMock(),
    ) as mock_assert_valid_group, patch(
        "app.routes.admin.tenants.fetch_actor_by_id", return_value=AsyncMock()
    ) as mock_fetch_actor, patch(
        "app.routes.admin.tenants.remove_actor_by_id", return_value=AsyncMock()
    ) as mock_delete_actor, patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await delete_tenant_by_id(
            wallet_id=wallet_id, group_id=group_id, admin_auth=TENANT_ADMIN_AUTHED
        )

        mock_assert_valid_group.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            group_id=group_id,
            logger=ANY,
        )

        mock_fetch_actor.assert_called_once_with(wallet_id)
        mock_delete_actor.assert_called_once_with(wallet_id)

        # Assert that delete_wallet was called with the correct wallet_id
        admin_controller_mock.multitenancy.delete_wallet.assert_awaited_once_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
async def test_delete_tenant_by_id_fail_wrong_group():
    # Setup wallet return object including the group_id it belongs to
    wallet_return_obj = AsyncMock()
    wallet_return_obj.settings = {"wallet.group_id": "correct_group"}

    # Mock the get_wallet call to return the above object
    multitenancy_mock = AsyncMock(get_wallet=AsyncMock(return_value=wallet_return_obj))
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Expect an HTTPException due to group mismatch
        with pytest.raises(HTTPException) as exc_info:
            await delete_tenant_by_id(
                wallet_id=wallet_id,
                group_id="wrong_group",
                admin_auth=TENANT_ADMIN_AUTHED,
            )

        assert exc_info.value.status_code == 404
        # Ensure the get_wallet was called as expected
        admin_controller_mock.multitenancy.get_wallet.assert_awaited_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_get_wallet_auth_token_success(group_id):
    # Mock the structure of admin_controller -> multitenancy -> get_auth_token
    multitenancy_mock = AsyncMock(get_auth_token=AsyncMock())
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_wallet_and_assert_valid_group",
        return_value=AsyncMock(),
    ) as mock_assert_valid_group, patch(
        "app.routes.admin.tenants.fetch_actor_by_id", return_value=None
    ), patch(
        "app.routes.admin.tenants.remove_actor_by_id", return_value=AsyncMock()
    ), patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await get_wallet_auth_token(
            wallet_id=wallet_id, group_id=group_id, admin_auth=TENANT_ADMIN_AUTHED
        )

        mock_assert_valid_group.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            group_id=group_id,
            logger=ANY,
        )

        # Assert that get_auth_token was called with the correct wallet_id
        admin_controller_mock.multitenancy.get_auth_token.assert_awaited_once_with(
            wallet_id=wallet_id, body=CreateWalletTokenRequest()
        )


@pytest.mark.anyio
async def test_get_wallet_auth_token_fail_wrong_group():
    # Setup wallet return object including the group_id it belongs to
    wallet_return_obj = AsyncMock()
    wallet_return_obj.settings = {"wallet.group_id": "correct_group"}

    # Mock the get_wallet call to return the above object
    multitenancy_mock = AsyncMock(get_wallet=AsyncMock(return_value=wallet_return_obj))
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Expect an HTTPException due to group mismatch
        with pytest.raises(HTTPException) as exc_info:
            await get_wallet_auth_token(
                wallet_id=wallet_id,
                group_id="wrong_group",
                admin_auth=TENANT_ADMIN_AUTHED,
            )

        assert exc_info.value.status_code == 404
        # Ensure the get_wallet was called as expected
        admin_controller_mock.multitenancy.get_wallet.assert_awaited_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_update_tenant_success(group_id):
    body = UpdateTenantRequest()
    admin_controller_mock = AsyncMock()

    # Patch the dependencies
    with patch(
        "app.routes.admin.tenants.get_wallet_and_assert_valid_group",
        return_value=AsyncMock(),
    ) as mock_assert_valid_group, patch(
        "app.routes.admin.tenants.handle_tenant_update",
        return_value=AsyncMock(),
    ) as mock_handle_tenant_update, patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.tenant_from_wallet_record",
        return_value=Mock(),
    ):

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await update_tenant(
            wallet_id=wallet_id,
            body=body,
            group_id=group_id,
            admin_auth=TENANT_ADMIN_AUTHED,
        )

        # Verify mocks were called as expected
        mock_assert_valid_group.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            group_id=group_id,
            logger=ANY,
        )
        mock_handle_tenant_update.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            update_request=body,
        )


@pytest.mark.anyio
async def test_update_tenant_fail_wrong_group():
    body = UpdateTenantRequest()
    # Setup wallet return object including the group_id it belongs to
    wallet_return_obj = AsyncMock()
    wallet_return_obj.settings = {"wallet.group_id": "correct_group"}

    # Mock the get_wallet call to return the above object
    multitenancy_mock = AsyncMock(get_wallet=AsyncMock(return_value=wallet_return_obj))
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Expect an HTTPException due to group mismatch
        with pytest.raises(HTTPException) as exc_info:
            await update_tenant(
                wallet_id=wallet_id,
                body=body,
                group_id="wrong_group",
                admin_auth=TENANT_ADMIN_AUTHED,
            )

        assert exc_info.value.status_code == 404
        # Ensure the get_wallet was called as expected
        admin_controller_mock.multitenancy.get_wallet.assert_awaited_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_get_tenant_success(group_id):
    admin_controller_mock = AsyncMock()

    # Patch the dependencies
    with patch(
        "app.routes.admin.tenants.get_wallet_and_assert_valid_group",
        return_value=AsyncMock(),
    ) as mock_assert_valid_group, patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.tenant_from_wallet_record",
        return_value=Mock(),
    ):

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await get_tenant(
            wallet_id=wallet_id,
            group_id=group_id,
            admin_auth=TENANT_ADMIN_AUTHED,
        )

        # Verify mocks were called as expected
        mock_assert_valid_group.assert_awaited_once_with(
            admin_controller=admin_controller_mock,
            wallet_id=wallet_id,
            group_id=group_id,
            logger=ANY,
        )


@pytest.mark.anyio
async def test_get_tenant_fail_wrong_group():
    # Setup wallet return object including the group_id it belongs to
    wallet_return_obj = AsyncMock()
    wallet_return_obj.settings = {"wallet.group_id": "correct_group"}

    # Mock the get_wallet call to return the above object
    multitenancy_mock = AsyncMock(get_wallet=AsyncMock(return_value=wallet_return_obj))
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller:

        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Expect an HTTPException due to group mismatch
        with pytest.raises(HTTPException) as exc_info:
            await get_tenant(
                wallet_id=wallet_id,
                group_id="wrong_group",
                admin_auth=TENANT_ADMIN_AUTHED,
            )

        assert exc_info.value.status_code == 404
        # Ensure the get_wallet was called as expected
        admin_controller_mock.multitenancy.get_wallet.assert_awaited_with(
            wallet_id=wallet_id
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_get_tenants_success(group_id):
    admin_controller_mock = AsyncMock()

    # Setup wallets return object including the group_id it belongs to
    wallets_return_obj = AsyncMock()
    wallets_return_obj.results = ["some_wallets", "and_another_one", "why_not_another"]

    # Mock the get_wallets call to return the above object
    multitenancy_mock = AsyncMock(
        get_wallets=AsyncMock(return_value=wallets_return_obj)
    )
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    # Patch the dependencies
    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.tenant_from_wallet_record",
        return_value=Mock(),
    ) as mock_tenant_from_wallet_record:

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await get_tenants(
            wallet_name=wallet_name,
            group_id=group_id,
            admin_auth=TENANT_ADMIN_AUTHED,
        )
        assert mock_tenant_from_wallet_record.call_count == len(
            wallets_return_obj.results
        )


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "some_group"])
async def test_get_tenants_success_no_wallets(group_id):
    admin_controller_mock = AsyncMock()

    # Setup wallets return object to be an empty list
    wallets_return_obj = AsyncMock()
    wallets_return_obj.results = []

    # Mock the get_wallets call to return the above object
    multitenancy_mock = AsyncMock(
        get_wallets=AsyncMock(return_value=wallets_return_obj)
    )
    admin_controller_mock = AsyncMock(multitenancy=multitenancy_mock)

    # Patch the dependencies
    with patch(
        "app.routes.admin.tenants.get_tenant_admin_controller"
    ) as mock_get_admin_controller, patch(
        "app.routes.admin.tenants.tenant_from_wallet_record",
        return_value=Mock(),
    ) as mock_tenant_from_wallet_record:

        # Configure get_tenant_admin_controller to return our mocked admin_controller on enter
        mock_get_admin_controller.return_value.__aenter__.return_value = (
            admin_controller_mock
        )

        # Execute the function under test
        await get_tenants(
            wallet_name=wallet_name,
            group_id=group_id,
            admin_auth=TENANT_ADMIN_AUTHED,
        )
        mock_tenant_from_wallet_record.assert_not_called()
