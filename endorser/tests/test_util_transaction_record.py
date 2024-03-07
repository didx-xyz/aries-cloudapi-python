import json
from unittest.mock import MagicMock, Mock

import pytest
from aries_cloudcontroller import TransactionRecord

from endorser.util.transaction_record import (
    get_did_and_schema_id_from_cred_def_attachment,
    get_endorsement_request_attachment,
    is_credential_definition_transaction,
)


def test_get_endorsement_request_attachment_with_valid_attachment():
    transaction_record_with_attachment = TransactionRecord(
        messages_attach=[
            {
                "data": {
                    "json": json.dumps(
                        {
                            "identifier": "identifier_value",
                            "operation": {"type": "102", "ref": "ref_value"},
                        }
                    )
                }
            }
        ]
    )
    attachment = get_endorsement_request_attachment(transaction_record_with_attachment)
    assert attachment == {
        "identifier": "identifier_value",
        "operation": {"type": "102", "ref": "ref_value"},
    }


def test_get_endorsement_request_attachment_without_attachment():
    transaction_record_without_attachment = TransactionRecord(messages_attach=[])
    attachment = get_endorsement_request_attachment(
        transaction_record_without_attachment
    )
    assert attachment is None

    transaction_record_data_key = TransactionRecord(
        messages_attach=[{"not_the_expected_data_key": "abc"}]
    )
    attachment = get_endorsement_request_attachment(transaction_record_data_key)
    assert attachment is None

    transaction_record_without_json_key = TransactionRecord(
        messages_attach=[{"data": {"not_the_expected_json_key": "abc"}}]
    )
    attachment = get_endorsement_request_attachment(transaction_record_without_json_key)
    assert attachment is None


def test_get_endorsement_request_attachment_invalid_json():
    transaction_record_without_valid_json = TransactionRecord(
        messages_attach=[{"data": {"json": "invalid_json"}}]
    )
    attachment = get_endorsement_request_attachment(
        transaction_record_without_valid_json
    )
    assert attachment is None


def test_get_endorsement_request_attachment_exception():
    # Mock a TransactionRecord that raises an Exception when messages_attach is accessed
    transaction_record_exception = MagicMock()
    transaction_record_exception.messages_attach = Mock(
        side_effect=KeyError("Key error exception")
    )

    attachment = get_endorsement_request_attachment(transaction_record_exception)
    assert attachment is None

    transaction_record_exception = MagicMock()
    transaction_record_exception.messages_attach = Mock(
        side_effect=Exception("Test exception")
    )

    attachment = get_endorsement_request_attachment(transaction_record_exception)
    assert attachment is None


def test_is_credential_definition_transaction_true():
    attachment = {"operation": {"type": "102"}}
    assert is_credential_definition_transaction(attachment) is True


def test_is_credential_definition_transaction_false():
    attachment = {"operation": {"type": "100"}}
    assert is_credential_definition_transaction(attachment) is False


def test_is_credential_definition_transaction_no_operation():
    attachment = {"bad_key": {"type": "102"}}
    assert is_credential_definition_transaction(attachment) is False


def test_is_credential_definition_transaction_no_type():
    attachment = {"operation": {"bad_key": "102"}}
    assert is_credential_definition_transaction(attachment) is False


def test_is_credential_definition_transaction_exception():
    attachment = MagicMock(side_effect=KeyError("Exception"))

    assert is_credential_definition_transaction(attachment) is False


@pytest.mark.anyio
async def test_get_did_and_schema_id_from_cred_def_attachment(mock_acapy_client):
    mock_acapy_client.schema.get_schema.return_value = MagicMock(
        var_schema=MagicMock(id="schema_id")
    )

    did, schema_id = await get_did_and_schema_id_from_cred_def_attachment(
        mock_acapy_client,
        {"identifier": "identifier_value", "operation": {"ref": "ref_value"}},
    )

    assert did == "did:sov:identifier_value"
    assert schema_id == "schema_id"
    mock_acapy_client.schema.get_schema.assert_awaited_once_with(schema_id="ref_value")
