from typing import Literal

AcaPyTopics = Literal[
    "basicmessages",
    "connections",
    "credential",
    "endorse_transaction",
    "forward",
    "issue_credential",
    "issue_credential_v2_0",
    "issue_credential_v2_0_indy",
    "issue_credential_v2_0_ld_proof",
    "issuer_cred_rev",
    "out_of_band",
    "ping",
    "present_proof",
    "present_proof_v2_0",
    "revocation_registry",
    "problem_report",
]

CloudApiTopics = Literal[
    "basic-messages",
    "connections",
    "proofs",
    "credentials",
    "credentials_indy",
    "credentials_ld",
    "endorsements",
    "oob",
    "revocation",
    "issuer_cred_rev",
    "problem_report",
]
