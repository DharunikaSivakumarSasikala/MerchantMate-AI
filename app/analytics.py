from collections import Counter, defaultdict
from typing import Any

from app.paypal_service import list_invoices


PAID_STATUSES = {
    "PAID",
    "MARKED_AS_PAID",
}

OUTSTANDING_STATUSES = {
    "SENT",
    "UNPAID",
    "PARTIALLY_PAID",
    "PAYMENT_PENDING",
}


def _get_invoice_amount(invoice: dict[str, Any]) -> float:
    """Extract the invoice amount safely."""

    amount = invoice.get("amount", {})
    value = amount.get("value", "0")

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _get_customer_name(invoice: dict[str, Any]) -> str:
    """Extract the primary customer name safely."""

    recipients = invoice.get("primary_recipients", [])

    if not recipients:
        return "Unknown Customer"

    billing_info = recipients[0].get("billing_info", {})
    name = billing_info.get("name", {})

    given_name = name.get("given_name", "")
    surname = name.get("surname", "")

    full_name = f"{given_name} {surname}".strip()

    if full_name:
        return full_name

    return billing_info.get(
        "email_address",
        "Unknown Customer",
    )


def calculate_total_invoiced() -> float:
    """Calculate total value of all non-draft invoices."""

    invoices = list_invoices()

    total = sum(
        _get_invoice_amount(invoice)
        for invoice in invoices
        if invoice.get("status") != "DRAFT"
    )

    return round(total, 2)


def calculate_outstanding_amount() -> float:
    """Calculate total value of outstanding invoices."""

    invoices = list_invoices()

    total = sum(
        _get_invoice_amount(invoice)
        for invoice in invoices
        if invoice.get("status") in OUTSTANDING_STATUSES
    )

    return round(total, 2)


def calculate_paid_amount() -> float:
    """Calculate total value of paid invoices."""

    invoices = list_invoices()

    total = sum(
        _get_invoice_amount(invoice)
        for invoice in invoices
        if invoice.get("status") in PAID_STATUSES
    )

    return round(total, 2)


def calculate_average_invoice_value() -> float:
    """Calculate average value of non-draft invoices."""

    invoices = [
        invoice
        for invoice in list_invoices()
        if invoice.get("status") != "DRAFT"
    ]

    if not invoices:
        return 0.0

    total = sum(
        _get_invoice_amount(invoice)
        for invoice in invoices
    )

    average = total / len(invoices)

    return round(average, 2)


def get_invoice_status_counts() -> dict[str, int]:
    """Return invoice counts grouped by status."""

    invoices = list_invoices()

    statuses = [
        invoice.get("status", "UNKNOWN")
        for invoice in invoices
    ]

    return dict(Counter(statuses))


def get_top_customer() -> dict[str, Any]:
    """
    Return the customer with the highest total
    value of non-draft invoices.
    """

    invoices = list_invoices()

    customer_totals = defaultdict(float)

    for invoice in invoices:
        if invoice.get("status") == "DRAFT":
            continue

        customer = _get_customer_name(invoice)
        amount = _get_invoice_amount(invoice)

        customer_totals[customer] += amount

    if not customer_totals:
        return {
            "customer": None,
            "total": 0.0,
        }

    customer, total = max(
        customer_totals.items(),
        key=lambda item: item[1],
    )

    return {
        "customer": customer,
        "total": round(total, 2),
    }


def get_business_summary() -> dict[str, Any]:
    """Return a combined business analytics summary."""

    status_counts = get_invoice_status_counts()

    return {
        "total_invoiced": calculate_total_invoiced(),
        "outstanding_amount": calculate_outstanding_amount(),
        "paid_amount": calculate_paid_amount(),
        "average_invoice_value": calculate_average_invoice_value(),
        "status_counts": status_counts,
        "top_customer": get_top_customer(),
    }