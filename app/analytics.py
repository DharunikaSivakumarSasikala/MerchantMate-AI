from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

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


# ---------------------------------------------------------------------
# Basic invoice extraction
# ---------------------------------------------------------------------

def _get_invoice_amount(
    invoice: dict[str, Any],
) -> float:
    """Extract the invoice amount safely."""

    amount = invoice.get(
        "amount",
        {},
    )

    value = amount.get(
        "value",
        "0",
    )

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _get_customer_name(
    invoice: dict[str, Any],
) -> str:
    """Extract the primary customer name safely."""

    recipients = invoice.get(
        "primary_recipients",
        [],
    )

    if not recipients:
        return "Unknown Customer"

    billing_info = recipients[0].get(
        "billing_info",
        {},
    )

    name = billing_info.get(
        "name",
        {},
    )

    given_name = name.get(
        "given_name",
        "",
    )

    surname = name.get(
        "surname",
        "",
    )

    full_name = (
        f"{given_name} {surname}"
        .strip()
    )

    if full_name:
        return full_name

    return billing_info.get(
        "email_address",
        "Unknown Customer",
    )


# ---------------------------------------------------------------------
# Date handling
# ---------------------------------------------------------------------

def _parse_date_value(
    value: Any,
) -> Optional[date]:
    """
    Convert common PayPal date/datetime values into a date.

    Supports:
    - YYYY-MM-DD
    - ISO datetime values
    - ISO datetime values ending in Z
    """

    if not value:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    if not isinstance(
        value,
        str,
    ):
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    try:
        return date.fromisoformat(
            cleaned[:10]
        )

    except ValueError:
        pass

    try:
        cleaned_datetime = (
            cleaned.replace(
                "Z",
                "+00:00",
            )
        )

        return (
            datetime.fromisoformat(
                cleaned_datetime
            ).date()
        )

    except ValueError:
        return None


def _get_invoice_date(
    invoice: dict[str, Any],
) -> Optional[date]:
    """
    Extract the most appropriate date from a PayPal invoice.

    PayPal invoice responses may expose the invoice date in
    different locations depending on the endpoint/response shape.
    """

    detail = invoice.get(
        "detail",
        {},
    )

    candidates = [
        detail.get(
            "invoice_date"
        ),
        invoice.get(
            "invoice_date"
        ),
        invoice.get(
            "create_time"
        ),
        invoice.get(
            "update_time"
        ),
    ]

    for candidate in candidates:
        parsed = _parse_date_value(
            candidate
        )

        if parsed is not None:
            return parsed

    return None


# ---------------------------------------------------------------------
# Period handling
# ---------------------------------------------------------------------

def _normalise_period(
    period: Optional[str],
) -> str:
    """Normalise conversational period values."""

    if not period:
        return "all_time"

    cleaned = (
        period.lower()
        .strip()
        .replace(
            "-",
            " ",
        )
        .replace(
            "_",
            " ",
        )
    )

    cleaned = " ".join(
        cleaned.split()
    )

    aliases = {
        "all": "all_time",
        "all time": "all_time",
        "everything": "all_time",
        "today": "today",
        "yesterday": "yesterday",
        "this week": "this_week",
        "current week": "this_week",
        "last week": "last_week",
        "previous week": "last_week",
        "this month": "this_month",
        "current month": "this_month",
        "last month": "last_month",
        "previous month": "last_month",
        "this year": "this_year",
        "current year": "this_year",
    }

    return aliases.get(
        cleaned,
        "all_time",
    )


def _period_bounds(
    period: Optional[str],
    today: Optional[date] = None,
) -> tuple[
    Optional[date],
    Optional[date],
]:
    """
    Return inclusive start/end dates for a supported period.

    Weeks use Monday as the first day.
    """

    current_date = (
        today
        or datetime.now(
            timezone.utc
        ).date()
    )

    normalised = _normalise_period(
        period
    )

    if normalised == "all_time":
        return None, None

    if normalised == "today":
        return (
            current_date,
            current_date,
        )

    if normalised == "yesterday":
        yesterday = (
            current_date
            - timedelta(
                days=1
            )
        )

        return (
            yesterday,
            yesterday,
        )

    if normalised == "this_week":
        start = (
            current_date
            - timedelta(
                days=current_date.weekday()
            )
        )

        return (
            start,
            current_date,
        )

    if normalised == "last_week":
        this_week_start = (
            current_date
            - timedelta(
                days=current_date.weekday()
            )
        )

        end = (
            this_week_start
            - timedelta(
                days=1
            )
        )

        start = (
            end
            - timedelta(
                days=6
            )
        )

        return (
            start,
            end,
        )

    if normalised == "this_month":
        start = current_date.replace(
            day=1
        )

        return (
            start,
            current_date,
        )

    if normalised == "last_month":
        this_month_start = (
            current_date.replace(
                day=1
            )
        )

        end = (
            this_month_start
            - timedelta(
                days=1
            )
        )

        start = end.replace(
            day=1
        )

        return (
            start,
            end,
        )

    if normalised == "this_year":
        start = date(
            current_date.year,
            1,
            1,
        )

        return (
            start,
            current_date,
        )

    return None, None


