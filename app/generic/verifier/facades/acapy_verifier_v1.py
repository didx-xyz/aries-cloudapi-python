from aries_cloudcontroller import (
    AcaPyClient,
    V10PresentationCreateRequestRequest,
    V10PresentationProblemReportRequest,
    V10PresentationSendRequestRequest,
)

from app.exceptions.cloud_api_error import CloudApiException
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared.log_config import get_logger
from shared.models.conversion import presentation_record_to_model as record_to_model
from shared.models.protocol import pres_id_no_version
from shared.models.topics import PresentationExchange

logger = get_logger(__name__)


class VerifierV1(Verifier):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
    ) -> PresentationExchange:
        bound_logger = logger.bind(body=proof_request)
        bound_logger.debug("Creating v1 proof request")
        presentation_exchange = (
            await controller.present_proof_v1_0.create_proof_request(
                body=V10PresentationCreateRequestRequest(
                    proof_request=proof_request.proof_request,
                    comment=proof_request.comment,
                    trace=False,
                )
            )
        )
        bound_logger.debug("Returning v1 PresentationExchange.")
        return record_to_model(presentation_exchange)

    @classmethod
    async def get_credentials_for_request(cls, controller: AcaPyClient, proof_id: str):
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id=proof_id)

        try:
            bound_logger.debug("Getting v1 matching credentials from proof id")
            result = await controller.present_proof_v1_0.get_matching_credentials(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            bound_logger.exception(
                "An unexpected error occurred while getting matching credentials."
            )
            raise CloudApiException("Failed to get credentials for request.") from e

        if result:
            bound_logger.debug("Successfully got matching v1 credentials.")
        else:
            bound_logger.debug("No matching v1 credentials obtained.")
        return result

    @classmethod
    async def get_proof_records(cls, controller: AcaPyClient):
        try:
            logger.debug("Fetching v1 present-proof exchange records")
            presentation_exchange = await controller.present_proof_v1_0.get_records()
            result = [
                record_to_model(rec) for rec in presentation_exchange.results or []
            ]
        except Exception as e:
            logger.exception("An unexpected error occurred while getting records.")
            raise CloudApiException("Failed to get proof records.") from e

        if result:
            logger.debug("Successfully got v1 present-proof records.")
        else:
            logger.info("No v1 present-proof records obtained.")
        return result

    @classmethod
    async def get_proof_record(cls, controller: AcaPyClient, proof_id: str):
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id)
        try:
            bound_logger.debug("Fetching single v1 present-proof exchange record")
            presentation_exchange = await controller.present_proof_v1_0.get_record(
                pres_ex_id=pres_ex_id
            )
            result = record_to_model(presentation_exchange)
        except Exception as e:
            bound_logger.exception("An unexpected error occurred while getting record.")
            raise CloudApiException("Failed to get proof record.") from e

        if result:
            bound_logger.debug("Successfully got v1 present-proof record.")
        else:
            bound_logger.info("No v1 present-proof record obtained.")
        return result

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str):
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id=proof_id)
        try:
            bound_logger.debug("Deleting v1 present-proof exchange record")
            await controller.present_proof_v1_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            bound_logger.exception(
                "An unexpected error occurred while deleting record."
            )
            raise CloudApiException("Failed to delete record.") from e

        bound_logger.debug("Successfully deleted v1 present-proof record.")

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
    ) -> PresentationExchange:
        bound_logger = logger.bind(body=proof_request)
        try:
            bound_logger.debug("Send free v1 presentation request")
            presentation_exchange = (
                await controller.present_proof_v1_0.send_request_free(
                    body=V10PresentationSendRequestRequest(
                        connection_id=proof_request.connection_id,
                        proof_request=proof_request.proof_request,
                    )
                )
            )
            result = record_to_model(presentation_exchange)
        except Exception as e:
            bound_logger.exception(
                "An unexpected error occurred while sending presentation request."
            )
            raise CloudApiException("Failed to send presentation request.") from e

        if result:
            bound_logger.debug("Successfully sent v1 presentation request.")
        else:
            bound_logger.warning("No result from sending v1 presentation request.")
        return result

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        bound_logger = logger.bind(body=proof_request)
        proof_id = pres_id_no_version(proof_id=proof_request.proof_id)
        try:
            bound_logger.debug("Send v1 proof presentation")
            presentation_record = await controller.present_proof_v1_0.send_presentation(
                pres_ex_id=proof_id, body=proof_request.presentation_spec
            )
            result = record_to_model(presentation_record)
        except Exception as e:
            bound_logger.exception(
                "An unexpected error occurred while sending a proof presentation."
            )
            raise CloudApiException("Failed to send proof presentation.") from e

        if result:
            bound_logger.debug("Successfully sent v1 proof presentation.")
        else:
            bound_logger.warning("No result from sending v1 proof presentation.")
        return result

    @classmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, proof_request: RejectProofRequest
    ) -> None:
        bound_logger = logger.bind(body=proof_request)
        bound_logger.info("Request to reject v1 presentation exchange record")
        proof_id = pres_id_no_version(proof_id=proof_request.proof_id)
        # Report problem if desired
        if proof_request.problem_report:
            try:
                bound_logger.debug("Submitting v1 problem report")
                await controller.present_proof_v1_0.report_problem(
                    pres_ex_id=proof_id,
                    body=V10PresentationProblemReportRequest(
                        description=proof_request.problem_report
                    ),
                )
            except Exception as e:
                bound_logger.exception(
                    "An unexpected error occurred while reporting problem."
                )
                raise CloudApiException("Failed to report problem.") from e

        try:
            bound_logger.debug("Deleting v1 presentation exchange record")
            await controller.present_proof_v1_0.delete_record(pres_ex_id=proof_id)
        except Exception as e:
            bound_logger.exception(
                "An unexpected error occurred while deleting record."
            )
            raise CloudApiException("Failed to delete record.") from e

        bound_logger.info("Successfully rejected v1 presentation exchange record.")
