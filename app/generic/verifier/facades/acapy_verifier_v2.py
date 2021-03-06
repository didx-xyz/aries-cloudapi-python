from typing import Optional
import logging

from aries_cloudcontroller import (
    AcaPyClient,
    V20PresCreateRequestRequest,
    V20PresProblemReportRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)
from fastapi.exceptions import HTTPException

from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared_models import (
    PresentationExchange,
    presentation_record_to_model as record_to_model,
    pres_id_no_version,
)

logger = logging.getLogger(__name__)


class VerifierV2(Verifier):
    @classmethod
    async def get_proof_records(cls, controller: AcaPyClient):
        try:
            presentation_exchange = await controller.present_proof_v2_0.get_records()
            return [record_to_model(rec) for rec in presentation_exchange.results or []]
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def get_proof_record(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = pres_id_no_version(proof_id)
            presentation_exchange = await controller.present_proof_v2_0.get_record(
                pres_ex_id=pres_ex_id
            )
            return record_to_model(presentation_exchange)
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def get_credentials_for_request(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = pres_id_no_version(proof_id=proof_id)
            return await controller.present_proof_v2_0.get_matching_credentials(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = pres_id_no_version(proof_id=proof_id)
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
        comment: Optional[str] = None,
    ) -> PresentationExchange:
        proof_record = await controller.present_proof_v2_0.create_proof_request(
            body=V20PresCreateRequestRequest(
                presentation_request=V20PresRequestByFormat(
                    indy=proof_request.proof_request
                ),
                comment=comment,
                trace=False,
            )
        )
        return record_to_model(proof_record)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
    ) -> PresentationExchange:
        presentation_exchange = await controller.present_proof_v2_0.send_request_free(
            body=V20PresSendRequestRequest(
                connection_id=proof_request.connection_id,
                presentation_request=V20PresRequestByFormat(
                    dif=None, indy=proof_request.proof_request
                ),
            )
        )
        return record_to_model(presentation_exchange)

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        pres_ex_id = pres_id_no_version(proof_id=proof_request.proof_id)
        presentation_record = await controller.present_proof_v2_0.send_presentation(
            pres_ex_id=pres_ex_id,
            body=V20PresSpecByFormatRequest(indy=proof_request.presentation_spec),
        )
        return record_to_model(presentation_record)

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
                raise e from e

        try:
            # delete exchange record
            await controller.present_proof_v2_0.delete_record(pres_ex_id=pres_ex_id)
        except:
            raise HTTPException(status_code=500, detail="Failed to delete record")
