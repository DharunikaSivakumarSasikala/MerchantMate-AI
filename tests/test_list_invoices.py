from app.paypal_service import list_invoices


def main():
    try:
        invoices = list_invoices()

        print(f"Total invoices returned: {len(invoices)}")
        print()

        for invoice in invoices:
            detail = invoice.get("detail", {})

            print("Invoice ID:", invoice.get("id"))
            print("Invoice Number:", detail.get("invoice_number"))
            print("Status:", invoice.get("status"))

            amount = invoice.get("amount", {})

            if amount:
                print(
                    "Amount:",
                    amount.get("currency_code"),
                    amount.get("value"),
                )

            print("-" * 40)

    except Exception as exc:
        print("Failed to retrieve invoices.")
        print(exc)


if __name__ == "__main__":
    main()