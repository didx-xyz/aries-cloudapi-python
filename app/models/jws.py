from typing import Dict, Optional

from pydantic import BaseModel, Field


class JWSCreateRequest(BaseModel):
    did: str = Field(
        ..., examples=["did:key:z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq"]
    )
    headers: Dict = Field(default={})
    payload: Dict = Field(default={})
    verification_method: str = Field(
        ...,
        description="Information used for proof verification",
        examples=[
            "did:key:z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq#z6MkjCj"
            "xuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq"
        ],
    )


class JWSCreateResponse(BaseModel):
    jws: str = Field(
        ...,
        examples=[
            "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJFZERTQSIsICJraWQiOiAiZGlkOmtleTp6Nk1rakNqeHVUWHhWUFdTOUpZajJaaUt0S3ZTUzFz"
            "ckM2a0JSZXM0V0NCMm1TV3EjejZNa2pDanh1VFh4VlBXUzlKWWoyWmlLdEt2U1Mxc3JDNmtCUmVzNFdDQjJtU1dxIn0.e30.rOLhhAaM"
            "fWb_rFzgKofXRuv72bj7SjRcPieICMV1TE1eJrTG-RoIJ6crrEc_mRmnFtI7dExEZAnCqd4LzGozAA"
        ],
    )


class JWSVerifyRequest(JWSCreateResponse):
    pass  # Verify request is same as create response


class JWSVerifyResponse(BaseModel):
    error: Optional[str] = Field(default=None, description="Error text")
    headers: Dict = Field(
        description="Headers from verified JWT.",
        examples=[
            {
                "typ": "JWT",
                "alg": "EdDSA",
                "kid": "did:key:z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq#z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kB"
                "Res4WCB2mSWq",
            }
        ],
    )
    kid: str = Field(
        description="kid of signer",
        examples=[
            "did:key:z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq#z6MkjCjxuTXxVPWS9JYj2ZiKtKvSS1srC6kBRes4WCB2mSWq"
        ],
    )
    payload: Dict = Field(description="Payload from verified JWT")
    valid: bool = Field(...)
