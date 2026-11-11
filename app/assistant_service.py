import re
from typing import Optional

from app.ai_service import interpret_user_message
from app.analytics import (
    calculate_average_invoice_value,
    calculate_outstanding_amount,
    calculate_paid_amount,
    calculate_total_invoiced,
    get_business_summary,
    get_top_customer,
)
from app.models import (
    AIIntent,
    AssistantResponse,
    InvoiceDraft,
)
from app.paypal_service import (
    get_outstanding_invoices,
    list_invoices,
)


SUPPORTED_CURRENCIES = {
    "AUD",
    "USD",
    "EUR",
    "GBP",
}


def _is_valid_email(email: str) -> bool:
    """
    Perform lightweight application-level email validation.

    This is intentionally independent of the language model.
    """

    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )

    return bool(
        re.fullmatch(
            pattern,
            email.strip(),
        )
    )


def _format_money(
    amount: float,
    currency: str = "AUD",
) -> str:
    """
    Format a financial value consistently for MerchantMate responses.
    """

    return f"{currency} {amount:,.2f}"


def _get_missing_invoice_fields(
    intent: AIIntent,
) -> list[str]:
    """
    Determine which fields are required before MerchantMate can
    prepare an invoice for confirmation.
    """

    missing = []

    if not intent.customer_email:
        missing.append("customer_email")

    if intent.amount is None:
        missing.append("amount")

    if not intent.description:
        missing.append("description")

    return missing


def _missing_fields_message(
    missing_fields: list[str],
) -> str:
    """
    Produce a user-friendly clarification message.
    """

    labels = {
        "customer_email": "customer email address",
        "amount": "invoice amount",
        "description": "invoice description",
    }

    readable = [
        labels[field]
        for field in missing_fields
    ]

    if len(readable) == 1:
        return (
            "I can prepare the invoice, but I still need the "
            f"{readable[0]}."
        )

    if len(readable) == 2:
        fields_text = (
            f"{readable[0]} and {readable[1]}"
        )
    else:
        fields_text = (
            ", ".join(readable[:-1])
            + f", and {readable[-1]}"
        )

    return (
        "I can prepare the invoice, but I still need the "
        f"{fields_text}."
    )


def _handle_create_invoice(
    intent: AIIntent,
) -> AssistantResponse:
    """
    Validate invoice information and prepare a confirmation preview.

    This function NEVER creates a PayPal invoice.
    """

    missing_fields = (
        _get_missing_invoice_fields(
            intent
        )
    )

    if missing_fields:
        return AssistantResponse(
            status="needs_information",
            intent="create_invoice",
            message=_missing_fields_message(
                missing_fields
            ),
            missing_fields=missing_fields,
            requires_confirmation=False,
        )

    if intent.amount is None:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message="The invoice amount is missing.",
        )

    if intent.amount <= 0:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                "The invoice amount must be greater than zero."
            ),
        )

    if not intent.customer_email:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message="A customer email address is required.",
        )

    if not _is_valid_email(
        intent.customer_email
    ):
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                "The customer email address is not valid."
            ),
        )

    currency = (
        intent.currency or "AUD"
    ).upper()

    if currency not in SUPPORTED_CURRENCIES:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                f"{currency} is not currently supported. "
                "MerchantMate currently supports AUD, USD, "
                "EUR, and GBP."
            ),
        )

    if not intent.description:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message="An invoice description is required.",
        )

    draft = InvoiceDraft(
        customer_name=intent.customer_name,
        customer_email=(
            intent.customer_email
        ),
        amount=intent.amount,
        currency=currency,
        description=intent.description,
    )

    customer_display = (
        draft.customer_name
        or draft.customer_email
    )

    message = (
        "Invoice ready for confirmation.\n\n"
        f"Customer: {customer_display}\n"
        f"Email: {draft.customer_email}\n"
        f"Description: {draft.description}\n"
        f"Amount: "
        f"{_format_money(draft.amount, draft.currency)}\n\n"
        "Please confirm before I create and send this invoice."
    )

    return AssistantResponse(
        status="confirmation_required",
        intent="create_invoice",
        message=message,
        invoice_draft=draft,
        requires_confirmation=True,
    )


def _handle_list_invoices() -> AssistantResponse:
    invoices = list_invoices()

    return AssistantResponse(
        status="success",
        intent="list_invoices",
        message=(
            f"I found {len(invoices)} invoice"
            f"{'' if len(invoices) == 1 else 's'}."
        ),
        data=invoices,
    )


def _handle_outstanding_invoices() -> AssistantResponse:
    invoices = get_outstanding_invoices()

    return AssistantResponse(
        status="success",
        intent="outstanding_invoices",
        message=(
            f"You currently have {len(invoices)} outstanding "
            f"invoice{'' if len(invoices) == 1 else 's'}."
        ),
        data=invoices,
    )


