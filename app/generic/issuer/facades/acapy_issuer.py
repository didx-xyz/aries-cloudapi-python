from abc import ABC, abstractmethod
from typing import List, Optional

from aries_cloudcontroller import AcaPyClient

from app.generic.issuer.models import Credential, CredentialNoConnection
from shared.models.topics import CredentialExchange


class Issuer(ABC):
    """Abstract issuer interface."""

    @classmethod
    @abstractmethod
    async def send_credential(
        cls, controller: AcaPyClient, credential: Credential
    ) -> CredentialExchange:
        """
        Create and send indy credential using Issue Credential protocol. Automating the entire flow.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential: Credential
            Credential to issue

        Returns:
        --------
        cred_ex_record:
            The credential record
        """

    @classmethod
    @abstractmethod
    async def create_offer(
        cls, controller: AcaPyClient, credential: CredentialNoConnection
    ) -> CredentialExchange:
        """
        Create a credential offer not bound to a connection.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential: CredentialNoConnection
            Credential offer to create

        Returns:
        --------
        cred_ex_record:
            The credential record
        """

    @classmethod
    @abstractmethod
    async def request_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ) -> CredentialExchange:
        """
        Request credential

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential_exchange_id:
            The credential_exchange_id of the exchange

        Returns:
        --------
        cred_ex_record:
            The credential record
        """

    @classmethod
    @abstractmethod
    async def store_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ) -> CredentialExchange:
        """
        Store credential

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential_exchange_id:
            The credential_exchange_id of the exchange

        Returns:
        --------
        cred_ex_record:
            The credential record
        """

    @classmethod
    @abstractmethod
    async def delete_credential(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ):
        """Delete credential record.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential_exchange_id:
            The credential_exchange_id of the exchange
        """

    @classmethod
    @abstractmethod
    async def get_records(
        cls, controller: AcaPyClient, connection_id: Optional[str] = None
    ) -> List[CredentialExchange]:
        """Get list of credential records.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        connection_id:
            Filter credential record by connection id
        """

    @classmethod
    @abstractmethod
    async def get_record(
        cls, controller: AcaPyClient, credential_exchange_id: str
    ) -> CredentialExchange:
        """Get credential record.

        Parameters:
        -----------
        controller: AcaPyClient
            The aries_cloudcontroller object
        credential_exchange_id:
            The credential_exchange_id of the exchange
        """
