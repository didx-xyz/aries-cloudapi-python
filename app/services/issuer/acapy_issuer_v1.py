from typing import Dict, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    CredAttrSpec,
    CredentialPreview,
    V10CredentialConnFreeOfferRequest,
    V10CredentialExchange,
    V10CredentialProposalRequestMand,
    V10CredentialStoreRequest,
)

from app.exceptions.cloud_api_error import CloudApiException
from app.models.issuer import CredentialBase, CredentialType, CredentialWithConnection
from app.services.issuer.acapy_issuer import Issuer
from app.util.credentials import cred_id_no_version
from shared.log_config import get_logger
from shared.models.conversion import credential_record_to_model_v1
from shared.models.topics import CredentialExchange

logger = get_logger(__name__)


class IssuerV1(Issuer):
    @classmethod
    async def send_credential(
        cls, controller: AcaPyClient, credential: CredentialWithConnection
    ):
        if credential.type != CredentialType.INDY:
            raise CloudApiException(
                f"Only Indy credential types are supported in v1. Requested type: {credential.type}",
                status_code=400,
            )

        bound_logger = logger.bind(body=credential)
        bound_logger.debug("Getting credential preview from attributes")
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.indy_credential_detail.attributes
        )

        bound_logger.debug("Issue v1 credential (automated)")
        record = await controller.issue_credential_v1_0.issue_credential_automated(
            body=V10CredentialProposalRequestMand(
                connection_id=credential.connection_id,
                credential_proposal=credential_preview,
                cred_def_id=credential.indy_credential_detail.credential_definition_id,
            )
        )

        bound_logger.debug("Returning v1 credential result as CredentialExchange.")
        return cls.__record_to_model(record)

    @classmethod
    async def create_offer(cls, controller: AcaPyClient, credential: CredentialBase):
        if credential.type != CredentialType.INDY:
            raise CloudApiException(
                f"Only Indy credential types are supported in v1. Requested type: {credential.type}",
                status_code=400,
            )

        bound_logger = logger.bind(body=credential)
        bound_logger.debug("Getting credential preview from attributes")
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.indy_credential_detail.attributes
        )

        bound_logger.debug("Creating v1 credential offer")
        record = await controller.issue_credential_v1_0.create_offer(
            body=V10CredentialConnFreeOfferRequest(
                credential_preview=credential_preview,
                cred_def_id=credential.indy_credential_detail.credential_definition_id,
            )
        )

        bound_logger.debug("Returning v1 create offer result as CredentialExchange.")
        return cls.__record_to_model(record)

    @classmethod
    async def request_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Sending v1 credential request")
        record = await controller.issue_credential_v1_0.send_request(
            cred_ex_id=credential_exchange_id
        )

        bound_logger.debug("Returning v1 send request result as CredentialExchange.")
        return cls.__record_to_model(record)

    @classmethod
    async def store_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Storing v1 credential record")
        record = await controller.issue_credential_v1_0.store_credential(
            cred_ex_id=credential_exchange_id, body=V10CredentialStoreRequest()
        )

        bound_logger.debug(
            "Returning v1 store credential result as CredentialExchange."
        )
        return cls.__record_to_model(record)

    @classmethod
    async def delete_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Getting v1 credential record")
        record = await controller.issue_credential_v1_0.get_record(
            cred_ex_id=credential_exchange_id
        )

        bound_logger.debug("Deleting v1 credential record")
        await controller.issue_credential_v1_0.delete_record(
            cred_ex_id=credential_exchange_id
        )

        # also delete indy credential
        if record.credential_id:
            bound_logger.debug("Deleting indy credential")
            await controller.credentials.delete_record(
                credential_id=record.credential_id
            )
        bound_logger.debug("Successfully deleted credential.")

    @classmethod
    async def get_records(
        cls, controller: AcaPyClient, connection_id: Optional[str] = None
    ):
        bound_logger = logger.bind(body={"connection_id": connection_id})
        bound_logger.debug("Getting v1 credential records by connection id")
        result = await controller.issue_credential_v1_0.get_records(
            connection_id=connection_id,
        )

        if not result.results:
            bound_logger.debug("No v1 record results.")
            return []

        bound_logger.debug("Returning v1 record results as CredentialExchange.")
        return [cls.__record_to_model(record) for record in result.results]

    @classmethod
    async def get_record(cls, controller: AcaPyClient, credential_exchange_id: str):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Getting v1 credential record")
        record = await controller.issue_credential_v1_0.get_record(
            cred_ex_id=credential_exchange_id,
        )

        bound_logger.debug("Returning v1 credential record as CredentialExchange.")
        return cls.__record_to_model(record)

    @classmethod
    def __record_to_model(cls, record: V10CredentialExchange) -> CredentialExchange:
        return credential_record_to_model_v1(record)

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
