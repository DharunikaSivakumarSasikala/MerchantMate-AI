from unittest.mock import patch

from app.assistant_service import (
    process_intent,
    process_message,
)
from app.models import AIIntent


def create_confirmation_state():
    """
    Create a complete invoice confirmation state without calling
    Ollama or PayPal.
    """
    intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email="sarah@example.com",
        amount=250.0,
        currency="AUD",
        description="photography",
        requires_confirmation=True,
    )

    result = process_intent(intent)

    assert result.status == "confirmation_required"

    return result.state


def test_successful_execution():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice",
            return_value="INV2-TEST-001",
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice",
            return_value=None,
        ) as mock_send,
    ):
        result = process_message(
            "confirm",
            state,
        )

    assert result.status == "confirmed"

    mock_create.assert_called_once()
    mock_send.assert_called_once_with(
        "INV2-TEST-001"
    )

    assert result.data == {
        "paypal_invoice_id": "INV2-TEST-001",
        "sent": True,
    }

    assert result.state.pending_invoice is None
    assert result.state.paypal_invoice_id is None


def test_cancel_does_not_execute():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice"
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice"
        ) as mock_send,
    ):
        result = process_message(
            "cancel",
            state,
        )

    assert result.status == "cancelled"

    mock_create.assert_not_called()
    mock_send.assert_not_called()


def test_ambiguous_confirmation_does_not_execute():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice"
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice"
        ) as mock_send,
    ):
        result = process_message(
            "maybe",
            state,
        )

    assert result.status == "confirmation_required"

    mock_create.assert_not_called()
    mock_send.assert_not_called()


def test_creation_failure():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice",
            side_effect=RuntimeError(
                "Mock PayPal create failure"
            ),
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice"
        ) as mock_send,
    ):
        result = process_message(
            "confirm",
            state,
        )

    assert result.status == "error"

    mock_create.assert_called_once()
    mock_send.assert_not_called()

    assert result.state.paypal_invoice_id is None
    assert result.state.awaiting_confirmation is True


def test_send_failure_preserves_invoice_id():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice",
            return_value="INV2-TEST-002",
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice",
            side_effect=RuntimeError(
                "Mock PayPal send failure"
            ),
        ) as mock_send,
    ):
        result = process_message(
            "confirm",
            state,
        )

    assert result.status == "error"

    mock_create.assert_called_once()
    mock_send.assert_called_once_with(
        "INV2-TEST-002"
    )

    assert (
        result.state.paypal_invoice_id
        == "INV2-TEST-002"
    )
    assert result.state.awaiting_confirmation is True


def test_retry_does_not_create_duplicate():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice",
            return_value="INV2-TEST-003",
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice",
            side_effect=RuntimeError(
                "First send failed"
            ),
        ) as mock_send,
    ):
        first_result = process_message(
            "confirm",
            state,
        )

    assert (
        first_result.state.paypal_invoice_id
        == "INV2-TEST-003"
    )

    mock_create.assert_called_once()
    mock_send.assert_called_once_with(
        "INV2-TEST-003"
    )

    with (
        patch(
            "app.assistant_service.create_invoice"
        ) as retry_create,
        patch(
            "app.assistant_service.send_invoice",
            return_value=None,
        ) as retry_send,
    ):
        second_result = process_message(
            "retry",
            first_result.state,
        )

    retry_create.assert_not_called()
    retry_send.assert_called_once_with(
        "INV2-TEST-003"
    )

    assert second_result.status == "confirmed"

    assert second_result.data == {
        "paypal_invoice_id": "INV2-TEST-003",
        "sent": True,
    }

    assert second_result.state.pending_invoice is None
    assert second_result.state.paypal_invoice_id is None
    assert (
        second_result.state.awaiting_confirmation
        is False
    )


def test_repeated_confirmation_after_success():
    state = create_confirmation_state()

    with (
        patch(
            "app.assistant_service.create_invoice",
            return_value="INV2-TEST-004",
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice",
            return_value=None,
        ) as mock_send,
    ):
        result = process_message(
            "confirm",
            state,
        )

    assert result.status == "confirmed"

    mock_create.assert_called_once()
    mock_send.assert_called_once_with(
        "INV2-TEST-004"
    )

    # A successful execution must remove all executable invoice
    # state so the same invoice cannot be executed again.
    assert result.state.pending_invoice is None
    assert result.state.awaiting_confirmation is False
    assert result.state.paypal_invoice_id is None