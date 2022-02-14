import logging
from typing import Dict

from aries_cloudcontroller import (
    AcaPyClient,
    V10PresentationCreateRequestRequest,
    V10PresentationProblemReportRequest,
    V10PresentationSendRequestRequest,
)
from aries_cloudcontroller.model.indy_proof_request import IndyProofRequest
from aries_cloudcontroller.model.v10_presentation_exchange import (
    V10PresentationExchange,
)
from fastapi.exceptions import HTTPException
from pydantic.typing import NoneType

import app.generic.verifier.facades.acapy_verifier_utils as utils
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared_models import PresentationExchange

logger = logging.getLogger(__name__)


class VerifierV1(Verifier):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
    ) -> PresentationExchange:
        presentation_exchange = (
            await controller.present_proof_v1_0.create_proof_request(
                body=V10PresentationCreateRequestRequest(
                    proof_request=proof_request.proof_request,
                    comment=proof_request.comment,
                    trace=False,
                )
            )
        )
        return utils.record_to_model(presentation_exchange)

    @classmethod
    async def get_credentials_for_request(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = utils.pres_id_no_version(proof_id=proof_id)
            return await controller.present_proof_v1_0.get_matching_credentials(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def get_proof_records(cls, controller: AcaPyClient):
        try:
            presentation_exchange = await controller.present_proof_v1_0.get_records()
            return [utils.record_to_model(rec) for rec in presentation_exchange.results]
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def get_proof_record(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = utils.pres_id_no_version(proof_id)
            presentation_exchange = await controller.present_proof_v1_0.get_record(
                pres_ex_id=pres_ex_id
            )
            return utils.record_to_model(presentation_exchange)
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str):
        try:
            pres_ex_id = utils.pres_id_no_version(proof_id=proof_id)
            return await controller.present_proof_v1_0.delete_record(
                pres_ex_id=pres_ex_id
            )
        except Exception as e:
            logger.error(f"{e!r}")
            raise e from e

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
        free: bool = True,
    ) -> PresentationExchange:
        try:
            # This "free" is de facto the only one we support right now
            if free and isinstance(proof_request.proof_request, IndyProofRequest):
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_request_free(
                        body=V10PresentationSendRequestRequest(
                            connection_id=proof_request.connection_id,
                            proof_request=proof_request.proof_request,
                        )
                    )
                )
            else:
                raise NotImplementedError
            return utils.record_to_model(presentation_exchange)
        except (AttributeError, TypeError) as e:
            raise NotImplementedError(f"{e!r}")
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        proof_id = utils.pres_id_no_version(proof_id=proof_request.proof_id)
        presentation_record = await controller.present_proof_v1_0.send_presentation(
            pres_ex_id=proof_id, body=proof_request.presentation_spec
        )
        return utils.record_to_model(presentation_record)

    @classmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, proof_request: RejectProofRequest
    ) -> None:
        # get the record
        proof_id = utils.pres_id_no_version(proof_id=proof_request.proof_id)
        proof_request_res = await controller.present_proof_v1_0.get_record(
            pres_ex_id=proof_id
        )
        # Report problem if desired
        if proof_request.problem_report:
            try:
                await controller.present_proof_v1_0.report_problem(
                    pres_ex_id=proof_id,
                    body=V10PresentationProblemReportRequest(
                        description=proof_request.problem_report
                    ),
                )
            except Exception as e:
                raise e from e
        # delete exchange record
        delete_proof_request_res = await controller.present_proof_v1_0.delete_record(
            pres_ex_id=proof_id
        )
        if not isinstance(proof_request_res, V10PresentationExchange) or not isinstance(
            delete_proof_request_res, (Dict, NoneType)
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")
