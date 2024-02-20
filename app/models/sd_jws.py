from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.models.jws import JWSCreateRequest, JWSVerifyResponse


class SDJWSCreateRequest(JWSCreateRequest):  # extend JWSCreateRequest model
    non_sd_list: Optional[List[str]] = Field(default=[])


class SDJWSCreateResponse(BaseModel):
    sd_jws: str = Field(
        ...,
        examples=[],
    )


class SDJWSVerifyRequest(SDJWSCreateResponse):
    pass  # Verify request is same as create response


class SDJWSVerifyResponse(JWSVerifyResponse):  # extend JWSVerifyResponse model
    disclosures: List[List[Union[str, Dict]]] = Field(..., examples=[])
