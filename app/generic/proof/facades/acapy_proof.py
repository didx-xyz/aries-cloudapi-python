from abc import ABC, abstractmethod
from typing import Optional

from aries_cloudcontroller import AcaPyClient, IndyProofRequest
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec

from app.generic.proof.models import PresentationExchange


class Proof(ABC):
    """Abstract proof interface"""

    @classmethod
    @abstractmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: IndyProofRequest,
        comment: Optional[str] = None,
    ) -> PresentationExchange:
        """
        Request proof from a connection ID.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: ProofRequest
            The proof request object
        comment: Optional[str]
            A human-readable comment

        Returns:
        --------
        Exchange record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: IndyProofRequest,
        comment: Optional[str] = None,
    ) -> PresentationExchange:
        """
        Create proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: V10PresentationCreateRequestRequest
            The proof request object
        comment: Optional[str]
            A human-readable comment

        Returns:
        --------
        Exchange record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_id: str, body: Optional[IndyPresSpec]
    ) -> PresentationExchange:
        """
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        pres_ex_id: str
            The presentation exchange ID
        body: IndyPresSpec
            The Indy presenatation specification

        Returns:
        --------
        Exchange record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        problem_report: Optional[str] = None,
    ) -> None:
        """
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        pres_ex_id: str
            The presentation exchange ID
        problem_report: Optional[str]
            The optional problem report

        Returns:
        --------
        None
            Returns None on successful record deletion.
        """
