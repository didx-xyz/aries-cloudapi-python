import pytest

from app.models.issuer import CredentialBase, CredentialType
from shared.exceptions.cloudapi_value_error import CloudApiValueError


def test_credential_base_model():
    with pytest.raises(CloudApiValueError) as exc:
        CredentialBase(type=CredentialType.INDY, indy_credential_detail=None)
    assert exc.value.detail == (
        "indy_credential_detail must be populated if `indy` "
        "credential type is selected"
    )

    with pytest.raises(CloudApiValueError) as exc:
        CredentialBase(type=CredentialType.LD_PROOF, ld_credential_detail=None)
    assert exc.value.detail == (
        "ld_credential_detail must be populated if `ld_proof` "
        "credential type is selected"
    )
