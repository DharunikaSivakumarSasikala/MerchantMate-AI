from app.ai_service import interpret_user_message


TEST_CASES = [
    {
        "message": (
            "Create an invoice for Sarah for 350 AUD "
            "for logo design."
        ),
        "expected": {
            "intent": "create_invoice",
            "customer_name": "Sarah",
            "customer_email": None,
            "amount": 350.0,
            "currency": "AUD",
            "description": "logo design",
            "requires_confirmation": True,
        },
    },
    {
        "message": (
            "Bill John at john@example.com $125 "
            "for website maintenance."
        ),
        "expected": {
            "intent": "create_invoice",
            "customer_name": "John",
            "customer_email": "john@example.com",
            "amount": 125.0,
            "currency": "AUD",
            "description": "website maintenance",
            "requires_confirmation": True,
        },
    },
    {
        "message": "Create an invoice for Emma.",
        "expected": {
            "intent": "create_invoice",
            "customer_name": "Emma",
            "customer_email": None,
            "amount": None,
            "currency": None,
            "description": None,
            "requires_confirmation": True,
        },
    },
    {
        "message": "Show me all my invoices.",
        "expected": {
            "intent": "list_invoices",
            "requires_confirmation": False,
        },
    },
    {
        "message": "Which invoices are still outstanding?",
        "expected": {
            "intent": "outstanding_invoices",
            "requires_confirmation": False,
        },
    },
    {
        "message": "How much money am I still waiting to receive?",
        "expected": {
            "intent": "outstanding_amount",
            "requires_confirmation": False,
        },
    },
    {
        "message": "How much have I invoiced in total?",
        "expected": {
            "intent": "total_invoiced",
            "requires_confirmation": False,
        },
    },
    {
        "message": "How much invoice revenue has already been paid?",
        "expected": {
            "intent": "paid_amount",
            "requires_confirmation": False,
        },
    },
    {
        "message": "What is my average invoice value?",
        "expected": {
            "intent": "average_invoice_value",
            "requires_confirmation": False,
        },
    },
    {
        "message": "Who is my highest-paying customer?",
        "expected": {
            "intent": "top_customer",
            "customer_name": None,
            "customer_email": None,
            "requires_confirmation": False,
        },
    },
    {
        "message": "Give me a summary of my business.",
        "expected": {
            "intent": "business_summary",
            "requires_confirmation": False,
        },
    },
    {
        "message": "What can you help me with?",
        "expected": {
            "intent": "help",
            "description": None,
            "requires_confirmation": False,
        },
    },
    {
        "message": "What's the weather in Melbourne?",
        "expected": {
            "intent": "unknown",
            "description": None,
            "requires_confirmation": False,
        },
    },
]


def check_expected(result, expected):
    """
    Compare selected expected fields with the AI result.
    """

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
    print("\nMerchantMate AI Accuracy Tests")
    print("=" * 70)

    passed = 0
    failed = 0

    for number, test_case in enumerate(TEST_CASES, start=1):
        message = test_case["message"]
        expected = test_case["expected"]

        print(f"\nTest {number}")
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

    print("\n" + "=" * 70)
    print("Accuracy Summary")
    print(f"Passed: {passed}/{len(TEST_CASES)}")
    print(f"Failed: {failed}/{len(TEST_CASES)}")

    accuracy = (passed / len(TEST_CASES)) * 100

    print(f"Accuracy: {accuracy:.1f}%")

    if failed == 0:
        print("\nAll MerchantMate AI tests passed.")
    else:
        print(
            "\nSome AI behaviours still need improvement "
            "before this feature is committed."
        )


if __name__ == "__main__":
    main()