def _handle_outstanding_amount() -> AssistantResponse:
    amount = calculate_outstanding_amount()

    return AssistantResponse(
        status="success",
        intent="outstanding_amount",
        message=(
            f"You currently have "
            f"{_format_money(amount)} outstanding."
        ),
        data={
            "amount": amount,
            "currency": "AUD",
        },
    )


def _handle_total_invoiced() -> AssistantResponse:
    amount = calculate_total_invoiced()

    return AssistantResponse(
        status="success",
        intent="total_invoiced",
        message=(
            f"Your total invoiced amount is "
            f"{_format_money(amount)}."
        ),
        data={
            "amount": amount,
            "currency": "AUD",
        },
    )


def _handle_paid_amount() -> AssistantResponse:
    amount = calculate_paid_amount()

    return AssistantResponse(
        status="success",
        intent="paid_amount",
        message=(
            f"You have received "
            f"{_format_money(amount)} in paid invoices."
        ),
        data={
            "amount": amount,
            "currency": "AUD",
        },
    )


def _handle_average_invoice_value() -> AssistantResponse:
    amount = calculate_average_invoice_value()

    return AssistantResponse(
        status="success",
        intent="average_invoice_value",
        message=(
            f"Your average invoice value is "
            f"{_format_money(amount)}."
        ),
        data={
            "amount": amount,
            "currency": "AUD",
        },
    )


def _handle_top_customer() -> AssistantResponse:
    customer = get_top_customer()

    if not customer:
        return AssistantResponse(
            status="success",
            intent="top_customer",
            message=(
                "There is not enough invoice data to identify "
                "a top customer yet."
            ),
            data=None,
        )

    return AssistantResponse(
        status="success",
        intent="top_customer",
        message=(
            f"Your top customer is {customer['customer']} "
            f"with {_format_money(customer['total'])} "
            "in invoice value."
        ),
        data=customer,
    )


def _handle_business_summary() -> AssistantResponse:
    summary = get_business_summary()

    return AssistantResponse(
        status="success",
        intent="business_summary",
        message=(
            "Here is your current MerchantMate business summary."
        ),
        data=summary,
    )


def _handle_help() -> AssistantResponse:
    message = (
        "MerchantMate can help you prepare invoices, view invoices, "
        "check outstanding amounts, review paid revenue, calculate "
        "average invoice value, identify your top customer, and "
        "summarise your invoice activity."
    )

    return AssistantResponse(
        status="success",
        intent="help",
        message=message,
    )


def _handle_unknown() -> AssistantResponse:
    return AssistantResponse(
        status="unsupported",
        intent="unknown",
        message=(
            "I can't perform that request. MerchantMate currently "
            "supports invoice creation and invoice-based business "
            "analytics."
        ),
    )


def process_intent(
    intent: AIIntent,
) -> AssistantResponse:
    """
    Route a validated AIIntent to MerchantMate business logic.

    Keeping this separate from process_message() makes the
    orchestration layer easy to unit test without repeatedly calling
    the language model.
    """

    handlers = {
        "create_invoice": lambda: _handle_create_invoice(
            intent
        ),
        "list_invoices": _handle_list_invoices,
        "outstanding_invoices": (
            _handle_outstanding_invoices
        ),
        "outstanding_amount": (
            _handle_outstanding_amount
        ),
        "total_invoiced": _handle_total_invoiced,
        "paid_amount": _handle_paid_amount,
        "average_invoice_value": (
            _handle_average_invoice_value
        ),
        "top_customer": _handle_top_customer,
        "business_summary": _handle_business_summary,
        "help": _handle_help,
        "unknown": _handle_unknown,
    }

    handler = handlers.get(
        intent.intent
    )

    if handler is None:
        return AssistantResponse(
            status="unsupported",
            intent="unknown",
            message=(
                "MerchantMate could not route that request."
            ),
        )

    try:
        return handler()

    except Exception as exc:
        return AssistantResponse(
            status="error",
            intent=intent.intent,
            message=(
                "MerchantMate could not complete the request: "
                f"{exc}"
            ),
        )


def process_message(
    user_message: str,
) -> AssistantResponse:
    """
    Main MerchantMate entry point.

    Natural language
        -> Ollama understanding
        -> validated AIIntent
        -> deterministic business routing
    """

    try:
        intent = interpret_user_message(
            user_message
        )

        return process_intent(
            intent
        )

    except Exception as exc:
        return AssistantResponse(
            status="error",
            intent="unknown",
            message=(
                "MerchantMate could not understand the request: "
                f"{exc}"
            ),
        )