def filter_invoices_by_period(
    invoices: list[dict[str, Any]],
    period: Optional[str] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """
    Filter invoices to the requested date period.

    All-time requests return every invoice.

    If a period is requested and an invoice has no usable date,
    that invoice is excluded rather than guessed into the period.
    """

    start_date, end_date = (
        _period_bounds(
            period,
            today=today,
        )
    )

    if (
        start_date is None
        and end_date is None
    ):
        return list(
            invoices
        )

    filtered = []

    for invoice in invoices:
        invoice_date = (
            _get_invoice_date(
                invoice
            )
        )

        if invoice_date is None:
            continue

        if (
            start_date
            <= invoice_date
            <= end_date
        ):
            filtered.append(
                invoice
            )

    return filtered


# ---------------------------------------------------------------------
# Analytics operating on an invoice snapshot
# ---------------------------------------------------------------------

def _calculate_total_invoiced(
    invoices: list[dict[str, Any]],
) -> float:
    total = sum(
        _get_invoice_amount(
            invoice
        )
        for invoice in invoices
        if invoice.get(
            "status"
        ) != "DRAFT"
    )

    return round(
        total,
        2,
    )


def _calculate_outstanding_amount(
    invoices: list[dict[str, Any]],
) -> float:
    total = sum(
        _get_invoice_amount(
            invoice
        )
        for invoice in invoices
        if invoice.get(
            "status"
        )
        in OUTSTANDING_STATUSES
    )

    return round(
        total,
        2,
    )


def _calculate_paid_amount(
    invoices: list[dict[str, Any]],
) -> float:
    total = sum(
        _get_invoice_amount(
            invoice
        )
        for invoice in invoices
        if invoice.get(
            "status"
        )
        in PAID_STATUSES
    )

    return round(
        total,
        2,
    )


def _calculate_average_invoice_value(
    invoices: list[dict[str, Any]],
) -> float:
    non_draft_invoices = [
        invoice
        for invoice in invoices
        if invoice.get(
            "status"
        ) != "DRAFT"
    ]

    if not non_draft_invoices:
        return 0.0

    total = sum(
        _get_invoice_amount(
            invoice
        )
        for invoice
        in non_draft_invoices
    )

    average = (
        total
        / len(
            non_draft_invoices
        )
    )

    return round(
        average,
        2,
    )


def _get_invoice_status_counts(
    invoices: list[dict[str, Any]],
) -> dict[str, int]:
    statuses = [
        invoice.get(
            "status",
            "UNKNOWN",
        )
        for invoice in invoices
    ]

    return dict(
        Counter(
            statuses
        )
    )


def _get_top_customer(
    invoices: list[dict[str, Any]],
) -> dict[str, Any]:
    customer_totals = defaultdict(
        float
    )

    for invoice in invoices:
        if invoice.get(
            "status"
        ) == "DRAFT":
            continue

        customer = (
            _get_customer_name(
                invoice
            )
        )

        amount = (
            _get_invoice_amount(
                invoice
            )
        )

        customer_totals[
            customer
        ] += amount

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
        "total": round(
            total,
            2,
        ),
    }


# ---------------------------------------------------------------------
# Public analytics API
# ---------------------------------------------------------------------

def _get_filtered_invoices(
    period: Optional[str] = None,
) -> list[dict[str, Any]]:
    invoices = list_invoices()

    return filter_invoices_by_period(
        invoices,
        period=period,
    )


def calculate_total_invoiced(
    period: Optional[str] = None,
) -> float:
    """Calculate total non-draft invoice value."""

    invoices = _get_filtered_invoices(
        period
    )

    return _calculate_total_invoiced(
        invoices
    )


def calculate_outstanding_amount(
    period: Optional[str] = None,
) -> float:
    """Calculate outstanding invoice value."""

    invoices = _get_filtered_invoices(
        period
    )

    return _calculate_outstanding_amount(
        invoices
    )


def calculate_paid_amount(
    period: Optional[str] = None,
) -> float:
    """Calculate paid invoice value."""

    invoices = _get_filtered_invoices(
        period
    )

    return _calculate_paid_amount(
        invoices
    )


def calculate_average_invoice_value(
    period: Optional[str] = None,
) -> float:
    """Calculate average non-draft invoice value."""

    invoices = _get_filtered_invoices(
        period
    )

    return _calculate_average_invoice_value(
        invoices
    )


def get_invoice_status_counts(
    period: Optional[str] = None,
) -> dict[str, int]:
    """Return invoice counts grouped by status."""

    invoices = _get_filtered_invoices(
        period
    )

    return _get_invoice_status_counts(
        invoices
    )


def get_top_customer(
    period: Optional[str] = None,
) -> dict[str, Any]:
    """Return the top customer for the requested period."""

    invoices = _get_filtered_invoices(
        period
    )

    return _get_top_customer(
        invoices
    )


def get_business_summary(
    period: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return a combined business analytics summary.

    The PayPal invoice list is fetched exactly once so every
    metric is calculated from the same invoice snapshot.
    """

    invoices = list_invoices()

    filtered_invoices = (
        filter_invoices_by_period(
            invoices,
            period=period,
        )
    )

    normalised_period = (
        _normalise_period(
            period
        )
    )

    return {
        "period": normalised_period,
        "invoice_count": len(
            filtered_invoices
        ),
        "total_invoiced": (
            _calculate_total_invoiced(
                filtered_invoices
            )
        ),
        "outstanding_amount": (
            _calculate_outstanding_amount(
                filtered_invoices
            )
        ),
        "paid_amount": (
            _calculate_paid_amount(
                filtered_invoices
            )
        ),
        "average_invoice_value": (
            _calculate_average_invoice_value(
                filtered_invoices
            )
        ),
        "status_counts": (
            _get_invoice_status_counts(
                filtered_invoices
            )
        ),
        "top_customer": (
            _get_top_customer(
                filtered_invoices
            )
        ),
    }