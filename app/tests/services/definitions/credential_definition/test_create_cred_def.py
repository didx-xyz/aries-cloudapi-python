from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aries_cloudcontroller import AcaPyClient, CredentialDefinitionSendRequest

from app.models.definitions import CreateCredentialDefinition
from app.services.definitions.credential_definitions import create_credential_definition


@pytest.mark.anyio
async def test_create_credential_definition_success():
    mock_aries_controller = AsyncMock(spec=AcaPyClient)
    mock_publisher = AsyncMock()
    mock_publisher.publish_credential_definition.return_value = MagicMock(
        sent=MagicMock(credential_definition_id="test_cred_def_id"), txn=None
    )

    create_cred_def_payload = CreateCredentialDefinition(
        schema_id="test_schema_id", tag="test_tag", support_revocation=False
    )

    with patch(
        "app.services.definitions.credential_definitions.CredentialDefinitionPublisher",
        return_value=mock_publisher,
    ), patch(
        "app.services.definitions.credential_definitions.assert_public_did",
        return_value="test_public_did",
    ), patch(
        "app.services.definitions.credential_definitions.assert_valid_issuer"
    ), patch(
        "app.services.definitions.credential_definitions.handle_model_with_validation"
    ) as mock_handle_model:

        mock_handle_model.return_value = CredentialDefinitionSendRequest(
            schema_id="CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3.0",
            support_revocation=False,
            tag="test_tag",
        )

        result = await create_credential_definition(
            mock_aries_controller, create_cred_def_payload, False
        )

        assert result == "test_cred_def_id"
        mock_publisher.publish_credential_definition.assert_called_once()
        mock_handle_model.assert_called_once()


@pytest.mark.anyio
async def test_create_credential_definition_with_revocation():
    mock_aries_controller = AsyncMock(spec=AcaPyClient)
    mock_publisher = AsyncMock()
    mock_publisher.publish_credential_definition.return_value = MagicMock(
        sent=MagicMock(credential_definition_id="test_cred_def_id"),
        txn=MagicMock(transaction_id="test_txn_id"),
    )

    create_cred_def_payload = CreateCredentialDefinition(
        schema_id="test_schema_id", tag="test_tag", support_revocation=True
    )

    with patch(
        "app.services.definitions.credential_definitions.CredentialDefinitionPublisher",
        return_value=mock_publisher,
    ), patch(
        "app.services.definitions.credential_definitions.assert_public_did",
        return_value="test_public_did",
    ), patch(
        "app.services.definitions.credential_definitions.assert_valid_issuer"
    ), patch(
        "app.services.definitions.credential_definitions.handle_model_with_validation"
    ), patch(
        "app.services.definitions.credential_definitions.wait_for_transaction_ack"
    ), patch(
        "app.services.definitions.credential_definitions.CredentialDefinitionSendRequest"
    ):

        result = await create_credential_definition(
            mock_aries_controller, create_cred_def_payload, True
        )

        assert result == "test_cred_def_id"
        mock_publisher.check_endorser_connection.assert_called_once()
        mock_publisher.publish_credential_definition.assert_called_once()
        mock_publisher.wait_for_revocation_registry.assert_called_once_with(
            "test_cred_def_id"
        )


@pytest.mark.anyio
async def test_create_credential_definition_invalid_issuer():
    mock_aries_controller = AsyncMock(spec=AcaPyClient)
    create_cred_def_payload = CreateCredentialDefinition(
        schema_id="test_schema_id", tag="test_tag", support_revocation=False
    )

    with patch(
        "app.services.definitions.credential_definitions.assert_public_did",
        return_value="test_public_did",
    ), patch(
        "app.services.definitions.credential_definitions.assert_valid_issuer",
        side_effect=Exception("Invalid issuer"),
    ):

        with pytest.raises(Exception) as exc_info:
            await create_credential_definition(
                mock_aries_controller, create_cred_def_payload, False
            )

        assert str(exc_info.value) == "Invalid issuer"