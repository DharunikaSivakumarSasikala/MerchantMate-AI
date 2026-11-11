import os

import requests
from dotenv import load_dotenv


load_dotenv()

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_BASE_URL = os.getenv(
    "PAYPAL_BASE_URL",
    "https://api-m.sandbox.paypal.com",
)
PAYPAL_BUSINESS_EMAIL = os.getenv("PAYPAL_BUSINESS_EMAIL")


def get_access_token() -> str:
    """Get a PayPal OAuth access token."""

    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise ValueError(
            "PayPal credentials are missing. "
            "Check PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env."
        )

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US",
        },
        data={
            "grant_type": "client_credentials",
        },
        timeout=20,
    )

    if not response.ok:
        print("OAuth status:", response.status_code)
        print("OAuth response:", response.text)

    response.raise_for_status()

    return response.json()["access_token"]


def create_invoice(
    customer_email: str,
    customer_name: str,
    description: str,
    amount: float,
    currency: str = "AUD",
) -> str:
    """Create a draft PayPal invoice."""

    if not PAYPAL_BUSINESS_EMAIL:
        raise ValueError(
            "PAYPAL_BUSINESS_EMAIL is missing. "
            "Add your sandbox business email to .env."
        )

    if amount <= 0:
        raise ValueError("Invoice amount must be greater than zero.")

    token = get_access_token()

    payload = {
        "detail": {
            "currency_code": currency,
            "note": "Thank you for your business.",
        },
        "invoicer": {
            "email_address": PAYPAL_BUSINESS_EMAIL,
            "name": {
                "given_name": "MerchantMate",
                "surname": "AI",
            },
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "email_address": customer_email,
                    "name": {
                        "given_name": customer_name,
                    },
                }
            }
        ],
        "items": [
            {
                "name": description,
                "quantity": "1",
                "unit_amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}",
                },
            }
        ],
    }

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/invoicing/invoices",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    if not response.ok:
        print("PayPal status:", response.status_code)
        print("PayPal response:", response.text)

    response.raise_for_status()

    data = response.json()

    if "id" in data:
        return data["id"]

    if "href" in data:
        return data["href"].rstrip("/").split("/")[-1]

    raise ValueError(
        "PayPal created the invoice but no invoice ID "
        f"could be found in the response: {data}"
    )


def send_invoice(invoice_id: str) -> None:
    """Send a previously created PayPal invoice."""

    if not invoice_id:
        raise ValueError("Invoice ID is required.")

    token = get_access_token()

    payload = {
        "send_to_recipient": True,
        "send_to_invoicer": True,
    }

    response = requests.post(
        f"{PAYPAL_BASE_URL}/v2/invoicing/invoices/{invoice_id}/send",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )

    if not response.ok:
        print("PayPal send status:", response.status_code)
        print("PayPal send response:", response.text)

    response.raise_for_status()


def list_invoices(page: int = 1, page_size: int = 20) -> list:
    """Retrieve invoices from PayPal."""

    token = get_access_token()

    response = requests.get(
        f"{PAYPAL_BASE_URL}/v2/invoicing/invoices",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        params={
            "page": page,
            "page_size": page_size,
            "total_required": "true",
        },
        timeout=20,
    )

    if not response.ok:
        print("PayPal list status:", response.status_code)
        print("PayPal list response:", response.text)

    response.raise_for_status()

    data = response.json()

    return data.get("items", [])


def get_outstanding_invoices() -> list:
    """Return invoices that have not yet been paid."""

    invoices = list_invoices()

    outstanding_statuses = {
        "SENT",
        "UNPAID",
        "PARTIALLY_PAID",
        "PAYMENT_PENDING",
    }

    return [
        invoice
        for invoice in invoices
        if invoice.get("status") in outstanding_statuses
    ]