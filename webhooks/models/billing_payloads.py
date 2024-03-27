from pydantic import BaseModel, Field
from typing import Literal


class LagoEvent(BaseModel):
    transaction_id: str
    external_customer_id: str


class CredentialBillingEvent(LagoEvent):
    code: Literal["issue_done"] = Field("issue_done")


class ProofBillingEvent(LagoEvent):
    code: Literal["proof_done"] = Field("proof_done")


class CredDefBillingEvent(LagoEvent):
    code: Literal["cred_def"] = Field("cred_def")


class RevRegDefBillingEvent(LagoEvent):
    code: Literal["rev_reg_def"] = Field("rev_reg_def")


class RevRegEntryBillingEvent(LagoEvent):
    code: Literal["rev_reg_entry"] = Field("rev_reg_entry")


class AttribBillingEvent(LagoEvent):
    code: Literal["attrib"] = Field("attrib")


class RevocationBillingEvent(LagoEvent):
    code: Literal["revoked"] = Field("revoked")


class EndorsementBillingEvent(
    CredDefBillingEvent,
    RevRegDefBillingEvent,
    RevRegEntryBillingEvent,
    AttribBillingEvent,
):
    pass


class BillingEvent(
    CredentialBillingEvent,
    ProofBillingEvent,
    EndorsementBillingEvent,
    RevocationBillingEvent,
):
    pass
