import logging
from typing import Dict, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    V20CredAttrSpec,
    V20CredExRecord,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredPreview,
    V20CredExFree,
    V20CredRequestRequest,
)
from aries_cloudcontroller.model.v20_cred_store_request import V20CredStoreRequest
from generic.issuer.facades.acapy_issuer import Issuer
from generic.issuer.models import (
    Credential,
    CredentialExchange,
    IssueCredentialProtocolVersion,
)

logger = logging.getLogger(__name__)


class IssuerV2(Issuer):
    @classmethod
    async def send_credential(cls, controller: AcaPyClient, credential: Credential):
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.attributes
        )

        record = await controller.issue_credential_v2_0.issue_credential_automated(
            body=V20CredExFree(
                connection_id=credential.connection_id,
                credential_preview=credential_preview,
                auto_remove=False,
                filter=V20CredFilter(
                    indy=V20CredFilterIndy(
                        cred_def_id=credential.cred_def_id,
                    )
                ),
            )
        )

        return cls.__record_to_model(record)

    @classmethod
    async def request_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        record = await controller.issue_credential_v2_0.send_request(
            cred_ex_id=credential_exchange_id, body=V20CredRequestRequest()
        )

        return cls.__record_to_model(record)

    @classmethod
    async def store_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        record = await controller.issue_credential_v2_0.store_credential(
            cred_ex_id=credential_exchange_id, body=V20CredStoreRequest()
        )

        if not record.cred_ex_record:
            raise Exception("No cred_ex_record found on record")

        return cls.__record_to_model(record.cred_ex_record)

    @classmethod
    async def delete_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        record = await controller.issue_credential_v2_0.get_record(
            cred_ex_id=credential_exchange_id
        )

        await controller.issue_credential_v2_0.delete_record(
            cred_ex_id=credential_exchange_id
        )

        # also delete indy credential
        if record.indy and record.indy.cred_id_stored:
            await controller.credentials.delete_record(
                credential_id=record.indy.cred_id_stored
            )

    @classmethod
    def __record_to_model(cls, record: V20CredExRecord) -> CredentialExchange:
        attributes = cls.__attributes_from_record(record)

        schema_id = None
        credential_definition_id = None

        if record.by_format and record.by_format.cred_offer:
            schema_id = record.by_format.cred_offer.get("indy", {}).get(
                "schema_id", None
            )
            credential_definition_id = record.by_format.cred_offer.get("indy", {}).get(
                "cred_def_id", None
            )

        return CredentialExchange(
            credential_id=f"v2-{record.cred_ex_id}",
            role=record.role,
            created_at=record.created_at,
            updated_at=record.updated_at,
            attributes=attributes,
            protocol_version=IssueCredentialProtocolVersion.v2,
            schema_id=schema_id,
            credential_definition_id=credential_definition_id,
            state=record.state,
            connection_id=record.connection_id,
        )

    @classmethod
    async def get_records(
        cls, controller: AcaPyClient, connection_id: Optional[str] = None
    ):
        result = await controller.issue_credential_v2_0.get_records(
            connection_id=connection_id,
        )

        if not result.results:
            return []

        return [
            cls.__record_to_model(record.cred_ex_record)
            for record in result.results
            if record.cred_ex_record
        ]

    @classmethod
    async def get_record(cls, controller: AcaPyClient, credential_exchange_id: str):
        record = await controller.issue_credential_v2_0.get_record(
            cred_ex_id=credential_exchange_id,
        )

        if not record.cred_ex_record:
            raise Exception("Record has not credential exchang record")

        return cls.__record_to_model(record.cred_ex_record)

    @classmethod
    def __preview_from_attributes(
        cls,
        attributes: Dict[str, str],
    ) -> V20CredPreview:
        return V20CredPreview(
            attributes=[
                V20CredAttrSpec(name=name, value=value)
                for name, value in attributes.items()
            ]
        )

    @classmethod
    def __attributes_from_record(
        cls, record: V20CredExRecord
    ) -> Optional[Dict[str, str]]:
        preview = None

        if record.cred_preview:
            preview = record.cred_preview
        elif record.cred_offer and record.cred_offer.credential_preview:
            preview = record.cred_offer.credential_preview
        elif record.cred_proposal and record.cred_proposal.credential_preview:
            preview = record.cred_proposal.credential_preview

        return (
            {attr.name: attr.value for attr in preview.attributes} if preview else None
        )
