from typing import List, Optional

from aries_cloudcontroller.models.indy_cred_info import (
    IndyCredInfo as IndyCredInfoAcaPy,
)
from aries_cloudcontroller.models.vc_record import VCRecord as VCRecordAcaPy
from pydantic import BaseModel, Field
import warnings
from typing import Optional

from aries_cloudcontroller import DIDCreateOptions
from pydantic import BaseModel, Field, StrictStr, model_validator
from typing_extensions import deprecated


class SetDidEndpointRequest(BaseModel):
    endpoint: str = Field(...)


class VCRecord(VCRecordAcaPy):
    credential_id: str = Field(
        ..., alias="record_id", description="Credential identifier"
    )
    record_id: str = Field(
        ...,
        alias="credential_id",
        description="(deprecated - renamed to credential_id) Credential identifier",
        deprecated=True,
    )


class VCRecordList(BaseModel):
    results: Optional[List[VCRecord]] = None


class IndyCredInfo(IndyCredInfoAcaPy):
    credential_id: str = Field(
        ..., alias="referent", description="Credential identifier"
    )
    referent: str = Field(
        ...,
        alias="credential_id",
        description="(deprecated - renamed to credential_id) Credential identifier",
        deprecated=True,
    )


class CredInfoList(BaseModel):
    results: Optional[List[IndyCredInfo]] = None


class DIDCreate(BaseModel):
    method: Optional[StrictStr] = Field(
        default=None,
        description="Method for the requested DID. Supported methods are 'key', 'sov', and any other registered method.",
        examples=["sov", "key", "did:peer:2", "did:peer:4"],
    )
    options: Optional[DIDCreateOptions] = Field(
        default=None,
        deprecated=deprecated("Please use key_type and did fields directly instead."),
        description="To define a key type and/or a did depending on chosen DID method.",
        examples=[{"key_type": "ed25519", "did": "did:peer:2"}],
    )
    seed: Optional[StrictStr] = Field(
        default=None,
        description="Optional seed to use for DID. Must be enabled in configuration before use.",
    )
    key_type: Optional[StrictStr] = Field(
        default="ed25519",
        description="Key type to use for the DID key_pair. Validated with the chosen DID method's supported key types.",
        examples=["ed25519", "x25519", "bls12381g1", "bls12381g2", "bls12381g1g2"],
    )
    did: Optional[str] = Field(
        default=None,
        description="Specify final value of the did (including did:<method>: prefix) if the method supports or requires so.",
        strict=True,
    )

    @model_validator(mode="before")
    def handle_deprecated_options(cls, values: dict) -> dict:
        """
        Handle both deprecated options field and new flattened fields.
        Priority: If both are provided, new fields take precedence.
        """
        options = values.get("options")

        if options:
            warnings.warn(
                "The 'options' field is deprecated. Please use 'key_type' and 'did' fields directly.",
                DeprecationWarning,
                stacklevel=2,
            )

            # Only use options values if new fields are not set
            if not values.get("key_type") and options.get("key_type"):
                values["key_type"] = options["key_type"]
            if not values.get("did") and options.get("did"):
                values["did"] = options["did"]

        # Default key_type to ed25519 if not provided
        if not values.get("key_type"):
            values["key_type"] = "ed25519"

        return values
