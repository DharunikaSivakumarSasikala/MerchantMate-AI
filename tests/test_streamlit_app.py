from pathlib import Path
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

APP_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "streamlit_app.py"
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def check(
    condition,
    message,
    errors,
):
    if not condition:
        errors.append(
            message
        )


def mock_health_response():
    response = Mock()

    response.raise_for_status.return_value = (
        None
    )

    response.json.return_value = {
        "status": "ok",
        "service": "MerchantMate AI API",
        "version": "1.0.0",
    }

    return response


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------

def test_app_loads():
    errors = []

    with patch(
        "requests.get",
        return_value=mock_health_response(),
    ):
        app = AppTest.from_file(
            str(APP_PATH)
        ).run()

    check(
        len(app.exception) == 0,
        "Streamlit app should load without exceptions.",
        errors,
    )

    titles = [
        element.value
        for element in app.title
    ]

    check(
        "MerchantMate AI" in titles,
        "MerchantMate title should be visible.",
        errors,
    )

    return errors


def test_dashboard_metrics_exist():
    errors = []

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
        check(
            label in labels,
            f"Missing dashboard metric: {label}",
            errors,
        )

    return errors


def test_api_connected_status():
    errors = []

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

    check(
        any(
            "API: Connected" in message
            for message in success_messages
        ),
        (
            "Connected API status should "
            "be displayed."
        ),
        errors,
    )

    return errors


def test_disconnected_api():
    errors = []

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

    check(
        any(
            "API: Disconnected" in message
            for message in error_messages
        ),
        (
            "Disconnected API status should "
            "be displayed."
        ),
        errors,
    )

    return errors


def test_initial_state_is_safe():
    errors = []

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

    check(
        state[
            "pending_invoice"
        ]
        is None,
        (
            "Initial state should have no "
            "pending invoice."
        ),
        errors,
    )

    check(
        state[
            "awaiting_confirmation"
        ]
        is False,
        (
            "Initial state must not await "
            "confirmation."
        ),
        errors,
    )

    check(
        state[
            "paypal_invoice_id"
        ]
        is None,
        (
            "Initial state must not contain "
            "a PayPal invoice ID."
        ),
        errors,
    )

    return errors


def test_new_conversation_clears_state():
    errors = []

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
                "customer_name": (
                    "Test Customer"
                ),
                "customer_email": (
                    "test@example.com"
                ),
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

        new_conversation = None

        for button in app.button:
            if (
                button.label
                == "New conversation"
            ):
                new_conversation = (
                    button
                )

                break

        check(
            new_conversation
            is not None,
            (
                "New conversation button "
                "was not found."
            ),
            errors,
        )

        if (
            new_conversation
            is not None
        ):
            new_conversation.click().run()

            state = (
                app.session_state[
                    "conversation_state"
                ]
            )

            check(
                state[
                    "pending_invoice"
                ]
                is None,
                (
                    "New conversation should "
                    "clear pending invoice."
                ),
                errors,
            )

            check(
                state[
                    "awaiting_confirmation"
                ]
                is False,
                (
                    "New conversation should "
                    "clear confirmation state."
                ),
                errors,
            )

            check(
                len(
                    app.session_state[
                        "messages"
                    ]
                )
                == 0,
                (
                    "New conversation should "
                    "clear chat history."
                ),
                errors,
            )

    return errors


# ---------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------

def main():
    print(
        "\nMerchantMate Streamlit Tests"
    )

    print(
        "=" * 70
    )

    print(
        f"Testing app: {APP_PATH}"
    )

    tests = [
        (
            "Application loads",
            test_app_loads,
        ),
        (
            "Dashboard metrics",
            test_dashboard_metrics_exist,
        ),
        (
            "API connected status",
            test_api_connected_status,
        ),
        (
            "API disconnected status",
            test_disconnected_api,
        ),
        (
            "Safe initial state",
            test_initial_state_is_safe,
        ),
        (
            "New conversation clears state",
            test_new_conversation_clears_state,
        ),
    ]

    passed = 0

    for number, (
        name,
        test_function,
    ) in enumerate(
        tests,
        start=1,
    ):
        print(
            f"\n{'-' * 70}"
        )

        print(
            f"Test {number}: {name}"
        )

        try:
            errors = (
                test_function()
            )

        except Exception as exc:
            errors = [
                (
                    "Unexpected exception: "
                    f"{exc}"
                )
            ]

        if errors:
            print(
                "\nRESULT: FAIL"
            )

            for error in errors:
                print(
                    f"  - {error}"
                )

        else:
            print(
                "\nRESULT: PASS"
            )

            passed += 1

    total = len(
        tests
    )

    failed = (
        total - passed
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "Streamlit Test Summary"
    )

    print(
        f"Passed: {passed}/{total}"
    )

    print(
        f"Failed: {failed}/{total}"
    )

    print(
        "Accuracy: "
        f"{(passed / total) * 100:.1f}%"
    )

    if failed == 0:
        print(
            "\nMerchantMate Streamlit frontend "
            "passed all UI tests."
        )

        print(
            "No PayPal write operations were "
            "performed by this test suite."
        )

    else:
        print(
            "\nFix frontend failures before "
            "committing the Streamlit milestone."
        )


if __name__ == "__main__":
    main()