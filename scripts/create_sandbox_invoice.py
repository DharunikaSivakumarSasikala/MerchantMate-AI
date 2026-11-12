import os

from dotenv import load_dotenv

from app.paypal_service import create_invoice, send_invoice


def main():
    load_dotenv()

    customer_email = os.getenv("PAYPAL_SANDBOX_CUSTOMER_EMAIL")

    if not customer_email:
        raise RuntimeError(
            "PAYPAL_SANDBOX_CUSTOMER_EMAIL is not configured in .env."
        )

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