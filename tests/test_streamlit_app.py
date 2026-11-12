from pathlib import Path
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parent.parent

APP_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "streamlit_app.py"
)


def mock_health_response():
    response = Mock()

    response.raise_for_status.return_value = None

    response.json.return_value = {
        "status": "ok",
        "service": "MerchantMate AI API",
        "version": "1.0.0",
    }

    return response


def test_app_loads():
    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    assert len(app.exception) == 0

    titles = [
        element.value
        for element in app.title
    ]

    assert "MerchantMate AI" in titles


def test_dashboard_metrics_exist():
    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    labels = [
        metric.label
        for metric in app.metric
    ]

    expected = [
        "Total Invoiced",
        "Outstanding",
        "Paid",
        "Average Invoice",
    ]

    for label in expected:
        assert label in labels, (
            f"Missing dashboard metric: {label}"
        )


def test_api_connected_status():
    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    success_messages = [
        element.value
        for element in app.success
    ]

    assert any(
        "API: Connected" in message
        for message in success_messages
    )


def test_disconnected_api():
    with patch(
        "requests.get",
        side_effect=requests.ConnectionError(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    error_messages = [
        element.value
        for element in app.error
    ]

    assert any(
        "API: Disconnected" in message
        for message in error_messages
    )


def test_initial_state_is_safe():
    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    state = app.session_state[
        "conversation_state"
    ]

    assert state["pending_invoice"] is None
    assert state["awaiting_confirmation"] is False
    assert state["paypal_invoice_id"] is None


def test_new_conversation_clears_state():
    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

        app.session_state[
            "conversation_state"
        ] = {
            "pending_invoice": {
                "customer_name": "Test Customer",
                "customer_email": "test@example.com",
                "amount": 5.0,
                "currency": "AUD",
                "description": "test",
            },
            "requested_field": None,
            "awaiting_confirmation": True,
            "paypal_invoice_id": None,
        }

        app.session_state[
            "messages"
        ] = [
            {
                "role": "user",
                "content": "test",
            }
        ]

        new_conversation = next(
            (
                button
                for button in app.button
                if button.label
                == "New conversation"
            ),
            None,
        )

        assert new_conversation is not None

        new_conversation.click().run()

        state = app.session_state[
            "conversation_state"
        ]

        assert state["pending_invoice"] is None
        assert state["awaiting_confirmation"] is False
        assert len(
            app.session_state["messages"]
        ) == 0