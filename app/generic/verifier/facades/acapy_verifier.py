from abc import ABC, abstractmethod

from aries_cloudcontroller import AcaPyClient

from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    PresentationExchange,
    RejectProofRequest,
    SendProofRequest,
)


class Verifier(ABC):
    """Abstract proof interface"""

    @classmethod
    @abstractmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: SendProofRequest,
    ) -> PresentationExchange:
        """
        Request proof from a connection ID.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: SendProofRequest
            The proof request object

        Returns:
        --------
        exchange_record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: CreateProofRequest,
    ) -> PresentationExchange:
        """
        Create proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: CreateProofRequest
            The proof request object

        Returns:
        --------
        exchange_record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def accept_proof_request(
        cls, controller: AcaPyClient, proof_request: AcceptProofRequest
    ) -> PresentationExchange:
        """
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: AcceptProofRequet
            The proof request object

        Returns:
        --------
        exchange_record: PresentationExchange
            The proof exchange record
        """

    @classmethod
    @abstractmethod
    async def reject_proof_request(
        cls, controller: AcaPyClient, proof_request: RejectProofRequest
    ) -> None:
        """
        Accept proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: AcceptProofRequet
            The proof request object

        Returns:
        --------
        None
            Returns None on successful record deletion.
        """
