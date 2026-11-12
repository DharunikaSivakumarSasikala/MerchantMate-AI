from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data.get("service") == "MerchantMate AI API"
    assert data.get("docs") == "/docs"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MerchantMate AI API",
        "version": "1.0.0",
    }


def test_empty_message_validation():
    response = client.post(
        "/api/chat",
        json={
            "message": "",
        },
    )

    assert response.status_code == 422


def test_chat_help():
    with patch(
        "app.main.process_message"
    ) as mock_process:
        mock_process.return_value = {
            "status": "success",
            "intent": "help",
            "message": "MerchantMate help response.",
            "data": None,
            "missing_fields": [],
            "invoice_draft": None,
            "requires_confirmation": False,
            "state": {
                "pending_invoice": None,
                "requested_field": None,
                "awaiting_confirmation": False,
                "paypal_invoice_id": None,
            },
        }

        response = client.post(
            "/api/chat",
            json={
                "message": "What can you do?",
            },
        )

    assert response.status_code == 200

    mock_process.assert_called_once()

    call = mock_process.call_args

    assert call.kwargs["user_message"] == "What can you do?"
    assert call.kwargs["state"] is None


def test_conversation_state_round_trip():
    incoming_state = {
        "pending_invoice": {
            "customer_name": "Sarah",
            "customer_email": None,
            "amount": 250.0,
            "currency": "AUD",
            "description": "photography",
        },
        "requested_field": "customer_email",
        "awaiting_confirmation": False,
        "paypal_invoice_id": None,
    }

    with patch(
        "app.main.process_message"
    ) as mock_process:
        mock_process.return_value = {
            "status": "confirmation_required",
            "intent": "create_invoice",
            "message": "Invoice ready for confirmation.",
            "data": None,
            "missing_fields": [],
            "invoice_draft": {
                "customer_name": "Sarah",
                "customer_email": "sarah@example.com",
                "amount": 250.0,
                "currency": "AUD",
                "description": "photography",
            },
            "requires_confirmation": True,
            "state": {
                "pending_invoice": {
                    "customer_name": "Sarah",
                    "customer_email": "sarah@example.com",
                    "amount": 250.0,
                    "currency": "AUD",
                    "description": "photography",
                },
                "requested_field": None,
                "awaiting_confirmation": True,
                "paypal_invoice_id": None,
            },
        }

        response = client.post(
            "/api/chat",
            json={
                "message": "sarah@example.com",
                "state": incoming_state,
            },
        )

    assert response.status_code == 200

    mock_process.assert_called_once()

    passed_state = mock_process.call_args.kwargs["state"]

    assert passed_state is not None
    assert passed_state.pending_invoice is not None
    assert passed_state.pending_invoice.customer_name == "Sarah"
    assert passed_state.requested_field == "customer_email"

    data = response.json()

    assert data["state"]["awaiting_confirmation"] is True


def test_confirmation_routes_through_service():
    confirmation_state = {
        "pending_invoice": {
            "customer_name": "Sarah",
            "customer_email": "sarah@example.com",
            "amount": 250.0,
            "currency": "AUD",
            "description": "photography",
        },
        "requested_field": None,
        "awaiting_confirmation": True,
        "paypal_invoice_id": None,
    }

    with patch(
        "app.main.process_message"
    ) as mock_process:
        mock_process.return_value = {
            "status": "confirmed",
            "intent": "create_invoice",
            "message": (
                "Invoice created and sent successfully "
                "through PayPal."
            ),
            "data": {
                "paypal_invoice_id": "INV2-MOCK-API",
                "sent": True,
            },
            "missing_fields": [],
            "invoice_draft": {
                "customer_name": "Sarah",
                "customer_email": "sarah@example.com",
                "amount": 250.0,
                "currency": "AUD",
                "description": "photography",
            },
            "requires_confirmation": False,
            "state": {
                "pending_invoice": None,
                "requested_field": None,
                "awaiting_confirmation": False,
                "paypal_invoice_id": None,
            },
        }

        response = client.post(
            "/api/chat",
            json={
                "message": "confirm",
                "state": confirmation_state,
            },
        )

    assert response.status_code == 200

    mock_process.assert_called_once()

    data = response.json()

    assert data["status"] == "confirmed"
    assert data["data"]["paypal_invoice_id"] == "INV2-MOCK-API"


def test_malformed_state_rejected():
    response = client.post(
        "/api/chat",
        json={
            "message": "confirm",
            "state": {
                "pending_invoice": None,
                "requested_field": "not_a_real_field",
                "awaiting_confirmation": True,
                "paypal_invoice_id": None,
            },
        },
    )

    assert response.status_code == 422