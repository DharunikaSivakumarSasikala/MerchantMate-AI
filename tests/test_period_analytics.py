from datetime import date
from unittest.mock import patch

from app.analytics import (
    calculate_average_invoice_value,
    calculate_outstanding_amount,
    calculate_paid_amount,
    calculate_total_invoiced,
    filter_invoices_by_period,
    get_business_summary,
    get_top_customer,
)


def make_invoice(
    amount,
    status,
    invoice_date,
    customer="Test Customer",
):
    names = customer.split(
        " ",
        1,
    )

    given_name = names[0]

    surname = (
        names[1]
        if len(names) > 1
        else ""
    )

    return {
        "status": status,
        "amount": {
            "currency_code": "AUD",
            "value": str(
                amount
            ),
        },
        "detail": {
            "invoice_date": (
                invoice_date
            ),
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "name": {
                        "given_name": (
                            given_name
                        ),
                        "surname": (
                            surname
                        ),
                    },
                    "email_address": (
                        "test@example.com"
                    ),
                }
            }
        ],
    }


INVOICES = [
    make_invoice(
        100,
        "PAID",
        "2026-11-11",
        "Sarah Lee",
    ),
    make_invoice(
        200,
        "SENT",
        "2026-11-10",
        "Sarah Lee",
    ),
    make_invoice(
        300,
        "PAID",
        "2026-11-05",
        "Alex Smith",
    ),
    make_invoice(
        400,
        "SENT",
        "2026-10-20",
        "Jordan Brown",
    ),
    make_invoice(
        500,
        "PAID",
        "2025-12-15",
        "Old Customer",
    ),
    make_invoice(
        999,
        "DRAFT",
        "2026-11-11",
        "Draft Customer",
    ),
]


TODAY = date(
    2026,
    11,
    11,
)


def test_today_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="today",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 2


def test_yesterday_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="yesterday",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 1

    assert (
        filtered[0]["amount"]["value"]
        == "200"
    )


def test_this_week_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="this week",
            today=TODAY,
        )
    )

    amounts = {
        invoice["amount"]["value"]
        for invoice in filtered
    }

    assert amounts == {
        "100",
        "200",
        "999",
    }


def test_last_week_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="last week",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 1

    assert (
        filtered[0]["amount"]["value"]
        == "300"
    )


def test_this_month_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="this month",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 4


def test_last_month_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="last month",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 1

    assert (
        filtered[0]["amount"]["value"]
        == "400"
    )


def test_this_year_filter():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="this year",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 5


def test_all_time_returns_everything():
    filtered = (
        filter_invoices_by_period(
            INVOICES,
            period="all time",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == len(
        INVOICES
    )


@patch(
    "app.analytics.list_invoices"
)
def test_existing_analytics_remain_compatible(
    mock_list,
):
    mock_list.return_value = INVOICES

    assert (
        calculate_total_invoiced()
        == 1500.0
    )

    assert (
        calculate_outstanding_amount()
        == 600.0
    )

    assert (
        calculate_paid_amount()
        == 900.0
    )

    assert (
        calculate_average_invoice_value()
        == 300.0
    )


@patch(
    "app.analytics.list_invoices"
)
def test_top_customer(
    mock_list,
):
    mock_list.return_value = INVOICES

    result = get_top_customer()

    assert (
        result["customer"]
        == "Old Customer"
    )

    assert (
        result["total"]
        == 500.0
    )


@patch(
    "app.analytics.list_invoices"
)
def test_summary_fetches_paypal_once(
    mock_list,
):
    mock_list.return_value = INVOICES

    summary = (
        get_business_summary()
    )

    assert (
        mock_list.call_count
        == 1
    )

    assert (
        summary["total_invoiced"]
        == 1500.0
    )

    assert (
        summary["outstanding_amount"]
        == 600.0
    )

    assert (
        summary["paid_amount"]
        == 900.0
    )

    assert (
        summary[
            "average_invoice_value"
        ]
        == 300.0
    )

    assert (
        summary["invoice_count"]
        == 6
    )

    assert (
        summary["period"]
        == "all_time"
    )


def test_missing_date_not_guessed_into_period():
    invoices = [
        {
            "status": "PAID",
            "amount": {
                "value": "100"
            },
        }
    ]

    filtered = (
        filter_invoices_by_period(
            invoices,
            period="today",
            today=TODAY,
        )
    )

    assert filtered == []


def test_missing_date_preserved_for_all_time():
    invoices = [
        {
            "status": "PAID",
            "amount": {
                "value": "100"
            },
        }
    ]

    filtered = (
        filter_invoices_by_period(
            invoices,
            period="all time",
            today=TODAY,
        )
    )

    assert len(
        filtered
    ) == 1