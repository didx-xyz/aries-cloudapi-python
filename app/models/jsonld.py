from typing import Any, Dict, Optional

from aries_cloudcontroller import SignatureOptions
from pydantic import BaseModel


class JsonLdSignRequest(BaseModel):
    credential_id: Optional[str]
    credential: Optional[Dict[str, Any]]
    verkey: Optional[str] = None
    pub_did: Optional[str] = None
    signature_options: Optional[SignatureOptions] = None


class JsonLdVerifyRequest(BaseModel):
    doc: Dict[str, Any]
    public_did: Optional[str] = None
    verkey: Optional[str] = None
