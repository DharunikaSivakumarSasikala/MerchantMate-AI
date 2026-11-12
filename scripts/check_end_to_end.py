from app.assistant_service import process_message


TEST_CASES = [
    {
        "name": "Complete natural-language invoice",
        "message": (
            "Create an invoice for Sarah at "
            "sarah@example.com for $350 for logo design."
        ),
        "expected_status": "confirmation_required",
        "expected_intent": "create_invoice",
        "confirmation": True,
    },
    {
        "name": "Invoice missing email",
        "message": (
            "Invoice Sarah $250 for photography."
        ),
        "expected_status": "needs_information",
        "expected_intent": "create_invoice",
        "confirmation": False,
    },
    {
        "name": "Invoice missing amount",
        "message": (
            "Create an invoice for Sarah at "
            "sarah@example.com for tutoring."
        ),
        "expected_status": "needs_information",
        "expected_intent": "create_invoice",
        "confirmation": False,
    },
    {
        "name": "Bare invoice request",
        "message": "Create an invoice.",
        "expected_status": "needs_information",
        "expected_intent": "create_invoice",
        "confirmation": False,
    },
    {
        "name": "Zero-value invoice",
        "message": (
            "Invoice Sarah at sarah@example.com "
            "0 AUD for consulting."
        ),
        "expected_status": "error",
        "expected_intent": "create_invoice",
        "confirmation": False,
    },
    {
        "name": "Unsupported payment",
        "message": "Pay Sarah $300.",
        "expected_status": "unsupported",
        "expected_intent": "unknown",
        "confirmation": False,
    },
    {
        "name": "Unsupported refund",
        "message": "Refund Sarah $50.",
        "expected_status": "unsupported",
        "expected_intent": "unknown",
        "confirmation": False,
    },
    {
        "name": "Help",
        "message": "What can you help me with?",
        "expected_status": "success",
        "expected_intent": "help",
        "confirmation": False,
    },
]


def run_test(number, test):
    print(f"\nTest {number}: {test['name']}")
    print(f"User: {test['message']}")

    result = process_message(
        test["message"]
    )

    print(f"Status: {result.status}")
    print(f"Intent: {result.intent}")
    print(f"Message: {result.message}")
    print(
        "Requires confirmation: "
        f"{result.requires_confirmation}"
    )

    if result.missing_fields:
        print(
            f"Missing fields: "
            f"{result.missing_fields}"
        )

    if result.invoice_draft:
        print(
            "Invoice draft: "
            f"{result.invoice_draft.model_dump()}"
        )

    errors = []

    if (
        result.status
        != test["expected_status"]
    ):
        errors.append(
            "status: expected "
            f"{test['expected_status']!r}, "
            f"got {result.status!r}"
        )

    if (
        result.intent
        != test["expected_intent"]
    ):
        errors.append(
            "intent: expected "
            f"{test['expected_intent']!r}, "
            f"got {result.intent!r}"
        )

    if (
        result.requires_confirmation
        != test["confirmation"]
    ):
        errors.append(
            "requires_confirmation: expected "
            f"{test['confirmation']!r}, "
            f"got "
            f"{result.requires_confirmation!r}"
        )

    if errors:
        print("RESULT: FAIL")

        for error in errors:
            print(f"  - {error}")

        return False

    print("RESULT: PASS")
    return True


def main():
    print(
        "\nMerchantMate End-to-End "
        "Orchestration Tests"
    )
    print("=" * 70)

    passed = 0

    for number, test in enumerate(
        TEST_CASES,
        start=1,
    ):
        if run_test(number, test):
            passed += 1

    total = len(TEST_CASES)
    failed = total - passed

    print("\n" + "=" * 70)
    print("End-to-End Summary")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(
        f"Accuracy: "
        f"{(passed / total) * 100:.1f}%"
    )

    if failed == 0:
        print(
            "\nMerchantMate end-to-end "
            "orchestration passed."
        )
        print(
            "No PayPal invoice was created "
            "during these tests."
        )
    else:
        print(
            "\nResolve orchestration failures "
            "before enabling invoice execution."
        )


if __name__ == "__main__":
    main()