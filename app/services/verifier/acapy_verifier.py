from abc import ABC, abstractmethod
from typing import List

from aries_cloudcontroller import AcaPyClient, IndyCredPrecis

from app.models.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from shared.models.topics import PresentationExchange


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
        proof_request: AcceptProofRequest
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
        Reject proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_request: RejectProofRequest
            The proof request object

        Returns:
        --------
        None
            Returns None on successful request rejection.
        """

    @classmethod
    @abstractmethod
    async def delete_proof(cls, controller: AcaPyClient, proof_id: str) -> None:
        """
        Delete proof request

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_id: str
            The proof record exchange id

        Returns:
        --------
        None
            Returns None on successful record deletion.
        """

    @classmethod
    @abstractmethod
    async def get_proof_records(
        cls, controller: AcaPyClient
    ) -> List[PresentationExchange]:
        """
        Get all proof records

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object

        Returns:
        --------
        [PresentationExchange]
            A list of presentation exchange records
        """

    @classmethod
    @abstractmethod
    async def get_proof_record(
        cls, controller: AcaPyClient, proof_id: str
    ) -> PresentationExchange:
        """
        Get a specific proof record

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        proof_id: str
            The presentation exchange ID

        Returns:
        --------
        PresentationExchange
            A presentation exchange records
        """

    @classmethod
    @abstractmethod
    async def get_credentials_for_request(
        cls, controller: AcaPyClient, proof_id: str
    ) -> List[IndyCredPrecis]:
        """
        Retrieve the credentials for a proof

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
         proof_id: str
            The proof id

        Returns:
        --------
        [IndyCredPrecis]
            A list of presentation exchange records
        """
