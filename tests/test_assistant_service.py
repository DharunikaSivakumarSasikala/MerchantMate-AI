from app.assistant_service import process_intent
from app.models import AIIntent


def run_test(
    number,
    name,
    intent,
    expected_status,
    expected_confirmation,
    expected_missing=None,
):
    print(f"\nTest {number}: {name}")

    result = process_intent(intent)

    print(f"Status: {result.status}")
    print(f"Intent: {result.intent}")
    print(f"Message: {result.message}")
    print(
        "Requires confirmation: "
        f"{result.requires_confirmation}"
    )

    if result.missing_fields:
        print(
            f"Missing fields: {result.missing_fields}"
        )

    if result.invoice_draft:
        print(
            "Draft: "
            f"{result.invoice_draft.model_dump()}"
        )

    errors = []

    if result.status != expected_status:
        errors.append(
            f"status expected {expected_status!r}, "
            f"got {result.status!r}"
        )

    if (
        result.requires_confirmation
        != expected_confirmation
    ):
        errors.append(
            "requires_confirmation expected "
            f"{expected_confirmation!r}, got "
            f"{result.requires_confirmation!r}"
        )

    if expected_missing is not None:
        if set(result.missing_fields) != set(
            expected_missing
        ):
            errors.append(
                f"missing_fields expected {expected_missing!r}, "
                f"got {result.missing_fields!r}"
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
        "\nMerchantMate Assistant Service Tests"
    )
    print("=" * 70)

    tests = [
        {
            "name": "Complete invoice",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                amount=350,
                currency="AUD",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "confirmation_required",
            "confirmation": True,
            "missing": [],
        },
        {
            "name": "Missing email",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                amount=350,
                currency="AUD",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "needs_information",
            "confirmation": False,
            "missing": [
                "customer_email",
            ],
        },
        {
            "name": "Missing amount",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "needs_information",
            "confirmation": False,
            "missing": [
                "amount",
            ],
        },
        {
            "name": "Missing description",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                amount=350,
                currency="AUD",
                requires_confirmation=True,
            ),
            "status": "needs_information",
            "confirmation": False,
            "missing": [
                "description",
            ],
        },
        {
            "name": "Multiple missing fields",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                requires_confirmation=True,
            ),
            "status": "needs_information",
            "confirmation": False,
            "missing": [
                "customer_email",
                "amount",
                "description",
            ],
        },
        {
            "name": "Zero amount rejected",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                amount=0,
                currency="AUD",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "error",
            "confirmation": False,
            "missing": [],
        },
        {
            "name": "Invalid email rejected",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="not-an-email",
                amount=350,
                currency="AUD",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "error",
            "confirmation": False,
            "missing": [],
        },
        {
            "name": "Unsupported currency rejected",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                amount=350,
                currency="XYZ",
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "error",
            "confirmation": False,
            "missing": [],
        },
        {
            "name": "Default AUD currency",
            "intent": AIIntent(
                intent="create_invoice",
                customer_name="Sarah",
                customer_email="sarah@example.com",
                amount=350,
                currency=None,
                description="logo design",
                requires_confirmation=True,
            ),
            "status": "confirmation_required",
            "confirmation": True,
            "missing": [],
        },
        {
            "name": "Unknown request",
            "intent": AIIntent(
                intent="unknown",
                requires_confirmation=False,
            ),
            "status": "unsupported",
            "confirmation": False,
            "missing": [],
        },
        {
            "name": "Help request",
            "intent": AIIntent(
                intent="help",
                requires_confirmation=False,
            ),
            "status": "success",
            "confirmation": False,
            "missing": [],
        },
    ]

    passed = 0

    for number, test in enumerate(
        tests,
        start=1,
    ):
        if run_test(
            number=number,
            name=test["name"],
            intent=test["intent"],
            expected_status=test["status"],
            expected_confirmation=(
                test["confirmation"]
            ),
            expected_missing=test["missing"],
        ):
            passed += 1

    total = len(tests)
    failed = total - passed

    print("\n" + "=" * 70)
    print("Assistant Service Summary")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    print(
        f"Accuracy: {(passed / total) * 100:.1f}%"
    )

    if failed == 0:
        print(
            "\nMerchantMate business validation "
            "tests passed."
        )
    else:
        print(
            "\nFix business validation failures "
            "before enabling PayPal execution."
        )


if __name__ == "__main__":
    main()