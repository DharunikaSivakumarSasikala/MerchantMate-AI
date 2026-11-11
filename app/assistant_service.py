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
    ConversationState,
    InvoiceDraft,
    PendingInvoice,
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


CONFIRMATION_WORDS = {
    "confirm",
    "confirmed",
    "yes",
    "yes confirm",
    "yes, confirm",
    "go ahead",
    "create it",
    "send it",
    "create and send",
}


CANCELLATION_WORDS = {
    "cancel",
    "cancel it",
    "no",
    "no cancel",
    "no, cancel",
    "stop",
    "never mind",
    "nevermind",
}


EMAIL_PATTERN = (
    r"^[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def _normalise_reply(
    message: str,
) -> str:
    """
    Normalise short conversational control replies.
    """

    return " ".join(
        message.lower()
        .strip()
        .rstrip(".!?")
        .split()
    )


def _is_confirmation(
    message: str,
) -> bool:
    return (
        _normalise_reply(message)
        in CONFIRMATION_WORDS
    )


def _is_cancellation(
    message: str,
) -> bool:
    return (
        _normalise_reply(message)
        in CANCELLATION_WORDS
    )


def _is_valid_email(
    email: str,
) -> bool:
    return bool(
        re.fullmatch(
            EMAIL_PATTERN,
            email.strip(),
        )
    )


def _format_money(
    amount: float,
    currency: str = "AUD",
) -> str:
    return f"{currency} {amount:,.2f}"


def _empty_state() -> ConversationState:
    return ConversationState()


def _get_missing_pending_fields(
    invoice: PendingInvoice,
) -> list[str]:
    missing = []

    if not invoice.customer_email:
        missing.append("customer_email")

    if invoice.amount is None:
        missing.append("amount")

    if not invoice.description:
        missing.append("description")

    return missing


def _next_requested_field(
    invoice: PendingInvoice,
) -> Optional[str]:
    """
    Ask for one missing field at a time.

    This makes follow-up messages deterministic instead of asking
    Ollama to guess what a short answer refers to.
    """

    missing = _get_missing_pending_fields(
        invoice
    )

    if not missing:
        return None

    return missing[0]


def _field_question(
    field: str,
    invoice: PendingInvoice,
) -> str:
    customer = (
        invoice.customer_name
        or "the customer"
    )

    if field == "customer_email":
        return (
            f"What email address should I use for {customer}?"
        )

    if field == "amount":
        return (
            "What amount should I invoice?"
        )

    if field == "description":
        return (
            "What is the invoice for?"
        )

    return (
        "Please provide the missing invoice information."
    )


def _intent_to_pending_invoice(
    intent: AIIntent,
) -> PendingInvoice:
    return PendingInvoice(
        customer_name=intent.customer_name,
        customer_email=intent.customer_email,
        amount=intent.amount,
        currency=(
            intent.currency
            if intent.amount is not None
            else None
        ),
        description=intent.description,
    )


def _validate_pending_invoice(
    invoice: PendingInvoice,
) -> Optional[str]:
    """
    Return an error message if collected invoice data is invalid.
    """

    if (
        invoice.amount is not None
        and invoice.amount <= 0
    ):
        return (
            "The invoice amount must be greater than zero."
        )

    if (
        invoice.customer_email
        and not _is_valid_email(
            invoice.customer_email
        )
    ):
        return (
            "The customer email address is not valid."
        )

    if invoice.currency:
        currency = invoice.currency.upper()

        if currency not in SUPPORTED_CURRENCIES:
            return (
                f"{currency} is not currently supported. "
                "MerchantMate currently supports AUD, USD, "
                "EUR, and GBP."
            )

    return None


def _build_invoice_draft(
    invoice: PendingInvoice,
) -> InvoiceDraft:
    """
    Convert a complete pending invoice into an executable draft.
    """

    if not invoice.customer_email:
        raise ValueError(
            "Customer email is required."
        )

    if invoice.amount is None:
        raise ValueError(
            "Invoice amount is required."
        )

    if invoice.amount <= 0:
        raise ValueError(
            "Invoice amount must be greater than zero."
        )

    if not invoice.description:
        raise ValueError(
            "Invoice description is required."
        )

    currency = (
        invoice.currency or "AUD"
    ).upper()

    if currency not in SUPPORTED_CURRENCIES:
        raise ValueError(
            f"Unsupported currency: {currency}"
        )

    if not _is_valid_email(
        invoice.customer_email
    ):
        raise ValueError(
            "Customer email address is invalid."
        )

    return InvoiceDraft(
        customer_name=invoice.customer_name,
        customer_email=invoice.customer_email,
        amount=invoice.amount,
        currency=currency,
        description=invoice.description,
    )


