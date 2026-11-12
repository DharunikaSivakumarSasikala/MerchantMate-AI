from unittest.mock import patch

from app.assistant_service import process_message
from app.models import AIIntent


def test_missing_email_flow():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email=None,
        amount=250,
        currency="AUD",
        description="photography",
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            "Invoice Sarah $250 for photography."
        )

    assert result1.status == "needs_information"
    assert result1.state.requested_field == "customer_email"
    assert result1.state.pending_invoice is not None
    assert result1.state.pending_invoice.customer_name == "Sarah"
    assert result1.state.pending_invoice.amount == 250
    assert result1.state.pending_invoice.currency == "AUD"
    assert result1.state.pending_invoice.description == "photography"
    assert not result1.state.awaiting_confirmation

    result2 = process_message(
        "sarah@example.com",
        result1.state,
    )

    assert result2.status == "confirmation_required"
    assert result2.state.awaiting_confirmation
    assert result2.invoice_draft is not None
    assert result2.invoice_draft.customer_name == "Sarah"
    assert result2.invoice_draft.customer_email == "sarah@example.com"
    assert result2.invoice_draft.amount == 250
    assert result2.invoice_draft.currency == "AUD"
    assert result2.invoice_draft.description == "photography"

    with (
        patch(
            "app.assistant_service.create_invoice",
            return_value="INV2-MOCK-CONVERSATION",
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice",
            return_value=None,
        ) as mock_send,
    ):
        result3 = process_message(
            "confirm",
            result2.state,
        )

    assert result3.status == "confirmed"

    mock_create.assert_called_once()
    mock_send.assert_called_once_with(
        "INV2-MOCK-CONVERSATION"
    )

    assert result3.data == {
        "paypal_invoice_id": "INV2-MOCK-CONVERSATION",
        "sent": True,
    }

    assert result3.state.pending_invoice is None
    assert not result3.state.awaiting_confirmation


def test_multiple_missing_fields():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email=None,
        amount=None,
        currency="AUD",
        description=None,
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            "Create an invoice for Sarah."
        )

    assert result1.status == "needs_information"
    assert result1.state.requested_field == "customer_email"
    assert result1.state.pending_invoice is not None
    assert result1.state.pending_invoice.customer_name == "Sarah"

    result2 = process_message(
        "sarah@example.com",
        result1.state,
    )

    assert result2.status == "needs_information"
    assert result2.state.requested_field == "amount"
    assert result2.state.pending_invoice is not None
    assert result2.state.pending_invoice.customer_email == "sarah@example.com"

    result3 = process_message(
        "350 AUD",
        result2.state,
    )

    assert result3.status == "needs_information"
    assert result3.state.requested_field == "description"
    assert result3.state.pending_invoice is not None
    assert result3.state.pending_invoice.amount == 350
    assert result3.state.pending_invoice.currency == "AUD"

    result4 = process_message(
        "logo design",
        result3.state,
    )

    assert result4.status == "confirmation_required"
    assert result4.state.awaiting_confirmation
    assert result4.invoice_draft is not None

    assert result4.invoice_draft.customer_name == "Sarah"
    assert result4.invoice_draft.customer_email == "sarah@example.com"
    assert result4.invoice_draft.amount == 350
    assert result4.invoice_draft.currency == "AUD"
    assert result4.invoice_draft.description == "logo design"


def test_cancel_confirmation():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email="sarah@example.com",
        amount=200,
        currency="AUD",
        description="tutoring",
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            (
                "Create an invoice for Sarah at "
                "sarah@example.com for $200 for tutoring."
            )
        )

    assert result1.status == "confirmation_required"
    assert result1.state.awaiting_confirmation

    with (
        patch(
            "app.assistant_service.create_invoice"
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice"
        ) as mock_send,
    ):
        result2 = process_message(
            "cancel",
            result1.state,
        )

    assert result2.status == "cancelled"

    mock_create.assert_not_called()
    mock_send.assert_not_called()

    assert result2.state.pending_invoice is None
    assert not result2.state.awaiting_confirmation


def test_invalid_email():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email=None,
        amount=100,
        currency="AUD",
        description="consulting",
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            "Invoice Sarah $100 for consulting."
        )

    assert result1.status == "needs_information"
    assert result1.state.requested_field == "customer_email"

    result2 = process_message(
        "not-an-email",
        result1.state,
    )

    assert result2.status == "needs_information"
    assert result2.state.requested_field == "customer_email"
    assert not result2.state.awaiting_confirmation
    assert result2.state.pending_invoice is not None
    assert result2.state.pending_invoice.customer_email is None


def test_invalid_amount():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email="sarah@example.com",
        amount=None,
        currency="AUD",
        description=None,
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            (
                "Create an invoice for Sarah at "
                "sarah@example.com."
            )
        )

    assert result1.status == "needs_information"
    assert result1.state.requested_field == "amount"

    result2 = process_message(
        "0",
        result1.state,
    )

    assert result2.status == "needs_information"
    assert result2.state.requested_field == "amount"
    assert not result2.state.awaiting_confirmation
    assert result2.state.pending_invoice is not None
    assert result2.state.pending_invoice.amount is None


def test_non_confirmation():
    initial_intent = AIIntent(
        intent="create_invoice",
        customer_name="Sarah",
        customer_email="sarah@example.com",
        amount=175,
        currency="AUD",
        description="maintenance",
        requires_confirmation=True,
    )

    with patch(
        "app.assistant_service.interpret_user_message",
        return_value=initial_intent,
    ):
        result1 = process_message(
            (
                "Invoice Sarah at sarah@example.com "
                "$175 for maintenance."
            )
        )

    assert result1.status == "confirmation_required"
    assert result1.state.awaiting_confirmation

    with (
        patch(
            "app.assistant_service.create_invoice"
        ) as mock_create,
        patch(
            "app.assistant_service.send_invoice"
        ) as mock_send,
    ):
        result2 = process_message(
            "maybe",
            result1.state,
        )

    assert result2.status == "confirmation_required"
    assert result2.state.awaiting_confirmation

    mock_create.assert_not_called()
    mock_send.assert_not_called()