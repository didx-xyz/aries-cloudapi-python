from typing import List, Optional

from aries_cloudcontroller.models.indy_cred_info import IndyCredInfo
from aries_cloudcontroller.models.vc_record import VCRecord
from pydantic import BaseModel, Field


class SetDidEndpointRequest(BaseModel):
    endpoint: str = Field(...)


class ExtendedVCRecord(VCRecord):
    credential_id: str = Field(..., alias="record_id")
    record_id: str = Field(..., alias="credential_id")


class VCRecordList(BaseModel):
    results: Optional[List[ExtendedVCRecord]] = None


class ExtendedIndyCredInfo(IndyCredInfo):
    credential_id: str = Field(..., alias="referent")
    referent: str = Field(..., alias="credential_id")


class CredInfoList(BaseModel):
    results: Optional[List[ExtendedIndyCredInfo]] = None
