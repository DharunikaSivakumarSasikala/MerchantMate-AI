from app.ai_service import interpret_user_message


TEST_CASES = [
    # ---------------------------------------------------------
    # Natural invoice phrasing
    # ---------------------------------------------------------
    {
        "name": "Casual invoice wording",
        "message": "Hey, could you bill Sarah 275 bucks for the design work?",
        "expected": {
            "intent": "create_invoice",
            "customer_name": "Sarah",
            "amount": 275.0,
            "currency": "AUD",
            "description": "design work",
            "requires_confirmation": True,
        },
    },
    {
        "name": "Email without customer name",
        "message": (
            "I need to charge alex@example.com 89.50 "
            "for consulting."
        ),
        "expected": {
            "intent": "create_invoice",
            "customer_email": "alex@example.com",
            "amount": 89.50,
            "currency": "AUD",
            "description": "consulting",
            "requires_confirmation": True,
        },
    },
    {
        "name": "Invoice with USD",
        "message": (
            "Create an invoice for Michael for 500 USD "
            "for development services."
        ),
        "expected": {
            "intent": "create_invoice",
            "customer_name": "Michael",
            "amount": 500.0,
            "currency": "USD",
            "description": "development services",
            "requires_confirmation": True,
        },
    },

    # ---------------------------------------------------------
    # Missing information
    # ---------------------------------------------------------
    {
        "name": "Missing customer details",
        "message": "Send an invoice for $500 for photography.",
        "expected": {
            "intent": "create_invoice",
            "customer_name": None,
            "customer_email": None,
            "amount": 500.0,
            "currency": "AUD",
            "description": "photography",
            "requires_confirmation": True,
        },
    },
    {
        "name": "Missing amount",
        "message": "Invoice Priya for tutoring services.",
        "expected": {
            "intent": "create_invoice",
            "customer_name": "Priya",
            "amount": None,
            "description": "tutoring services",
            "requires_confirmation": True,
        },
    },

    # ---------------------------------------------------------
    # Analytics paraphrases
    # ---------------------------------------------------------
    {
        "name": "Outstanding amount paraphrase",
        "message": "How much do people still owe me?",
        "expected": {
            "intent": "outstanding_amount",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Paid amount paraphrase",
        "message": "Have I actually been paid anything yet?",
        "expected": {
            "intent": "paid_amount",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Top customer paraphrase",
        "message": "Who spends the most with me?",
        "expected": {
            "intent": "top_customer",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Outstanding invoices paraphrase",
        "message": "Show me everyone I'm still waiting on payment from.",
        "expected": {
            "intent": "outstanding_invoices",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Business overview paraphrase",
        "message": "How is my business doing overall?",
        "expected": {
            "intent": "business_summary",
            "requires_confirmation": False,
        },
    },

    # ---------------------------------------------------------
    # Time periods
    # ---------------------------------------------------------
    {
        "name": "Weekly period",
        "message": "How much have I invoiced this week?",
        "expected": {
            "intent": "total_invoiced",
            "period": "this week",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Monthly period",
        "message": "How much have I been paid this month?",
        "expected": {
            "intent": "paid_amount",
            "period": "this month",
            "requires_confirmation": False,
        },
    },

    # ---------------------------------------------------------
    # Unsupported actions
    # ---------------------------------------------------------
    {
        "name": "Payment request",
        "message": "Pay Sarah $300.",
        "expected": {
            "intent": "unknown",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Delete invoices",
        "message": "Delete all my invoices.",
        "expected": {
            "intent": "unknown",
            "requires_confirmation": False,
        },
    },
    {
        "name": "Refund request",
        "message": "Refund John $50.",
        "expected": {
            "intent": "unknown",
            "requires_confirmation": False,
        },
    },

    # ---------------------------------------------------------
    # Completely unrelated requests
    # ---------------------------------------------------------
    {
        "name": "Weather",
        "message": "Will it rain tomorrow?",
        "expected": {
            "intent": "unknown",
            "requires_confirmation": False,
        },
    },
    {
        "name": "General knowledge",
        "message": "Who is the prime minister of Australia?",
        "expected": {
            "intent": "unknown",
            "requires_confirmation": False,
        },
    },
]


def check_expected(result, expected):
    errors = []

    for field, expected_value in expected.items():
        actual_value = getattr(result, field)

        if actual_value != expected_value:
            errors.append(
                f"{field}: expected {expected_value!r}, "
                f"got {actual_value!r}"
            )

    return errors


def main():
    print("\nMerchantMate AI Robustness Tests")
    print("=" * 70)

    passed = 0
    failed = 0

    for number, test_case in enumerate(TEST_CASES, start=1):
        name = test_case["name"]
        message = test_case["message"]
        expected = test_case["expected"]

        print(f"\nTest {number}: {name}")
        print(f"User: {message}")

        try:
            result = interpret_user_message(message)

            print(f"Intent: {result.intent}")
            print(f"Customer: {result.customer_name}")
            print(f"Email: {result.customer_email}")
            print(f"Amount: {result.amount}")
            print(f"Currency: {result.currency}")
            print(f"Description: {result.description}")
            print(f"Period: {result.period}")
            print(
                "Requires confirmation: "
                f"{result.requires_confirmation}"
            )

            errors = check_expected(result, expected)

            if errors:
                failed += 1
                print("RESULT: FAIL")

                for error in errors:
                    print(f"  - {error}")
            else:
                passed += 1
                print("RESULT: PASS")

        except Exception as exc:
            failed += 1
            print("RESULT: ERROR")
            print(f"  - {exc}")

    total = len(TEST_CASES)
    accuracy = (passed / total) * 100

    print("\n" + "=" * 70)
    print("Robustness Summary")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(f"Accuracy: {accuracy:.1f}%")

    if failed == 0:
        print("\nAll MerchantMate robustness tests passed.")
    else:
        print(
            "\nReview failed cases before connecting "
            "AI output to PayPal."
        )


if __name__ == "__main__":
    main()