def _invoice_preview_message(
    draft: InvoiceDraft,
) -> str:
    customer_display = (
        draft.customer_name
        or draft.customer_email
    )

    return (
        "Invoice ready for confirmation.\n\n"
        f"Customer: {customer_display}\n"
        f"Email: {draft.customer_email}\n"
        f"Description: {draft.description}\n"
        f"Amount: "
        f"{_format_money(draft.amount, draft.currency)}\n\n"
        "Type 'confirm' to approve this invoice or "
        "'cancel' to discard it."
    )


def _confirmation_response(
    invoice: PendingInvoice,
) -> AssistantResponse:
    """
    Produce the final confirmation preview.

    IMPORTANT:
    This still does NOT call PayPal.
    """

    draft = _build_invoice_draft(
        invoice
    )

    state = ConversationState(
        pending_invoice=invoice,
        requested_field=None,
        awaiting_confirmation=True,
    )

    return AssistantResponse(
        status="confirmation_required",
        intent="create_invoice",
        message=_invoice_preview_message(
            draft
        ),
        invoice_draft=draft,
        requires_confirmation=True,
        state=state,
    )


def _needs_information_response(
    invoice: PendingInvoice,
) -> AssistantResponse:
    field = _next_requested_field(
        invoice
    )

    if field is None:
        return _confirmation_response(
            invoice
        )

    state = ConversationState(
        pending_invoice=invoice,
        requested_field=field,
        awaiting_confirmation=False,
    )

    return AssistantResponse(
        status="needs_information",
        intent="create_invoice",
        message=_field_question(
            field,
            invoice,
        ),
        missing_fields=(
            _get_missing_pending_fields(
                invoice
            )
        ),
        requires_confirmation=False,
        state=state,
    )


def _handle_create_invoice(
    intent: AIIntent,
) -> AssistantResponse:
    invoice = _intent_to_pending_invoice(
        intent
    )

    error = _validate_pending_invoice(
        invoice
    )

    if error:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=error,
            state=_empty_state(),
        )

    missing = _get_missing_pending_fields(
        invoice
    )

    if missing:
        return _needs_information_response(
            invoice
        )

    return _confirmation_response(
        invoice
    )


def _parse_amount_reply(
    message: str,
) -> tuple[
    Optional[float],
    Optional[str],
]:
    """
    Parse an amount supplied specifically in response to an amount
    question.

    Accepted examples:
        350
        $350
        350 AUD
        AUD 350
        450 USD
    """

    cleaned = message.strip()

    patterns = [
        (
            r"^\$\s*"
            r"(-?\d[\d,]*(?:\.\d+)?)"
            r"\s*$"
        ),
        (
            r"^"
            r"(-?\d[\d,]*(?:\.\d+)?)"
            r"\s*(AUD|USD|EUR|GBP)"
            r"\s*$"
        ),
        (
            r"^(AUD|USD|EUR|GBP)"
            r"\s*"
            r"(-?\d[\d,]*(?:\.\d+)?)"
            r"\s*$"
        ),
        (
            r"^"
            r"(-?\d[\d,]*(?:\.\d+)?)"
            r"\s*$"
        ),
    ]

    # $350
    match = re.fullmatch(
        patterns[0],
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            float(
                match.group(1).replace(
                    ",",
                    "",
                )
            ),
            "AUD",
        )

    # 350 AUD
    match = re.fullmatch(
        patterns[1],
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            float(
                match.group(1).replace(
                    ",",
                    "",
                )
            ),
            match.group(2).upper(),
        )

    # AUD 350
    match = re.fullmatch(
        patterns[2],
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            float(
                match.group(2).replace(
                    ",",
                    "",
                )
            ),
            match.group(1).upper(),
        )

    # 350
    match = re.fullmatch(
        patterns[3],
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            float(
                match.group(1).replace(
                    ",",
                    "",
                )
            ),
            "AUD",
        )

    return None, None


