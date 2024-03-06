from typing import Dict

from shared.models.webhook_events.topics import AcaPyTopics, CloudApiTopics

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
