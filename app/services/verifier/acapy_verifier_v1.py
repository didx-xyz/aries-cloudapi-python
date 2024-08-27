from typing import List, Optional

from aries_cloudcontroller import (
    AcaPyClient,
    IndyCredPrecis,
    V10PresentationCreateRequestRequest,
    V10PresentationProblemReportRequest,
    V10PresentationSendRequest,
    V10PresentationSendRequestRequest,
)

from app.exceptions import CloudApiException, handle_acapy_call
from app.models.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    ProofRequestType,
    RejectProofRequest,
    SendProofRequest,
)
from app.services.verifier.acapy_verifier import Verifier
from shared.log_config import get_logger
from shared.models.presentation_exchange import PresentationExchange
from shared.models.presentation_exchange import (
    presentation_record_to_model as record_to_model,
)
from shared.models.protocol import pres_id_no_version

logger = get_logger(__name__)


class VerifierV1(Verifier):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        create_proof_request: CreateProofRequest,
    ) -> PresentationExchange:
        if create_proof_request.type != ProofRequestType.INDY:
            raise CloudApiException(
                f"Only Indy credential types are supported in v1. Requested type: {create_proof_request.type}",
                status_code=400,
            )

        bound_logger = logger.bind(body=create_proof_request)
        bound_logger.debug("Creating v1 proof request")

        request_body = V10PresentationCreateRequestRequest(
            auto_remove=not create_proof_request.save_exchange_record,
            proof_request=create_proof_request.indy_proof_request,
            auto_verify=True,
            comment=create_proof_request.comment,
        )

        try:
            presentation_exchange = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.create_proof_request,
                body=request_body,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to create presentation request: {e.detail}", e.status_code
            ) from e

        result = record_to_model(presentation_exchange)
        bound_logger.debug("Successfully created v1 presentation request.")
        return result

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        send_proof_request: SendProofRequest,
    ) -> PresentationExchange:
        if send_proof_request.type != ProofRequestType.INDY:
            raise CloudApiException(
                f"Only Indy credential types are supported in v1. Requested type: {send_proof_request.type}",
                status_code=400,
            )

        bound_logger = logger.bind(body=send_proof_request)
        request_body = V10PresentationSendRequestRequest(
            auto_remove=not send_proof_request.save_exchange_record,
            connection_id=send_proof_request.connection_id,
            proof_request=send_proof_request.indy_proof_request,
            auto_verify=True,
            comment=send_proof_request.comment,
        )

        try:
            bound_logger.debug("Send free v1 presentation request")
            presentation_exchange = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.send_request_free,
                body=request_body,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to send presentation request: {e.detail}", e.status_code
            ) from e

        result = record_to_model(presentation_exchange)
        bound_logger.debug("Successfully created v1 presentation request.")
        return result

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, accept_proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        if accept_proof_request.type != ProofRequestType.INDY:
            raise CloudApiException(
                f"Only Indy credential types are supported in v1. Requested type: {accept_proof_request.type}",
                status_code=400,
            )

        bound_logger = logger.bind(body=accept_proof_request)
        proof_id = pres_id_no_version(proof_id=accept_proof_request.proof_id)

        bound_logger.debug("Send v1 proof presentation")
        indy_pres_spec = accept_proof_request.indy_presentation_spec
        v10_pres_send_req = V10PresentationSendRequest(
            auto_remove=not accept_proof_request.save_exchange_record,
            requested_attributes=indy_pres_spec.requested_attributes,
            requested_predicates=indy_pres_spec.requested_predicates,
            self_attested_attributes=indy_pres_spec.self_attested_attributes,
        )

        try:
            presentation_exchange = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.send_presentation,
                pres_ex_id=proof_id,
                body=v10_pres_send_req,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to send proof presentation: {e.detail}", e.status_code
            ) from e

        result = record_to_model(presentation_exchange)
        bound_logger.debug("Successfully created v1 presentation request.")
        return result

    @classmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, reject_proof_request: RejectProofRequest
    ) -> None:
        bound_logger = logger.bind(body=reject_proof_request)
        bound_logger.debug("Request to reject v1 presentation exchange record")
        proof_id = pres_id_no_version(proof_id=reject_proof_request.proof_id)

        request_body = V10PresentationProblemReportRequest(
            description=reject_proof_request.problem_report
        )

        try:
            bound_logger.debug("Submitting v1 problem report")
            await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.report_problem,
                pres_ex_id=proof_id,
                body=request_body,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to send problem report: {e.detail}", e.status_code
            ) from e

        if reject_proof_request.delete_proof_record:
            try:
                bound_logger.debug("Deleting v1 presentation exchange record")
                await handle_acapy_call(
                    logger=bound_logger,
                    acapy_call=controller.present_proof_v1_0.delete_record,
                    pres_ex_id=proof_id,
                )
            except CloudApiException as e:
                raise CloudApiException(
                    f"Failed to delete record: {e.detail}", e.status_code
                ) from e

        bound_logger.debug("Successfully rejected v1 presentation exchange record.")

    @classmethod
    async def get_proof_records(
        cls,
        controller: AcaPyClient,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        connection_id: str = None,
        role: str = None,
        state: str = None,
        thread_id: str = None,
    ) -> List[PresentationExchange]:
        try:
            logger.debug("Fetching v1 present-proof exchange records")
            presentation_exchange = await handle_acapy_call(
                logger=logger,
                acapy_call=controller.present_proof_v1_0.get_records,
                limit=limit,
                offset=offset,
                connection_id=connection_id,
                role=role,
                state=state,
                thread_id=thread_id,
            )
        except CloudApiException as e:
            logger.exception("An exception occurred while getting records.")
            raise CloudApiException(
                f"Failed to get proof records: {e.detail}", e.status_code
            ) from e

        result = [record_to_model(rec) for rec in presentation_exchange.results or []]
        logger.debug("Successfully got v1 present-proof records.")
        return result

    @classmethod
    async def get_proof_record(
        cls, controller: AcaPyClient, proof_id: str
    ) -> PresentationExchange:
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id)

        bound_logger.debug("Fetching single v1 present-proof exchange record")
        try:
            presentation_exchange = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.get_record,
                pres_ex_id=pres_ex_id,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to get proof record with proof id `{proof_id}`: {e.detail}",
                e.status_code,
            ) from e

        result = record_to_model(presentation_exchange)
        bound_logger.debug("Successfully created v1 presentation request.")
        return result

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str) -> None:
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id=proof_id)

        try:
            bound_logger.debug("Deleting v1 present-proof exchange record")
            await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.delete_record,
                pres_ex_id=pres_ex_id,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to delete record with proof id `{proof_id}`: {e.detail}",
                e.status_code,
            ) from e

        bound_logger.debug("Successfully deleted v1 present-proof record.")

    @classmethod
    async def get_credentials_by_proof_id(
        cls,
        controller: AcaPyClient,
        proof_id: str,
        referent: Optional[str] = None,
        count: Optional[str] = None,
        start: Optional[str] = None,
    ) -> List[IndyCredPrecis]:
        bound_logger = logger.bind(body={"proof_id": proof_id})
        pres_ex_id = pres_id_no_version(proof_id=proof_id)

        try:
            bound_logger.debug("Getting v1 matching credentials from proof id")
            result = await handle_acapy_call(
                logger=bound_logger,
                acapy_call=controller.present_proof_v1_0.get_matching_credentials,
                pres_ex_id=pres_ex_id,
                referent=referent,
                count=count,
                start=start,
            )
        except CloudApiException as e:
            raise CloudApiException(
                f"Failed to get credentials with proof id `{proof_id}`: {e.detail}",
                e.status_code,
            ) from e

        if result:
            bound_logger.debug("Successfully got matching v1 credentials.")
        else:
            bound_logger.debug("No matching v1 credentials obtained.")
        return result
