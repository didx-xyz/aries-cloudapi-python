from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LagoTopics(str, Enum):
    CREDENTIAL = "issue_done"
    PROOF = "proof_done"
    CRED_DEF = "cred_def"
    REV_REG_DEF = "rev_reg_def"
    REV_REG_ENTRY = "rev_reg_entry"
    ATTRIB = "attrib"
    REVOCATION = "revoked"


class LagoEvent(BaseModel):
    transaction_id: str
    external_customer_id: str


class CredentialBillingEvent(LagoEvent):
    code: Literal[LagoTopics.CREDENTIAL] = Field("issue_done")


class ProofBillingEvent(LagoEvent):
    code: Literal[LagoTopics.PROOF] = Field("proof_done")


class CredDefBillingEvent(LagoEvent):
    code: Literal[LagoTopics.CRED_DEF] = Field("cred_def")


class RevRegDefBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REV_REG_DEF] = Field("rev_reg_def")


class RevRegEntryBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REV_REG_ENTRY] = Field("rev_reg_entry")


class AttribBillingEvent(LagoEvent):
    code: Literal[LagoTopics.ATTRIB] = Field("attrib")


class RevocationBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REVOCATION] = Field("revoked")
