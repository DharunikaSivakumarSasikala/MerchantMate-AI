from unittest.mock import patch

from app.assistant_service import (
    process_intent,
    process_message,
)
from app.models import AIIntent


def check(
    condition,
    message,
    errors,
):
    if not condition:
        errors.append(
            message
        )


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

    result = process_intent(
        intent
    )

    if (
        result.status
        != "confirmation_required"
    ):
        raise AssertionError(
            "Test setup failed to create confirmation state."
        )

    return result.state


def test_successful_execution():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    print(
        f"Status: {result.status}"
    )
    print(
        f"Message: {result.message}"
    )
    print(
        f"Data: {result.data}"
    )

    check(
        result.status
        == "confirmed",
        "Successful execution should return confirmed.",
        errors,
    )

    check(
        mock_create.call_count
        == 1,
        "create_invoice should be called exactly once.",
        errors,
    )

    check(
        mock_send.call_count
        == 1,
        "send_invoice should be called exactly once.",
        errors,
    )

    mock_send.assert_called_once_with(
        "INV2-TEST-001"
    )

    check(
        result.data
        == {
            "paypal_invoice_id": (
                "INV2-TEST-001"
            ),
            "sent": True,
        },
        "Successful execution data is incorrect.",
        errors,
    )

    check(
        result.state.pending_invoice
        is None,
        "State should clear after successful execution.",
        errors,
    )

    check(
        result.state.paypal_invoice_id
        is None,
        "PayPal ID should clear from conversation state "
        "after success.",
        errors,
    )

    return errors


def test_cancel_does_not_execute():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    print(
        f"Status: {result.status}"
    )

    check(
        result.status
        == "cancelled",
        "Cancel should return cancelled.",
        errors,
    )

    check(
        mock_create.call_count
        == 0,
        "Cancel must not create an invoice.",
        errors,
    )

    check(
        mock_send.call_count
        == 0,
        "Cancel must not send an invoice.",
        errors,
    )

    return errors


def test_ambiguous_confirmation_does_not_execute():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    print(
        f"Status: {result.status}"
    )

    check(
        result.status
        == "confirmation_required",
        "Ambiguous confirmation must remain pending.",
        errors,
    )

    check(
        mock_create.call_count
        == 0,
        "Ambiguous confirmation must not create an invoice.",
        errors,
    )

    check(
        mock_send.call_count
        == 0,
        "Ambiguous confirmation must not send an invoice.",
        errors,
    )

    return errors


def test_creation_failure():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    print(
        f"Status: {result.status}"
    )
    print(
        f"Message: {result.message}"
    )

    check(
        result.status
        == "error",
        "Creation failure should return error.",
        errors,
    )

    check(
        mock_create.call_count
        == 1,
        "Creation should have been attempted once.",
        errors,
    )

    check(
        mock_send.call_count
        == 0,
        "Send must not run if creation fails.",
        errors,
    )

    check(
        result.state.paypal_invoice_id
        is None,
        "No PayPal ID should exist after creation failure.",
        errors,
    )

    check(
        result.state.awaiting_confirmation,
        "State should remain recoverable after creation failure.",
        errors,
    )

    return errors


def test_send_failure_preserves_invoice_id():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    print(
        f"Status: {result.status}"
    )
    print(
        f"Message: {result.message}"
    )

    check(
        result.status
        == "error",
        "Send failure should return error.",
        errors,
    )

    check(
        mock_create.call_count
        == 1,
        "Invoice should be created exactly once.",
        errors,
    )

    check(
        mock_send.call_count
        == 1,
        "Send should be attempted exactly once.",
        errors,
    )

    check(
        result.state.paypal_invoice_id
        == "INV2-TEST-002",
        "Created PayPal invoice ID must be preserved.",
        errors,
    )

    check(
        result.state.awaiting_confirmation,
        "Retry state should remain active.",
        errors,
    )

    return errors


def test_retry_does_not_create_duplicate():
    errors = []

    state = (
        create_confirmation_state()
    )

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
        first_result = (
            process_message(
                "confirm",
                state,
            )
        )

    check(
        first_result.state.paypal_invoice_id
        == "INV2-TEST-003",
        "First failure should preserve invoice ID.",
        errors,
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
        second_result = (
            process_message(
                "retry",
                first_result.state,
            )
        )

    print(
        f"Retry status: "
        f"{second_result.status}"
    )

    print(
        f"Retry message: "
        f"{second_result.message}"
    )

    check(
        mock_create.call_count
        == 1,
        "Original invoice should only be created once.",
        errors,
    )

    check(
        mock_send.call_count
        == 1,
        "First send should be attempted once.",
        errors,
    )

    check(
        retry_create.call_count
        == 0,
        "Retry must not create another PayPal invoice.",
        errors,
    )

    check(
        retry_send.call_count
        == 1,
        "Retry should send the existing invoice once.",
        errors,
    )

    retry_send.assert_called_once_with(
        "INV2-TEST-003"
    )

    check(
        second_result.status
        == "confirmed",
        "Successful retry should return confirmed.",
        errors,
    )

    check(
        second_result.data
        == {
            "paypal_invoice_id": (
                "INV2-TEST-003"
            ),
            "sent": True,
        },
        "Retry should return the existing PayPal invoice ID.",
        errors,
    )

    check(
        second_result.state.pending_invoice
        is None,
        "State should clear after successful retry.",
        errors,
    )

    return errors


def test_repeated_confirmation_after_success():
    errors = []

    state = (
        create_confirmation_state()
    )

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

    check(
        result.status
        == "confirmed",
        "First confirmation should succeed.",
        errors,
    )

    check(
        result.state.pending_invoice
        is None,
        "Successful execution must clear invoice state.",
        errors,
    )

    check(
        mock_create.call_count
        == 1,
        "Only one invoice should be created.",
        errors,
    )

    check(
        mock_send.call_count
        == 1,
        "Only one invoice should be sent.",
        errors,
    )

    # We deliberately do not feed another "confirm" through Ollama.
    # The important safety property is that no executable invoice
    # remains in the returned state after success.
    check(
        not result.state.awaiting_confirmation,
        "Successful state must not remain executable.",
        errors,
    )

    check(
        result.state.paypal_invoice_id
        is None,
        "Successful conversation state should be cleared.",
        errors,
    )

    return errors


def main():
    print(
        "\nMerchantMate PayPal Execution Safety Tests"
    )
    print(
        "=" * 70
    )

    tests = [
        (
            "Successful confirmed execution",
            test_successful_execution,
        ),
        (
            "Cancellation blocks execution",
            test_cancel_does_not_execute,
        ),
        (
            "Ambiguous confirmation blocks execution",
            test_ambiguous_confirmation_does_not_execute,
        ),
        (
            "PayPal creation failure",
            test_creation_failure,
        ),
        (
            "Send failure preserves invoice ID",
            test_send_failure_preserves_invoice_id,
        ),
        (
            "Retry does not create duplicate",
            test_retry_does_not_create_duplicate,
        ),
        (
            "Successful state cannot execute again",
            test_repeated_confirmation_after_success,
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
        "PayPal Execution Safety Summary"
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
            "\nMerchantMate PayPal execution "
            "safety tests passed."
        )
        print(
            "All PayPal operations in this test "
            "suite were mocked."
        )
    else:
        print(
            "\nDo not perform a live sandbox invoice "
            "test until every execution test passes."
        )


if __name__ == "__main__":
    main()