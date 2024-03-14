from enum import Enum
from typing import Literal, Optional

from aries_cloudcontroller import DIFPresSpec, DIFProofRequest, IndyPresSpec
from aries_cloudcontroller import IndyProofRequest as AcaPyIndyProofRequest
from pydantic import BaseModel, Field, ValidationInfo, field_validator

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

    @field_validator("indy_proof_request", mode="before")
    @classmethod
    def check_indy_proof_request(cls, value, values: ValidationInfo):
        if values.data.get("type") == ProofRequestType.INDY and value is None:
            raise ValueError(
                "indy_proof_request must be populated if `indy` type is selected"
            )

        if (
            values.data.get("type") == ProofRequestType.INDY
            and values.data.get("dif_proof_request") is not None
        ):
            raise ValueError(
                "dif_proof_request must not be populated if `indy` type is selected"
            )
        return value

    @field_validator("dif_proof_request", mode="before")
    @classmethod
    def check_dif_proof_request(cls, value, values: ValidationInfo):
        if values.data.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "dif_proof_request must be populated if `ld_proof` type is selected"
            )
        if (
            values.data.get("type") == ProofRequestType.LD_PROOF
            and values.data.get("indy_proof_request") is not None
        ):
            raise ValueError(
                "indy_proof_request must not be populated if `ld_proof` type is selected"
            )
        return value


class ProofRequestMetadata(BaseModel):
    protocol_version: PresentProofProtocolVersion = PresentProofProtocolVersion.v2
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
            raise ValueError(
                "indy_presentation_spec must be populated if `indy` type is selected"
            )
        return value

    @field_validator("dif_presentation_spec", mode="before")
    @classmethod
    def check_dif_presentation_spec(cls, value, values: ValidationInfo):
        if values.data.get("type") == ProofRequestType.LD_PROOF and value is None:
            raise ValueError(
                "dif_presentation_spec must be populated if `ld_proof` type is selected"
            )
        return value


class RejectProofRequest(ProofId):
    problem_report: Optional[str] = None


State = Literal[
    "abandoned",
    "done",
    "presentation-received",
    "presentation-sent",
    "proposal-received",
    "proposal-sent",
    "request-received",
    "request-sent",
]

Role = Literal["prover", "verifier"]
