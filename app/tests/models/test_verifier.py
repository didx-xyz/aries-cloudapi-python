import pytest
from aries_cloudcontroller import DIFProofRequest, PresentationDefinition

from app.models.verifier import (
    AcceptProofRequest,
    IndyProofRequest,
    ProofRequestBase,
    ProofRequestType,
)
from shared.exceptions.cloudapi_value_error import CloudApiValueError


def test_proof_request_base_model():
    with pytest.raises(CloudApiValueError) as exc:
        ProofRequestBase(type=ProofRequestType.INDY, indy_proof_request=None)
    assert exc.value.detail == (
        "indy_proof_request must be populated if `indy` type is selected"
    )

    with pytest.raises(CloudApiValueError) as exc:
        ProofRequestBase(
            type=ProofRequestType.LD_PROOF,
            indy_proof_request=IndyProofRequest(
                requested_attributes={}, requested_predicates={}
            ),
            dif_proof_request=DIFProofRequest(
                presentation_definition=PresentationDefinition()
            ),
        )
    assert exc.value.detail == (
        "indy_proof_request must not be populated if `ld_proof` type is selected"
    )

    with pytest.raises(CloudApiValueError) as exc:
        ProofRequestBase(
            type=ProofRequestType.INDY,
            indy_proof_request=IndyProofRequest(
                requested_attributes={}, requested_predicates={}
            ),
            dif_proof_request=DIFProofRequest(
                presentation_definition=PresentationDefinition()
            ),
        )
    assert exc.value.detail == (
        "dif_proof_request must not be populated if `indy` type is selected"
    )

    with pytest.raises(CloudApiValueError) as exc:
        ProofRequestBase(type=ProofRequestType.LD_PROOF, dif_proof_request=None)
    assert exc.value.detail == (
        "dif_proof_request must be populated if `ld_proof` type is selected"
    )


def test_accept_proof_request_model():
    with pytest.raises(CloudApiValueError) as exc:
        AcceptProofRequest(type=ProofRequestType.INDY, indy_presentation_spec=None)
    assert exc.value.detail == (
        "indy_presentation_spec must be populated if `indy` type is selected"
    )
    with pytest.raises(CloudApiValueError) as exc:
        AcceptProofRequest(type=ProofRequestType.LD_PROOF, dif_presentation_spec=None)
    assert exc.value.detail == (
        "dif_presentation_spec must be populated if `ld_proof` type is selected"
    )
