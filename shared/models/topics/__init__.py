from typing import Dict, Literal

# flake8: noqa
from shared.models.topics.base import *

WEBHOOK_TOPIC_ALL = "ALL_WEBHOOKS"

AcaPyTopics = Literal[
    "basicmessages",
    "connections",
    "endorse_transaction",
    "forward",
    "issue_credential",
    "issue_credential_v2_0",
    "issue_credential_v2_0_dif",
    "issue_credential_v2_0_indy",
    "issuer_cred_rev",
    "out_of_band",
    "ping",
    "present_proof",
    "present_proof_v2_0",
    "revocation_registry",
]

CloudApiTopics = Literal[
    "basic-messages",
    "connections",
    "proofs",
    "credentials",
    "endorsements",
    "oob",
    "revocation",
    "issuer_cred_rev"
]

topic_mapping: Dict[AcaPyTopics, CloudApiTopics] = {
    "basicmessages": "basic-messages",
    "connections": "connections",
    "endorse_transaction": "endorsements",
    "issue_credential": "credentials",
    "issue_credential_v2_0": "credentials",
    "revocation_registry": "revocation",
    "out_of_band": "oob",
    "present_proof": "proofs",
    "present_proof_v2_0": "proofs",
}
