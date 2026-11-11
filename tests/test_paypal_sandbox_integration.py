from app.assistant_service import process_message


def main():
    print("\nMerchantMate PayPal Sandbox Integration Test")
    print("=" * 60)

    customer_email = input(
        "Enter your PayPal Sandbox PERSONAL account email: "
    ).strip()

    if not customer_email:
        print("Cancelled: customer email is required.")
        return

    message = (
        "Create an invoice for Sandbox Customer at "
        f"{customer_email} for $1 AUD for "
        "MerchantMate integration test."
    )

    print("\n1. Preparing invoice...")
    result = process_message(message)

    print(f"Status: {result.status}")
    print(f"Message:\n{result.message}")

    if result.status != "confirmation_required":
        print(
            "\nSTOP: MerchantMate did not reach the "
            "confirmation stage."
        )
        return

    if result.invoice_draft is None:
        print(
            "\nSTOP: No invoice draft was produced."
        )
        return

    print("\n2. Invoice draft")
    print(
        result.invoice_draft.model_dump_json(
            indent=2
        )
    )

    print(
        "\nWARNING: The next step creates and sends a REAL "
        "invoice inside PayPal Sandbox."
    )

    confirmation = input(
        "Type CONFIRM to execute, or anything else to cancel: "
    ).strip()

    if confirmation != "CONFIRM":
        print("\nSandbox test cancelled.")
        return

    print("\n3. Sending through PayPal Sandbox...")

    final_result = process_message(
        "confirm",
        result.state,
    )

    print(
        f"\nStatus: {final_result.status}"
    )

    print(
        f"Message:\n{final_result.message}"
    )

    print(
        f"Data: {final_result.data}"
    )

    if (
        final_result.status == "confirmed"
        and final_result.data
        and final_result.data.get("sent")
    ):
        print("\n" + "=" * 60)
        print(
            "SUCCESS: MerchantMate created and sent "
            "the Sandbox invoice."
        )

        print(
            "PayPal Invoice ID:",
            final_result.data.get(
                "paypal_invoice_id"
            ),
        )

    else:
        print("\n" + "=" * 60)
        print(
            "Sandbox execution did not complete successfully."
        )

        print(
            "Do not retry blindly if an invoice ID was "
            "returned. MerchantMate may already have created "
            "the draft."
        )


if __name__ == "__main__":
    main()