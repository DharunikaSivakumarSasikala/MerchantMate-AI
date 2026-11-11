from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def check(
    condition,
    message,
    errors,
):
    if not condition:
        errors.append(message)


def test_root():
    errors = []

    response = client.get("/")

    print(
        "Status code:",
        response.status_code,
    )

    print(
        "Response:",
        response.json(),
    )

    check(
        response.status_code == 200,
        "Root endpoint should return HTTP 200.",
        errors,
    )

    data = response.json()

    check(
        data.get("service")
        == "MerchantMate AI API",
        "Root service name is incorrect.",
        errors,
    )

    check(
        data.get("docs")
        == "/docs",
        "Root should advertise /docs.",
        errors,
    )

    return errors


def test_health():
    errors = []

    response = client.get(
        "/health"
    )

    print(
        "Status code:",
        response.status_code,
    )

    print(
        "Response:",
        response.json(),
    )

    check(
        response.status_code == 200,
        "Health endpoint should return HTTP 200.",
        errors,
    )

    check(
        response.json()
        == {
            "status": "ok",
            "service": "MerchantMate AI API",
            "version": "1.0.0",
        },
        "Health response is incorrect.",
        errors,
    )

    return errors


def test_empty_message_validation():
    errors = []

    response = client.post(
        "/api/chat",
        json={
            "message": "",
        },
    )

    print(
        "Status code:",
        response.status_code,
    )

    check(
        response.status_code == 422,
        "Empty messages should be rejected with HTTP 422.",
        errors,
    )

    return errors


def test_chat_help():
    errors = []

    with patch(
        "app.main.process_message"
    ) as mock_process:
        mock_process.return_value = {
            "status": "success",
            "intent": "help",
            "message": (
                "MerchantMate help response."
            ),
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
                "message": "What can you do?"
            },
        )

    print(
        "Status code:",
        response.status_code,
    )

    print(
        "Response:",
        response.json(),
    )

    check(
        response.status_code == 200,
        "Chat endpoint should return HTTP 200.",
        errors,
    )

    check(
        mock_process.call_count == 1,
        "process_message should be called once.",
        errors,
    )

    call = mock_process.call_args

    check(
        call.kwargs["user_message"]
        == "What can you do?",
        "API passed the wrong message.",
        errors,
    )

    check(
        call.kwargs["state"]
        is None,
        "New conversation should have no state.",
        errors,
    )

    return errors


def test_conversation_state_round_trip():
    errors = []

    incoming_state = {
        "pending_invoice": {
            "customer_name": "Sarah",
            "customer_email": None,
            "amount": 250.0,
            "currency": "AUD",
            "description": "photography",
        },
        "requested_field": (
            "customer_email"
        ),
        "awaiting_confirmation": False,
        "paypal_invoice_id": None,
    }

    with patch(
        "app.main.process_message"
    ) as mock_process:
        mock_process.return_value = {
            "status": "confirmation_required",
            "intent": "create_invoice",
            "message": (
                "Invoice ready for confirmation."
            ),
            "data": None,
            "missing_fields": [],
            "invoice_draft": {
                "customer_name": "Sarah",
                "customer_email": (
                    "sarah@example.com"
                ),
                "amount": 250.0,
                "currency": "AUD",
                "description": "photography",
            },
            "requires_confirmation": True,
            "state": {
                "pending_invoice": {
                    "customer_name": "Sarah",
                    "customer_email": (
                        "sarah@example.com"
                    ),
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
                "message": (
                    "sarah@example.com"
                ),
                "state": incoming_state,
            },
        )

    print(
        "Status code:",
        response.status_code,
    )

    data = response.json()

    print(
        "Response:",
        data,
    )

    check(
        response.status_code == 200,
        "Stateful chat should return HTTP 200.",
        errors,
    )

    check(
        mock_process.call_count == 1,
        "process_message should be called once.",
        errors,
    )

    passed_state = (
        mock_process.call_args
        .kwargs["state"]
    )

    check(
        passed_state is not None,
        "Conversation state was not passed.",
        errors,
    )

    if passed_state:
        check(
            passed_state.pending_invoice
            is not None,
            "Pending invoice was lost.",
            errors,
        )

        if passed_state.pending_invoice:
            check(
                passed_state
                .pending_invoice
                .customer_name
                == "Sarah",
                "Customer name was not preserved.",
                errors,
            )

        check(
            passed_state.requested_field
            == "customer_email",
            "Requested field was not preserved.",
            errors,
        )

    check(
        data["state"][
            "awaiting_confirmation"
        ]
        is True,
        "Updated state was not returned.",
        errors,
    )

    return errors


def test_confirmation_routes_through_service():
    errors = []

    confirmation_state = {
        "pending_invoice": {
            "customer_name": "Sarah",
            "customer_email": (
                "sarah@example.com"
            ),
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
                "Invoice created and sent "
                "successfully through PayPal."
            ),
            "data": {
                "paypal_invoice_id": (
                    "INV2-MOCK-API"
                ),
                "sent": True,
            },
            "missing_fields": [],
            "invoice_draft": {
                "customer_name": "Sarah",
                "customer_email": (
                    "sarah@example.com"
                ),
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

    data = response.json()

    print(
        "Status code:",
        response.status_code,
    )

    print(
        "Response:",
        data,
    )

    check(
        response.status_code == 200,
        "Confirmation request should return HTTP 200.",
        errors,
    )

    check(
        mock_process.call_count == 1,
        "Confirmation should route through "
        "process_message exactly once.",
        errors,
    )

    check(
        data["status"]
        == "confirmed",
        "Confirmed status was not returned.",
        errors,
    )

    check(
        data["data"][
            "paypal_invoice_id"
        ]
        == "INV2-MOCK-API",
        "Invoice ID was not returned.",
        errors,
    )

    return errors


def test_malformed_state_rejected():
    errors = []

    response = client.post(
        "/api/chat",
        json={
            "message": "confirm",
            "state": {
                "pending_invoice": None,
                "requested_field": (
                    "not_a_real_field"
                ),
                "awaiting_confirmation": True,
                "paypal_invoice_id": None,
            },
        },
    )

    print(
        "Status code:",
        response.status_code,
    )

    check(
        response.status_code == 422,
        "Malformed state should return HTTP 422.",
        errors,
    )

    return errors


def main():
    print(
        "\nMerchantMate FastAPI Tests"
    )

    print(
        "=" * 70
    )

    tests = [
        (
            "Root endpoint",
            test_root,
        ),
        (
            "Health endpoint",
            test_health,
        ),
        (
            "Empty message validation",
            test_empty_message_validation,
        ),
        (
            "Chat routing",
            test_chat_help,
        ),
        (
            "Conversation state round trip",
            test_conversation_state_round_trip,
        ),
        (
            "Confirmation routes through service",
            test_confirmation_routes_through_service,
        ),
        (
            "Malformed state validation",
            test_malformed_state_rejected,
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
        "FastAPI Test Summary"
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
            "\nMerchantMate FastAPI layer passed "
            "all API tests."
        )

        print(
            "PayPal execution was mocked at the "
            "orchestration boundary."
        )

    else:
        print(
            "\nFix API failures before connecting "
            "the Streamlit frontend."
        )


if __name__ == "__main__":
    main()