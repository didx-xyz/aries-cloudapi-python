from unittest.mock import MagicMock, patch

import pytest

from shared.constants import GOVERNANCE_LABEL
from webhooks.util.billing import is_applicable_for_billing


@patch("webhooks.util.billing.LAGO_API_KEY", "")
@patch("webhooks.util.billing.LAGO_URL", "")
def test_lago_not_configured():
    wallet_id = "wallet_id"
    group_id = "group_id"
    topic = "topic"
    payload = {}
    logger = MagicMock()
    assert is_applicable_for_billing(wallet_id, group_id, topic, payload, logger) == (
        False,
        None,
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
def test_is_governance_label():
    wallet_id = GOVERNANCE_LABEL
    group_id = "group_id"
    topic = "topic"
    payload = {}
    logger = MagicMock()
    assert is_applicable_for_billing(wallet_id, group_id, topic, payload, logger) == (
        False,
        None,
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
def test_missing_group_id():
    wallet_id = "wallet_id"
    group_id = ""
    topic = "topic"
    payload = {}
    logger = MagicMock()
    assert is_applicable_for_billing(wallet_id, group_id, topic, payload, logger) == (
        False,
        None,
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
def test_not_applicable_topic():
    wallet_id = "wallet_id"
    group_id = "group_id"
    topic = "not_applicable_topic"
    payload = {}
    logger = MagicMock()
    assert is_applicable_for_billing(wallet_id, group_id, topic, payload, logger) == (
        False,
        None,
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
def test_not_applicable_state():
    wallet_id = "wallet_id"
    group_id = "group_id"
    topic = "proofs"
    payload = {"state": "not_applicable_state"}
    logger = MagicMock()
    assert is_applicable_for_billing(wallet_id, group_id, topic, payload, logger) == (
        False,
        None,
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
@pytest.mark.parametrize(
    "wallet_id, group_id, topic, payload, expected",
    [
        (
            "wallet_id",
            "group_id",
            "proofs",
            {"role": "verifier", "state": "done"},
            (True, None),
        ),
        (
            "wallet_id",
            "group_id",
            "proofs",
            {"role": "verifier", "state": "presentation_acked"},
            (True, None),
        ),
        (
            "wallet_id",
            "group_id",
            "proofs",
            {"role": "verifier", "state": "verified"},
            (True, None),
        ),
        (
            "wallet_id",
            "group_id",
            "proofs",
            {"role": "not_applicable_role", "state": "done"},
            (False, None),
        ),
    ],
)
def test_applicable_proof(wallet_id, group_id, topic, payload, expected):
    logger = MagicMock()
    assert (
        is_applicable_for_billing(wallet_id, group_id, topic, payload, logger)
        == expected
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
@pytest.mark.parametrize(
    "wallet_id, group_id, topic, payload, operation_type, expected",
    [
        (
            "wallet_id",
            "group_id",
            "endorsements",
            {"state": "transaction_acked"},
            "100",
            (True, "100"),
        ),
        (
            "wallet_id",
            "group_id",
            "endorsements",
            {"state": "transaction_acked"},
            "102",
            (True, "102"),
        ),
        (
            "wallet_id",
            "group_id",
            "endorsements",
            {"state": "transaction_acked"},
            "113",
            (True, "113"),
        ),
        (
            "wallet_id",
            "group_id",
            "endorsements",
            {"state": "transaction_acked"},
            "114",
            (True, "114"),
        ),
        (
            "wallet_id",
            "group_id",
            "endorsements",
            {"state": "transaction_acked"},
            "not_applicable_operation_type",
            (False, None),
        ),
    ],
)
def test_applicable_endorsement_operation_type(
    wallet_id, group_id, topic, payload, operation_type, expected
):
    logger = MagicMock()
    with patch("webhooks.util.billing.get_operation_type") as mock_get_operation_type:
        mock_get_operation_type.return_value = operation_type
        assert (
            is_applicable_for_billing(wallet_id, group_id, topic, payload, logger)
            == expected
        )
        mock_get_operation_type.assert_called_once_with(payload=payload, logger=logger)


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
@pytest.mark.parametrize(
    "wallet_id, group_id, topic, payload, expected",
    [
        ("wallet_id", "group_id", "credentials", {"state": "done"}, (True, None)),
        (
            "wallet_id",
            "group_id",
            "credentials",
            {"state": "credential_acked"},
            (True, None),
        ),
        (
            "wallet_id",
            "group_id",
            "credentials",
            {"state": "not_applicable_state"},
            (False, None),
        ),
    ],
)
def test_credentials_state(wallet_id, group_id, topic, payload, expected):
    logger = MagicMock()
    assert (
        is_applicable_for_billing(wallet_id, group_id, topic, payload, logger)
        == expected
    )


@patch("webhooks.util.billing.LAGO_API_KEY", "NOT_EMPTY")
@patch("webhooks.util.billing.LAGO_URL", "NOT_EMPTY")
@pytest.mark.parametrize(
    "wallet_id, group_id, topic, payload, expected",
    [
        (
            "wallet_id",
            "group_id",
            "issuer_cred_rev",
            {"state": "revoked"},
            (True, None),
        ),
        (
            "wallet_id",
            "group_id",
            "issuer_cred_rev",
            {"state": "not_applicable_state"},
            (False, None),
        ),
    ],
)
def test_issuer_cred_rev(wallet_id, group_id, topic, payload, expected):
    logger = MagicMock()
    assert (
        is_applicable_for_billing(wallet_id, group_id, topic, payload, logger)
        == expected
    )
