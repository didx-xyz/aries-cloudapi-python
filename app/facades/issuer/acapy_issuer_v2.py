from typing import Dict, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    V20CredAttrSpec,
    V20CredExFree,
    V20CredExRecord,
    V20CredFilter,
    V20CredFilterIndy,
    V20CredOfferConnFreeRequest,
    V20CredPreview,
    V20CredRequestRequest,
)
from aries_cloudcontroller.model.v20_cred_store_request import V20CredStoreRequest

from app.exceptions.cloud_api_error import CloudApiException
from app.facades.issuer.acapy_issuer import Issuer
from app.models.issuer import Credential, CredentialNoConnection
from app.util.credentials import cred_id_no_version
from shared.log_config import get_logger
from shared.models.conversion import credential_record_to_model_v2
from shared.models.topics import CredentialExchange

logger = get_logger(__name__)


class IssuerV2(Issuer):
    @classmethod
    async def send_credential(cls, controller: AcaPyClient, credential: Credential):
        bound_logger = logger.bind(body=credential)
        bound_logger.debug("Getting credential preview from attributes")
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.attributes
        )

        bound_logger.debug("Issue v2 credential (automated)")
        record = await controller.issue_credential_v2_0.issue_credential_automated(
            body=V20CredExFree(
                connection_id=credential.connection_id,
                credential_preview=credential_preview,
                filter=V20CredFilter(
                    indy=V20CredFilterIndy(
                        cred_def_id=credential.cred_def_id,
                    )
                ),
            )
        )

        bound_logger.debug("Returning v2 credential result as CredentialExchange.")
        return cls.__record_to_model(record)

    @classmethod
    async def create_offer(
        cls, controller: AcaPyClient, credential: CredentialNoConnection
    ):
        bound_logger = logger.bind(body=credential)
        bound_logger.debug("Getting credential preview from attributes")
        credential_preview = cls.__preview_from_attributes(
            attributes=credential.attributes
        )

        bound_logger.debug("Creating v2 credential offer")
        record = (
            await controller.issue_credential_v2_0.issue_credential20_create_offer_post(
                body=V20CredOfferConnFreeRequest(
                    credential_preview=credential_preview,
                    filter=V20CredFilter(
                        indy=V20CredFilterIndy(
                            cred_def_id=credential.cred_def_id,
                        )
                    ),
                )
            )
        )

        bound_logger.debug("Returning v2 create offer result as CredentialExchange.")
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

        bound_logger.debug("Sending v2 credential request")
        record = await controller.issue_credential_v2_0.send_request(
            cred_ex_id=credential_exchange_id, body=V20CredRequestRequest()
        )

        bound_logger.debug("Returning v2 send request result as CredentialExchange.")
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

        bound_logger.debug("Storing v2 credential record")
        record = await controller.issue_credential_v2_0.store_credential(
            cred_ex_id=credential_exchange_id, body=V20CredStoreRequest()
        )

        if not record.cred_ex_record:
            raise CloudApiException("Stored record has no credential exchange record.")

        bound_logger.debug(
            "Returning v2 store credential result as CredentialExchange."
        )
        return cls.__record_to_model(record.cred_ex_record)

    @classmethod
    async def delete_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Getting v2 credential record")
        record = await controller.issue_credential_v2_0.get_record(
            cred_ex_id=credential_exchange_id
        )

        bound_logger.debug("Deleting v2 credential record")
        await controller.issue_credential_v2_0.delete_record(
            cred_ex_id=credential_exchange_id
        )

        # also delete indy credential
        if record.indy and record.indy.cred_id_stored:
            bound_logger.debug("Deleting indy credential")
            await controller.credentials.delete_record(
                credential_id=record.indy.cred_id_stored
            )
        bound_logger.debug("Successfully deleted credential.")

    @classmethod
    async def get_records(
        cls, controller: AcaPyClient, connection_id: Optional[str] = None
    ):
        bound_logger = logger.bind(body={"connection_id": connection_id})
        bound_logger.debug("Getting v2 credential records by connection id")
        result = await controller.issue_credential_v2_0.get_records(
            connection_id=connection_id,
        )

        if not result.results:
            bound_logger.debug("No v2 record results.")
            return []

        bound_logger.debug("Returning v2 record results as CredentialExchange.")
        return [
            cls.__record_to_model(record.cred_ex_record)
            for record in result.results
            if record.cred_ex_record
        ]

    @classmethod
    async def get_record(cls, controller: AcaPyClient, credential_exchange_id: str):
        bound_logger = logger.bind(
            body={"credential_exchange_id": credential_exchange_id}
        )
        bound_logger.debug("Get credential id without version")
        credential_exchange_id = cred_id_no_version(credential_exchange_id)

        bound_logger.debug("Getting v2 credential record")
        record = await controller.issue_credential_v2_0.get_record(
            cred_ex_id=credential_exchange_id,
        )

        if not record.cred_ex_record:
            raise CloudApiException("Record has no credential exchange record.")

        bound_logger.debug("Returning v2 credential record as CredentialExchange.")
        return cls.__record_to_model(record.cred_ex_record)

    @classmethod
    def __record_to_model(cls, record: V20CredExRecord) -> CredentialExchange:
        return credential_record_to_model_v2(record=record)

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
