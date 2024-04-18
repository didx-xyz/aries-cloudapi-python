import pytest

from app.models.tenants import (
    CreateTenantRequest,
    UpdateTenantRequest,
    allowable_special_chars,
)
from shared.exceptions.cloudapi_value_error import CloudApiValueError


def test_create_tenant_model_wallet_label():
    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="a" * 101)
    assert exc.value.detail == "wallet_label has a max length of 100 characters"

    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="^")
    assert exc.value.detail == (
        "wallet_label may not contain certain special characters. "
        "Must be alphanumeric, may include spaces, and the following special "
        f"characters are allowed: {allowable_special_chars}"
    )


def test_create_tenant_model_wallet_name():
    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="a", wallet_name="a" * 101)
    assert exc.value.detail == "wallet_name has a max length of 100 characters"

    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="a", wallet_name="^")
    assert exc.value.detail == (
        "wallet_name may not contain certain special characters. "
        "Must be alphanumeric, may include spaces, and the following special "
        f"characters are allowed: {allowable_special_chars}"
    )


def test_create_tenant_model_group_id():
    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="a", group_id="a" * 51)
    assert exc.value.detail == "group_id has a max length of 50 characters"

    with pytest.raises(CloudApiValueError) as exc:
        CreateTenantRequest(wallet_label="a", group_id="^")
    assert exc.value.detail == (
        "group_id may not contain certain special characters. "
        "Must be alphanumeric, may include spaces, and the following special "
        f"characters are allowed: {allowable_special_chars}"
    )


def test_update_tenant_model_wallet_label():
    with pytest.raises(CloudApiValueError) as exc:
        UpdateTenantRequest(wallet_label="a" * 101)
    assert exc.value.detail == "wallet_label has a max length of 100 characters"

    with pytest.raises(CloudApiValueError) as exc:
        UpdateTenantRequest(wallet_label="^")
    assert exc.value.detail == (
        "wallet_label may not contain certain special characters. "
        "Must be alphanumeric, may include spaces, and the following special "
        f"characters are allowed: {allowable_special_chars}"
    )
