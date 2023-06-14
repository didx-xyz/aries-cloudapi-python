import logging
from typing import Optional

from aries_cloudcontroller import (
    AcaPyClient,
    V20PresCreateRequestRequest,
    V20PresProblemReportRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)

from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared import PresentationExchange, pres_id_no_version
from shared import presentation_record_to_model as record_to_model
from shared.cloud_api_error import CloudApiException

logger = logging.getLogger(__name__)


class VerifierV2(Verifier):
    @classmethod
    async def get_credentials_for_request(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id=proof_id)
        try:
            return await controller.present_proof_v2_0.get_matching_credentials(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while getting matching credentials: %r", e
            )
            raise CloudApiException("Failed to get credentials for request.") from e

    @classmethod
    async def get_proof_records(cls, controller: AcaPyClient):
        try:
            presentation_exchange = await controller.present_proof_v2_0.get_records()
            return [record_to_model(rec) for rec in presentation_exchange.results or []]
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while getting records: %r", e
            )
            raise CloudApiException("Failed to get proof records.") from e

    @classmethod
    async def get_proof_record(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id)
        try:
            presentation_exchange = await controller.present_proof_v2_0.get_record(
                pres_ex_id=pres_ex_id
            )
            return record_to_model(presentation_exchange)
        except Exception as e:
            logger.exception("An unexpected error occurred while getting record: %r", e)
            raise CloudApiException("Failed to get proof record.") from e

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str):
        pres_ex_id = pres_id_no_version(proof_id=proof_id)
        try:
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while deleting record: %r", e
            )
            raise CloudApiException("Failed to delete record.") from e

    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
    ) -> PresentationExchange:
        try:
            proof_record = await controller.present_proof_v2_0.create_proof_request(
                body=V20PresCreateRequestRequest(
                    presentation_request=V20PresRequestByFormat(
                        indy=proof_request.proof_request
                    ),
                    auto_verify=proof_request.auto_verify,
                    comment=proof_request.comment,
                    trace=proof_request.trace,
                )
            )
            return record_to_model(proof_record)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while creating presentation request: %r",
                e,
            )
            raise CloudApiException("Failed to create presentation request.") from e

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
    ) -> PresentationExchange:
        try:
            presentation_exchange = (
                await controller.present_proof_v2_0.send_request_free(
                    body=V20PresSendRequestRequest(
                        connection_id=proof_request.connection_id,
                        presentation_request=V20PresRequestByFormat(
                            dif=None, indy=proof_request.proof_request
                        ),
                        auto_verify=proof_request.auto_verify,
                        comment=proof_request.comment,
                        trace=proof_request.trace,
                    )
                )
            )
            return record_to_model(presentation_exchange)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending presentation request: %r", e
            )
            raise CloudApiException("Failed to send presentation request.") from e

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        pres_ex_id = pres_id_no_version(proof_id=proof_request.proof_id)
        try:
            presentation_record = await controller.present_proof_v2_0.send_presentation(
                pres_ex_id=pres_ex_id,
                body=V20PresSpecByFormatRequest(indy=proof_request.presentation_spec),
            )
            return record_to_model(presentation_record)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending a proof presentation: %r", e
            )
            raise CloudApiException("Failed to send proof presentation.") from e

    @classmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, proof_request: RejectProofRequest
    ) -> None:
        # get the record
        pres_ex_id = pres_id_no_version(proof_id=proof_request.proof_id)
        # Report problem if desired
        if proof_request.problem_report:
            try:
                await controller.present_proof_v2_0.report_problem(
                    pres_ex_id=pres_ex_id,
                    body=V20PresProblemReportRequest(
                        description=proof_request.problem_report
                    ),
                )
            except Exception as e:
                logger.exception(
                    "An unexpected error occurred while reporting problem: %r", e
                )
                raise CloudApiException("Failed to report problem.") from e

        try:
            # delete exchange record
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while deleting record: %r", e
            )
            raise CloudApiException("Failed to delete record.") from e
