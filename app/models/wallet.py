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
    Extends the AcapyDIDCreate model with smart defaults and a simplified interface.
    Handles deprecated `options` field from client requests by populating `key_type` and `did`.
    Downstream processes should use the appropriate `options` structure based on the model's fields.
    """

    method: Optional[StrictStr] = Field(
        default="sov",
        description="Method for the requested DID. Supported methods are 'sov', `web`, `did:peer:2` or `did:peer:4`.",
        examples=["sov", "key", "did:peer:2", "did:peer:4"],
    )
    options: Optional[DIDCreateOptions] = Field(
        default=None,
        deprecated=True,
        description="(Deprecated) Define a key type and/or a DID depending on the chosen DID method.",
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
        description="Specify the final value of DID (including `did:<method>:` prefix) if the method supports it.",
        strict=True,
    )

    @model_validator(mode="before")
    @classmethod
    def handle_deprecated_options(cls, values: dict) -> dict:
        """
        Handle deprecated `options` field from client requests.
        Populate `key_type` and `did` fields based on `options` if they aren't explicitly provided.
        Do not duplicate data by setting `options` based on `key_type` and `did`.

        Args:
            values: Dictionary containing the model fields

        Returns:
            Updated values dict with `key_type` and `did` populated from `options` if necessary
        """
        options = values.get("options")

        if options:
            # Populate `key_type` from `options` if not explicitly provided
            if not values.get("key_type"):
                values["key_type"] = options.get("key_type", "ed25519")

            # Populate `did` from `options` if not explicitly provided
            if not values.get("did"):
                values["did"] = options.get("did")

        return values

    def to_acapy_options(self) -> DIDCreateOptions:
        """
        Convert the model's fields into the `DIDCreateOptions` structure expected by ACA-Py.

        Returns:
            An instance of `DIDCreateOptions` populated with `key_type` and `did`.
        """
        return DIDCreateOptions(key_type=self.key_type, did=self.did)
