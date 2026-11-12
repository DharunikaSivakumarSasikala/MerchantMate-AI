from app.paypal_service import get_outstanding_invoices


def main():
    try:
        invoices = get_outstanding_invoices()

        print(f"Outstanding invoices: {len(invoices)}")
        print()

        for invoice in invoices:
            detail = invoice.get("detail", {})
            amount = invoice.get("amount", {})

            print("Invoice ID:", invoice.get("id"))
            print("Invoice Number:", detail.get("invoice_number"))
            print("Status:", invoice.get("status"))
            print(
                "Amount:",
                amount.get("currency_code"),
                amount.get("value"),
            )
            print("-" * 40)

    except Exception as exc:
        print("Failed to retrieve outstanding invoices.")
        print(exc)


if __name__ == "__main__":
    main()