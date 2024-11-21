import pytest

from app.models.jws import JWSCreateRequest
from shared.exceptions.cloudapi_value_error import CloudApiValueError


def test_jws_create_request():
    # no did or verification_method
    with pytest.raises(CloudApiValueError) as exc:
        JWSCreateRequest(payload={"test": "test_value"})

    assert exc.value.detail == (
        "One of `did` or `verification_method` must be populated."
    )

    # did and verification_method
    with pytest.raises(CloudApiValueError) as exc:
        JWSCreateRequest(
            did="did:sov:AGguR4mc186Tw11KeWd4qq",
            payload={"test": "test_value"},
            verification_method="did:sov:AGguR4mc186Tw11KeWd4qq",
        )

    assert exc.value.detail == (
        "Only one of `did` or `verification_method` can be populated."
    )

    # no payload
    with pytest.raises(CloudApiValueError) as exc:
        JWSCreateRequest(did="did:sov:AGguR4mc186Tw11KeWd4qq")

    assert exc.value.detail == ("`payload` must be populated.")
