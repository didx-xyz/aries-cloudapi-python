from abc import ABC, abstractmethod
from typing import Any, Optional

from aries_cloudcontroller import AcaPyClient, IndyProofRequest

from app.generic.proof.models import Presentation


class Proof(ABC):
    """Abstract proof interface"""

    @classmethod
    @abstractmethod
    async def request_proof(
        cls,
        controller: AcaPyClient,
        proof_request: Any = None,
        connection_id: str = None,
    ) -> Presentation:
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
        proof_request: Optional[IndyProofRequest] = None,
    ) -> Presentation:
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
        cls, controller: AcaPyClient, pres_ex_id: str
    ) -> Presentation:
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
    async def decline_proof_request(
        cls, controller: AcaPyClient, pres_ex_id: str
    ) -> Presentation:
        """ "
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        pres_ex_id: str
            The presentation exchange ID
        """
