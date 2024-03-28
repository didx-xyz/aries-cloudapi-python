from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class LagoTopics(Enum):
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
    code: Literal[LagoTopics.CREDENTIAL] = Field(LagoTopics.CREDENTIAL)


class ProofBillingEvent(LagoEvent):
    code: Literal[LagoTopics.PROOF] = Field(LagoTopics.PROOF)


class CredDefBillingEvent(LagoEvent):
    code: Literal[LagoTopics.CRED_DEF] = Field(LagoTopics.CRED_DEF)


class RevRegDefBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REV_REG_ENTRY] = Field(LagoTopics.REV_REG_DEF)


class RevRegEntryBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REV_REG_ENTRY] = Field(LagoTopics.REV_REG_ENTRY)


class AttribBillingEvent(LagoEvent):
    code: Literal[LagoTopics.ATTRIB] = Field(LagoTopics.ATTRIB)


class RevocationBillingEvent(LagoEvent):
    code: Literal[LagoTopics.REVOCATION] = Field(LagoTopics.REVOCATION)
