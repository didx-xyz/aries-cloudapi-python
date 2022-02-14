import logging
from typing import Dict, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredAttrSpec,
    CredentialPreview,
    V10CredentialExchange,
    V10CredentialProposalRequestMand,
)
from aries_cloudcontroller.model.v10_credential_store_request import (
    V10CredentialStoreRequest,
)

from app.generic.issuer.facades.acapy_issuer import Issuer
from app.generic.issuer.models import (
    Credential,
)
from app.generic.issuer.facades.acapy_issuer_utils import cred_id_no_version
from shared_models import CredentialExchange, IssueCredentialProtocolVersion

logger = logging.getLogger(__name__)


class IssuerV1(Issuer):
    @classmethod
    async def send_credential(cls, controller: AcaPyClient, credential: Credential):
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.attributes
        )

        record = await controller.issue_credential_v1_0.issue_credential_automated(
            body=V10CredentialProposalRequestMand(
                connection_id=credential.connection_id,
                credential_proposal=credential_preview,
                auto_remove=False,
                cred_def_id=credential.cred_def_id,
            )
        )

        return cls.__record_to_model(record)

    @classmethod
    async def request_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        credential_exchange_id = cred_id_no_version(credential_exchange_id)
        record = await controller.issue_credential_v1_0.send_request(
            cred_ex_id=credential_exchange_id
        )

        return cls.__record_to_model(record)

    @classmethod
    async def store_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        credential_exchange_id = cred_id_no_version(credential_exchange_id)
        record = await controller.issue_credential_v1_0.store_credential(
            cred_ex_id=credential_exchange_id, body=V10CredentialStoreRequest()
        )

        return cls.__record_to_model(record)

    @classmethod
    async def delete_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        credential_exchange_id = cred_id_no_version(credential_exchange_id)
        record = await controller.issue_credential_v1_0.get_record(
            cred_ex_id=credential_exchange_id
        )

        await controller.issue_credential_v1_0.delete_record(
            cred_ex_id=credential_exchange_id
        )

        # also delete indy credential
        if record.credential_id:
            await controller.credentials.delete_record(
                credential_id=record.credential_id
            )

    @classmethod
    async def get_records(
        cls, controller: AcaPyClient, connection_id: Optional[str] = None
    ):
        result = await controller.issue_credential_v1_0.get_records(
            connection_id=connection_id,
        )

        if not result.results:
            return []

        return [cls.__record_to_model(record) for record in result.results]

    @classmethod
    async def get_record(cls, controller: AcaPyClient, credential_exchange_id: str):
        credential_exchange_id = cred_id_no_version(credential_exchange_id)
        record = await controller.issue_credential_v1_0.get_record(
            cred_ex_id=credential_exchange_id,
        )

        return cls.__record_to_model(record)

    @classmethod
    def __record_to_model(cls, record: V10CredentialExchange) -> CredentialExchange:
        attributes = cls.__attributes_from_record(record)

        return CredentialExchange(
            credential_id=f"v1-{record.credential_exchange_id}",
            role=record.role,
            created_at=record.created_at,
            updated_at=record.updated_at,
            attributes=attributes,
            protocol_version=IssueCredentialProtocolVersion.v1,
            schema_id=record.schema_id,
            credential_definition_id=record.credential_definition_id,
            state=cls.__v1_state_to_rfc_state(record.state),
            connection_id=record.connection_id,
        )

    @classmethod
    def __attributes_from_record(
        cls, record: V10CredentialExchange
    ) -> Optional[Dict[str, str]]:
        preview = None

        if (
            record.credential_proposal_dict
            and record.credential_proposal_dict.credential_proposal
        ):
            preview = record.credential_proposal_dict.credential_proposal

        return (
            {attr.name: attr.value for attr in preview.attributes} if preview else None
        )

    @classmethod
    def __preview_from_attributes(
        cls,
        attributes: Dict[str, str],
    ) -> CredentialPreview:
        return CredentialPreview(
            attributes=[
                CredAttrSpec(name=name, value=value)
                for name, value in attributes.items()
            ]
        )

    @classmethod
    def __v1_state_to_rfc_state(cls, state: Optional[str]) -> Optional[str]:
        translation_dict = {
            "proposal_sent": "proposal-sent",
            "proposal_received": "proposal-received",
            "offer_sent": "offer-sent",
            "offer_received": "offer-received",
            "request_sent": "request-sent",
            "request_received": "request-received",
            "credential_issued": "credential-issued",
            "credential_received": "credential-received",
            "credential_acked": "done",
        }

        if not state or state not in translation_dict:
            return None

        return translation_dict[state]
