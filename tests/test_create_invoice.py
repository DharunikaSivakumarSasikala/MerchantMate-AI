from app.paypal_service import create_invoice, send_invoice


def main():
    customer_email = "sb-dq6s353841846@personal.example.com"

    try:
        invoice_id = create_invoice(
            customer_email=customer_email,
            customer_name="Sarah",
            description="Logo Design",
            amount=350.00,
            currency="AUD",
        )

        print("Invoice created successfully.")
        print(f"Invoice ID: {invoice_id}")

        send_invoice(invoice_id)

        print("Invoice sent successfully.")

    except Exception as exc:
        print("Invoice operation failed.")
        print(exc)


if __name__ == "__main__":
    main()