from abc import ABC, abstractmethod
from typing import Optional

from aries_cloudcontroller import AcaPyClient, IndyProofRequest
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec

from app.generic.proof.models import PresentationExchange


class Proof(ABC):
    """Abstract proof interface"""

    @classmethod
    @abstractmethod
    async def send_request_proof(
        cls,
        controller: AcaPyClient,
        proof_request: IndyProofRequest,
        comment: Optional[str] = None,
        trace: Optional[bool] = False,
    ) -> PresentationExchange:
        """
        Request proof from a connection ID.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: ProofRequest
            The proof request object
        connection_id: str
            The connection ID
        """

    @classmethod
    @abstractmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: IndyProofRequest,
        comment: Optional[str] = None,
        trace: Optional[bool] = False,
    ) -> PresentationExchange:
        """
        Create proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: V10PresentationCreateRequestRequest
            The proof request object
        """

    @classmethod
    @abstractmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, pres_ex_id: str, body: Optional[IndyPresSpec]
    ) -> PresentationExchange:
        """ "
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        pres_ex_id: str
            The presentation exchange ID
        """

    @classmethod
    @abstractmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        problem_report: Optional[str] = None,
    ) -> None:
        """ "
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        pres_ex_id: str
            The presentation exchange ID
        """
