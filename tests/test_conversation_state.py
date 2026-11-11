from app.assistant_service import process_message


def check(
    condition,
    message,
    errors,
):
    if not condition:
        errors.append(message)


def print_result(
    result,
):
    print(f"Status: {result.status}")
    print(f"Message: {result.message}")

    print(
        "Requested field: "
        f"{result.state.requested_field}"
    )

    print(
        "Awaiting confirmation: "
        f"{result.state.awaiting_confirmation}"
    )

    if result.state.pending_invoice:
        print(
            "Pending invoice: "
            f"{result.state.pending_invoice.model_dump()}"
        )

    if result.invoice_draft:
        print(
            "Draft: "
            f"{result.invoice_draft.model_dump()}"
        )


def test_missing_email_flow():
    errors = []

    print("\nStep 1")
    result1 = process_message(
        "Invoice Sarah $250 for photography."
    )

    print_result(result1)

    check(
        result1.status
        == "needs_information",
        "Step 1 should request information.",
        errors,
    )

    check(
        result1.state.requested_field
        == "customer_email",
        "Step 1 should request customer_email.",
        errors,
    )

    print("\nStep 2")
    result2 = process_message(
        "sarah@example.com",
        result1.state,
    )

    print_result(result2)

    check(
        result2.status
        == "confirmation_required",
        "Step 2 should reach confirmation.",
        errors,
    )

    check(
        result2.state.awaiting_confirmation,
        "Step 2 should await confirmation.",
        errors,
    )

    check(
        result2.invoice_draft is not None,
        "Step 2 should contain an invoice draft.",
        errors,
    )

    if result2.invoice_draft:
        check(
            result2.invoice_draft.customer_name
            == "Sarah",
            "Customer name should remain Sarah.",
            errors,
        )

        check(
            result2.invoice_draft.customer_email
            == "sarah@example.com",
            "Customer email was not stored.",
            errors,
        )

        check(
            result2.invoice_draft.amount
            == 250,
            "Amount should remain 250.",
            errors,
        )

        check(
            result2.invoice_draft.description
            == "photography",
            "Description should remain photography.",
            errors,
        )

    print("\nStep 3")
    result3 = process_message(
        "confirm",
        result2.state,
    )

    print_result(result3)

    check(
        result3.status == "confirmed",
        "Step 3 should accept confirmation.",
        errors,
    )

    check(
        result3.state.pending_invoice
        is None,
        "State should be cleared after confirmation.",
        errors,
    )

    return errors


def test_multiple_missing_fields():
    errors = []

    print("\nStep 1")
    result1 = process_message(
        "Create an invoice for Sarah."
    )

    print_result(result1)

    check(
        result1.state.requested_field
        == "customer_email",
        "First requested field should be email.",
        errors,
    )

    print("\nStep 2")
    result2 = process_message(
        "sarah@example.com",
        result1.state,
    )

    print_result(result2)

    check(
        result2.state.requested_field
        == "amount",
        "Second requested field should be amount.",
        errors,
    )

    print("\nStep 3")
    result3 = process_message(
        "350 AUD",
        result2.state,
    )

    print_result(result3)

    check(
        result3.state.requested_field
        == "description",
        "Third requested field should be description.",
        errors,
    )

    print("\nStep 4")
    result4 = process_message(
        "logo design",
        result3.state,
    )

    print_result(result4)

    check(
        result4.status
        == "confirmation_required",
        "Completed invoice should require confirmation.",
        errors,
    )

    if result4.invoice_draft:
        check(
            result4.invoice_draft.amount
            == 350,
            "Final amount should be 350.",
            errors,
        )

        check(
            result4.invoice_draft.currency
            == "AUD",
            "Final currency should be AUD.",
            errors,
        )

        check(
            result4.invoice_draft.description
            == "logo design",
            "Final description should be logo design.",
            errors,
        )

    else:
        errors.append(
            "Final invoice draft is missing."
        )

    return errors


def test_cancel_confirmation():
    errors = []

    result1 = process_message(
        (
            "Create an invoice for Sarah at "
            "sarah@example.com for $200 for tutoring."
        )
    )

    print_result(result1)

    check(
        result1.status
        == "confirmation_required",
        "Invoice should require confirmation.",
        errors,
    )

    result2 = process_message(
        "cancel",
        result1.state,
    )

    print_result(result2)

    check(
        result2.status == "cancelled",
        "Cancel should cancel the invoice.",
        errors,
    )

    check(
        result2.state.pending_invoice
        is None,
        "Cancel should clear pending invoice.",
        errors,
    )

    return errors


def test_invalid_email():
    errors = []

    result1 = process_message(
        "Invoice Sarah $100 for consulting."
    )

    result2 = process_message(
        "not-an-email",
        result1.state,
    )

    print_result(result2)

    check(
        result2.status
        == "needs_information",
        "Invalid email should request information again.",
        errors,
    )

    check(
        result2.state.requested_field
        == "customer_email",
        "Email should still be requested.",
        errors,
    )

    return errors


def test_invalid_amount():
    errors = []

    result1 = process_message(
        (
            "Create an invoice for Sarah at "
            "sarah@example.com."
        )
    )

    print_result(result1)

    # Depending on extraction, description is also missing,
    # but amount should be requested before description.
    check(
        result1.state.requested_field
        == "amount",
        "Amount should be requested.",
        errors,
    )

    result2 = process_message(
        "0",
        result1.state,
    )

    print_result(result2)

    check(
        result2.status
        == "needs_information",
        "Zero amount should be rejected.",
        errors,
    )

    check(
        result2.state.requested_field
        == "amount",
        "Amount should still be requested.",
        errors,
    )

    return errors


def test_non_confirmation():
    errors = []

    result1 = process_message(
        (
            "Invoice Sarah at sarah@example.com "
            "$175 for maintenance."
        )
    )

    result2 = process_message(
        "maybe",
        result1.state,
    )

    print_result(result2)

    check(
        result2.status
        == "confirmation_required",
        "Ambiguous response must not confirm.",
        errors,
    )

    check(
        result2.state.awaiting_confirmation,
        "Confirmation state must remain active.",
        errors,
    )

    return errors


def main():
    print(
        "\nMerchantMate Multi-Turn Conversation Tests"
    )
    print("=" * 70)

    tests = [
        (
            "Missing email → confirmation",
            test_missing_email_flow,
        ),
        (
            "Multiple missing fields",
            test_multiple_missing_fields,
        ),
        (
            "Cancel confirmation",
            test_cancel_confirmation,
        ),
        (
            "Invalid email",
            test_invalid_email,
        ),
        (
            "Invalid amount",
            test_invalid_amount,
        ),
        (
            "Ambiguous confirmation",
            test_non_confirmation,
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
            errors = test_function()

        except Exception as exc:
            errors = [
                f"Unexpected exception: {exc}"
            ]

        if errors:
            print("\nRESULT: FAIL")

            for error in errors:
                print(
                    f"  - {error}"
                )

        else:
            print("\nRESULT: PASS")
            passed += 1

    total = len(tests)
    failed = total - passed

    print("\n" + "=" * 70)
    print("Multi-Turn Conversation Summary")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(
        f"Accuracy: "
        f"{(passed / total) * 100:.1f}%"
    )

    if failed == 0:
        print(
            "\nMerchantMate multi-turn invoice "
            "state machine passed."
        )
        print(
            "PayPal execution remains disabled."
        )
    else:
        print(
            "\nDo not enable PayPal execution "
            "until all conversation tests pass."
        )


if __name__ == "__main__":
    main()