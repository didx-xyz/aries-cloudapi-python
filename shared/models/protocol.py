from enum import Enum


class PresentProofProtocolVersion(str, Enum):
    v1: str = "v1"
    v2: str = "v2"


class IssueCredentialProtocolVersion(str, Enum):
    v1: str = "v1"
    v2: str = "v2"


def pres_id_no_version(proof_id: str) -> str:
    if proof_id.startswith("v2-") or proof_id.startswith("v1-"):
        return proof_id[3:]
    else:
        raise ValueError("proof_id must start with prefix `v1-` or `v2-`.")
