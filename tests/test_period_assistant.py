from unittest.mock import patch

from app.assistant_service import process_intent
from app.models import AIIntent


@patch(
    "app.assistant_service.calculate_total_invoiced"
)
def test_total_invoiced_receives_period(
    mock_calculate,
):
    mock_calculate.return_value = 500.0

    intent = AIIntent(
        intent="total_invoiced",
        period="this month",
    )

    response = process_intent(
        intent
    )

    mock_calculate.assert_called_once_with(
        period="this month"
    )

    assert response.status == "success"
    assert response.intent == "total_invoiced"
    assert response.data["amount"] == 500.0
    assert response.data["period"] == "this month"
    assert "this month" in response.message.lower()


@patch(
    "app.assistant_service.calculate_outstanding_amount"
)
def test_outstanding_amount_receives_period(
    mock_calculate,
):
    mock_calculate.return_value = 250.0

    intent = AIIntent(
        intent="outstanding_amount",
        period="this week",
    )

    response = process_intent(
        intent
    )

    mock_calculate.assert_called_once_with(
        period="this week"
    )

    assert response.status == "success"
    assert response.data["amount"] == 250.0
    assert response.data["period"] == "this week"
    assert "this week" in response.message.lower()


@patch(
    "app.assistant_service.calculate_paid_amount"
)
def test_paid_amount_receives_period(
    mock_calculate,
):
    mock_calculate.return_value = 800.0

    intent = AIIntent(
        intent="paid_amount",
        period="this year",
    )

    response = process_intent(
        intent
    )

    mock_calculate.assert_called_once_with(
        period="this year"
    )

    assert response.status == "success"
    assert response.data["amount"] == 800.0
    assert response.data["period"] == "this year"
    assert "this year" in response.message.lower()


@patch(
    "app.assistant_service.calculate_average_invoice_value"
)
def test_average_invoice_receives_period(
    mock_calculate,
):
    mock_calculate.return_value = 125.0

    intent = AIIntent(
        intent="average_invoice_value",
        period="last month",
    )

    response = process_intent(
        intent
    )

    mock_calculate.assert_called_once_with(
        period="last month"
    )

    assert response.status == "success"
    assert response.data["amount"] == 125.0
    assert response.data["period"] == "last month"
    assert "last month" in response.message.lower()


@patch(
    "app.assistant_service.get_top_customer"
)
def test_top_customer_receives_period(
    mock_get_top_customer,
):
    mock_get_top_customer.return_value = {
        "customer": "Sarah Lee",
        "total": 900.0,
    }

    intent = AIIntent(
        intent="top_customer",
        period="this month",
    )

    response = process_intent(
        intent
    )

    mock_get_top_customer.assert_called_once_with(
        period="this month"
    )

    assert response.status == "success"
    assert response.data["customer"] == "Sarah Lee"
    assert response.data["total"] == 900.0
    assert response.data["period"] == "this month"
    assert "this month" in response.message.lower()


@patch(
    "app.assistant_service.get_top_customer"
)
def test_top_customer_handles_no_customer(
    mock_get_top_customer,
):
    mock_get_top_customer.return_value = None

    intent = AIIntent(
        intent="top_customer",
        period="last month",
    )

    response = process_intent(
        intent
    )

    mock_get_top_customer.assert_called_once_with(
        period="last month"
    )

    assert response.status == "success"
    assert response.data is None
    assert (
        "not enough invoice data"
        in response.message.lower()
    )
    assert "last month" in response.message.lower()


@patch(
    "app.assistant_service.get_business_summary"
)
def test_business_summary_receives_period(
    mock_summary,
):
    mock_summary.return_value = {
        "period": "this_week",
        "invoice_count": 2,
        "total_invoiced": 600.0,
        "outstanding_amount": 200.0,
        "paid_amount": 400.0,
        "average_invoice_value": 300.0,
        "status_counts": {
            "PAID": 1,
            "SENT": 1,
        },
        "top_customer": {
            "customer": "Sarah Lee",
            "total": 400.0,
        },
    }

    intent = AIIntent(
        intent="business_summary",
        period="this week",
    )

    response = process_intent(
        intent
    )

    mock_summary.assert_called_once_with(
        period="this week"
    )

    assert response.status == "success"
    assert response.data["period"] == "this_week"
    assert response.data["invoice_count"] == 2
    assert "this week" in response.message.lower()


@patch(
    "app.assistant_service.calculate_total_invoiced"
)
def test_no_period_remains_supported(
    mock_calculate,
):
    mock_calculate.return_value = 363.0

    intent = AIIntent(
        intent="total_invoiced",
    )

    response = process_intent(
        intent
    )

    mock_calculate.assert_called_once_with(
        period=None
    )

    assert response.status == "success"
    assert response.data["amount"] == 363.0
    assert response.data["period"] is None
    assert (
        response.message
        == "Your total invoiced amount is AUD 363.00."
    )
