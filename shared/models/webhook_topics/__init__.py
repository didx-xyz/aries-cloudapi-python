from typing import Dict, Literal

# flake8: noqa
from shared.models.webhook_topics.base import *
from shared.models.webhook_topics.endorsement_event import *
from shared.models.webhook_topics.payloads import *

WEBHOOK_TOPIC_ALL = "ALL_WEBHOOKS"

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

topic_mapping: Dict[AcaPyTopics, CloudApiTopics] = {
    "basicmessages": "basic-messages",
    "connections": "connections",
    "endorse_transaction": "endorsements",
    "credential": "deleted_credential",  # This is a previously unhandled event that only contains state:deleted
    "issue_credential": "credentials",
    "issue_credential_v2_0": "credentials",
    "issue_credential_v2_0_indy": "credentials_indy",
    "issue_credential_v2_0_ld_proof": "credentials_ld",
    "revocation_registry": "revocation",
    "issuer_cred_rev": "issuer_cred_rev",
    "out_of_band": "oob",
    "present_proof": "proofs",
    "present_proof_v2_0": "proofs",
    "problem_report": "problem_report",
}
