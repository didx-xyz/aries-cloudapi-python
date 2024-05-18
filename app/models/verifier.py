from enum import Enum
from typing import Optional, Union

from aries_cloudcontroller import DIFPresSpec, DIFProofRequest, IndyPresSpec
from aries_cloudcontroller import IndyProofRequest as AcaPyIndyProofRequest
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from shared.exceptions import CloudApiValueError
from shared.models.protocol import PresentProofProtocolVersion


class ProofRequestType(str, Enum):
    INDY: str = "indy"
    JWT: str = "jwt"
    LD_PROOF: str = "ld_proof"


class IndyProofRequest(AcaPyIndyProofRequest):
    name: str = Field(default="Proof", description="Proof request name")
    version: str = Field(default="1.0", description="Proof request version")


class ProofRequestBase(BaseModel):
    type: ProofRequestType = ProofRequestType.INDY
    indy_proof_request: Optional[IndyProofRequest] = None
    dif_proof_request: Optional[DIFProofRequest] = None

    @model_validator(mode="before")
    @classmethod
    def check_indy_proof_request(cls, values: Union[dict, "ProofRequestBase"]):
        # pydantic v2 removed safe way to get key, because `values` can be a dict or this type
        if not isinstance(values, dict):
            values = values.__dict__

        proof_type = values.get("type")
        indy_proof = values.get("indy_proof_request")
        dif_proof = values.get("dif_proof_request")

        if proof_type == ProofRequestType.INDY and indy_proof is None:
            raise CloudApiValueError(
                "indy_proof_request must be populated if `indy` type is selected"
            )

        if proof_type == ProofRequestType.LD_PROOF and dif_proof is None:
            raise CloudApiValueError(
                "dif_proof_request must be populated if `ld_proof` type is selected"
            )

        if proof_type == ProofRequestType.INDY and dif_proof is not None:
            raise CloudApiValueError(
                "dif_proof_request must not be populated if `indy` type is selected"
            )

        if proof_type == ProofRequestType.LD_PROOF and indy_proof is not None:
            raise CloudApiValueError(
                "indy_proof_request must not be populated if `ld_proof` type is selected"
            )

        return values


class ProofRequestMetadata(BaseModel):
    protocol_version: PresentProofProtocolVersion = PresentProofProtocolVersion.V2
    comment: Optional[str] = None
    trace: Optional[bool] = None


class CreateProofRequest(ProofRequestBase, ProofRequestMetadata):
    save_exchange_record: bool = Field(
        default=False,
        description="Whether the presentation exchange record should be saved on completion",
    )


class SendProofRequest(CreateProofRequest):
    connection_id: str


class ProofId(BaseModel):
    proof_id: str


class AcceptProofRequest(ProofId):
    type: ProofRequestType = ProofRequestType.INDY
    indy_presentation_spec: Optional[IndyPresSpec] = None
    dif_presentation_spec: Optional[DIFPresSpec] = None
    save_exchange_record: bool = Field(
        default=False,
        description="Whether the presentation exchange record should be saved on completion",
    )

    @field_validator("indy_presentation_spec", mode="before")
    @classmethod
    def check_indy_presentation_spec(cls, value, values: ValidationInfo):
        if values.data.get("type") == ProofRequestType.INDY and value is None:
            raise CloudApiValueError(
                "indy_presentation_spec must be populated if `indy` type is selected"
            )
        return value

    @field_validator("dif_presentation_spec", mode="before")
    @classmethod
    def check_dif_presentation_spec(cls, value, values: ValidationInfo):
        if values.data.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise CloudApiValueError(
                "dif_presentation_spec must be populated if `ld_proof` type is selected"
            )
        return value


class RejectProofRequest(ProofId):
    problem_report: str = Field(
        default="Rejected",
        description="Message to send with the rejection",
    )
    delete_proof_record: bool = Field(
        default=False,
        description=(
            "(True) delete the proof exchange record after rejecting, or "
            "(default, False) preserve the record after rejecting"
        ),
    )

    @field_validator("problem_report", mode="before")
    @classmethod
    def validate_problem_report(cls, value):
        if value == "":
            raise CloudApiValueError("problem_report cannot be an empty string")
        return value
