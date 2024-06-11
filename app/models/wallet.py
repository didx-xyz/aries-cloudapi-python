from typing import List, Optional

from aries_cloudcontroller.models.indy_cred_info import IndyCredInfo as IndyCredInfoAcaPy
from aries_cloudcontroller.models.vc_record import VCRecord as VCRecordAcaPy
from pydantic import BaseModel, Field


class SetDidEndpointRequest(BaseModel):
    endpoint: str = Field(...)


class VCRecord(VCRecordAcaPy):
    credential_id: str = Field(..., alias="record_id")
    record_id: str = Field(..., alias="credential_id")


class VCRecordList(BaseModel):
    results: Optional[List[VCRecord]] = None


class IndyCredInfo(IndyCredInfoAcaPy):
    credential_id: str = Field(..., alias="referent")
    referent: str = Field(..., alias="credential_id")


class CredInfoList(BaseModel):
    results: Optional[List[IndyCredInfo]] = None