def _handle_requested_field(
    user_message: str,
    state: ConversationState,
) -> AssistantResponse:
    invoice = state.pending_invoice

    if invoice is None:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                "There is no pending invoice to update."
            ),
            state=_empty_state(),
        )

    field = state.requested_field

    if field == "customer_email":
        email = user_message.strip()

        if not _is_valid_email(email):
            return AssistantResponse(
                status="needs_information",
                intent="create_invoice",
                message=(
                    "That doesn't look like a valid email "
                    "address. Please enter the customer's "
                    "email address."
                ),
                missing_fields=[
                    "customer_email"
                ],
                state=state,
            )

        invoice.customer_email = email

    elif field == "amount":
        amount, currency = (
            _parse_amount_reply(
                user_message
            )
        )

        if amount is None:
            return AssistantResponse(
                status="needs_information",
                intent="create_invoice",
                message=(
                    "Please enter a valid invoice amount, "
                    "for example 350, $350, or 350 AUD."
                ),
                missing_fields=[
                    "amount"
                ],
                state=state,
            )

        if amount <= 0:
            return AssistantResponse(
                status="needs_information",
                intent="create_invoice",
                message=(
                    "The invoice amount must be greater "
                    "than zero. Please enter a valid amount."
                ),
                missing_fields=[
                    "amount"
                ],
                state=state,
            )

        if (
            currency
            and currency
            not in SUPPORTED_CURRENCIES
        ):
            return AssistantResponse(
                status="needs_information",
                intent="create_invoice",
                message=(
                    "That currency is not supported."
                ),
                missing_fields=[
                    "amount"
                ],
                state=state,
            )

        invoice.amount = amount
        invoice.currency = (
            currency or "AUD"
        )

    elif field == "description":
        description = (
            user_message.strip()
        )

        if not description:
            return AssistantResponse(
                status="needs_information",
                intent="create_invoice",
                message=(
                    "Please provide a description "
                    "for the invoice."
                ),
                missing_fields=[
                    "description"
                ],
                state=state,
            )

        invoice.description = description

    else:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                "MerchantMate could not determine which "
                "invoice field is required."
            ),
            state=_empty_state(),
        )

    error = _validate_pending_invoice(
        invoice
    )

    if error:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=error,
            state=_empty_state(),
        )

    missing = _get_missing_pending_fields(
        invoice
    )

    if missing:
        return _needs_information_response(
            invoice
        )

    return _confirmation_response(
        invoice
    )


def _handle_confirmation_message(
    user_message: str,
    state: ConversationState,
) -> AssistantResponse:
    invoice = state.pending_invoice

    if invoice is None:
        return AssistantResponse(
            status="error",
            intent="create_invoice",
            message=(
                "There is no invoice waiting for confirmation."
            ),
            state=_empty_state(),
        )

    if _is_cancellation(
        user_message
    ):
        return AssistantResponse(
            status="cancelled",
            intent="create_invoice",
            message=(
                "The pending invoice has been cancelled. "
                "Nothing was sent to PayPal."
            ),
            state=_empty_state(),
        )

    if not _is_confirmation(
        user_message
    ):
        draft = _build_invoice_draft(
            invoice
        )

        return AssistantResponse(
            status="confirmation_required",
            intent="create_invoice",
            message=(
                "Please type 'confirm' to approve the "
                "invoice or 'cancel' to discard it."
            ),
            invoice_draft=draft,
            requires_confirmation=True,
            state=state,
        )

    draft = _build_invoice_draft(
        invoice
    )

    # SECURITY BOUNDARY:
    #
    # Step 8A deliberately stops here.
    # PayPal execution will be connected only after this state
    # machine has passed its tests.
    return AssistantResponse(
        status="confirmed",
        intent="create_invoice",
        message=(
            "Invoice confirmation accepted. "
            "PayPal execution is not enabled yet."
        ),
        invoice_draft=draft,
        requires_confirmation=False,
        state=_empty_state(),
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
    return AssistantResponse(
        status="success",
        intent="help",
        message=(
            "MerchantMate can help you prepare invoices, "
            "view invoices, check outstanding amounts, "
            "review paid revenue, calculate average invoice "
            "value, identify your top customer, and summarise "
            "your invoice activity."
        ),
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
        return _handle_unknown()

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
    state: Optional[ConversationState] = None,
) -> AssistantResponse:
    """
    Main conversational MerchantMate entry point.

    State is owned by the caller and returned with every response.
    """

    current_state = (
        state or ConversationState()
    )

    try:
        # Cancellation is allowed at either invoice conversation stage.
        if (
            current_state.pending_invoice
            and _is_cancellation(
                user_message
            )
        ):
            return AssistantResponse(
                status="cancelled",
                intent="create_invoice",
                message=(
                    "The pending invoice has been cancelled. "
                    "Nothing was sent to PayPal."
                ),
                state=_empty_state(),
            )

        if (
            current_state.awaiting_confirmation
        ):
            return _handle_confirmation_message(
                user_message,
                current_state,
            )

        if (
            current_state.pending_invoice
            and current_state.requested_field
        ):
            return _handle_requested_field(
                user_message,
                current_state,
            )

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
            state=current_state,
        )