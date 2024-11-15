from typing import List, Optional

from aries_cloudcontroller import DIDCreate as DIDCreateAcaPy
from aries_cloudcontroller.models.did_create_options import DIDCreateOptions
from aries_cloudcontroller.models.indy_cred_info import (
    IndyCredInfo as IndyCredInfoAcaPy,
)
from aries_cloudcontroller.models.vc_record import VCRecord as VCRecordAcaPy
from pydantic import BaseModel, Field, StrictStr, model_validator


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


class DIDCreate(DIDCreateAcaPy):
    """
    Extends the AcapyDIDCreate model with smart defaults and simplified interface.
    Automatically handles the options field structure while maintaining compatibility.
    """

    method: Optional[StrictStr] = Field(
        default="sov",
        description="Method for the requested DID. Supported methods are 'sov', `web`, `did:peer:2` or `did:peer:4`.",
        examples=["sov", "key", "did:peer:2", "did:peer:4"],
    )
    options: Optional[DIDCreateOptions] = Field(
        default=None,
        deprecated=True,
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
        examples=["ed25519", "bls12381g2"],
    )
    did: Optional[str] = Field(
        default=None,
        description="Specify final value of did (including did:<method>: prefix) if the method supports/requires it.",
        strict=True,
    )

    @model_validator(mode="before")
    @classmethod
    def handle_deprecated_options(cls, values: dict) -> dict:
        """
        Handle both deprecated options field and new flattened fields.
        Priority: If both are provided, new fields take precedence.
        """

        if not values.get("options"):
            values["options"] = {}
            values["options"]["key_type"] = values.get("key_type") or "ed25519"
            values["options"]["did"] = values.get("did")
        else:
            options: dict = values.get("options")
            if not options.get("key_type"):
                values["options"]["key_type"] = values.get("key_type") or "ed25519"
            if not options.get("did") and values.get("did"):
                values["options"]["did"] = values.get("did")

        return values
