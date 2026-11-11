import os
from typing import Any

import requests
import streamlit as st


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

API_BASE_URL = os.getenv(
    "MERCHANTMATE_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

CHAT_URL = f"{API_BASE_URL}/api/chat"
HEALTH_URL = f"{API_BASE_URL}/health"

REQUEST_TIMEOUT = 60


# ---------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="MerchantMate AI",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.20);
            padding: 1rem;
            border-radius: 0.8rem;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------

def empty_conversation_state() -> dict[str, Any]:
    return {
        "pending_invoice": None,
        "requested_field": None,
        "awaiting_confirmation": False,
        "paypal_invoice_id": None,
    }


def initialise_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = (
            empty_conversation_state()
        )

    if "last_response" not in st.session_state:
        st.session_state.last_response = None

    if "business_summary" not in st.session_state:
        st.session_state.business_summary = None

    if "api_error" not in st.session_state:
        st.session_state.api_error = None


initialise_session_state()


# ---------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------

def check_api_health() -> tuple[bool, str]:
    try:
        response = requests.get(
            HEALTH_URL,
            timeout=5,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("status") == "ok":
            return True, "Connected"

        return False, "Unexpected health response"

    except requests.RequestException:
        return False, "Disconnected"

    except ValueError:
        return False, "Invalid API response"


def send_chat_message(
    message: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if state is None:
        state = st.session_state.conversation_state

    payload = {
        "message": message,
        "state": state,
    }

    response = requests.post(
        CHAT_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def apply_response_state(
    result: dict[str, Any],
) -> None:
    new_state = result.get(
        "state"
    )

    if isinstance(
        new_state,
        dict,
    ):
        st.session_state.conversation_state = (
            new_state
        )

    st.session_state.last_response = result


def update_business_summary(
    response: dict[str, Any],
) -> None:
    if (
        response.get("intent") == "business_summary"
        and response.get("status") == "success"
        and isinstance(
            response.get("data"),
            dict,
        )
    ):
        st.session_state.business_summary = (
            response["data"]
        )


def append_assistant_response(
    result: dict[str, Any],
) -> None:
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.get(
                "message",
                "MerchantMate returned no message.",
            ),
            "status": result.get(
                "status"
            ),
            "intent": result.get(
                "intent"
            ),
            "invoice_draft": result.get(
                "invoice_draft"
            ),
            "data": result.get(
                "data"
            ),
            "requires_confirmation": result.get(
                "requires_confirmation",
                False,
            ),
        }
    )


def add_error_message(
    message: str,
) -> None:
    st.session_state.api_error = (
        message
    )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": message,
            "status": "error",
        }
    )


def handle_request_error(
    exc: Exception,
) -> None:
    if isinstance(
        exc,
        requests.Timeout,
    ):
        add_error_message(
            "MerchantMate timed out while waiting for the backend. "
            "Check that FastAPI and Ollama are running."
        )

        return

    if isinstance(
        exc,
        requests.ConnectionError,
    ):
        add_error_message(
            "MerchantMate cannot connect to the FastAPI backend. "
            "Start the backend on port 8000 and try again."
        )

        return

    if isinstance(
        exc,
        requests.HTTPError,
    ):
        status_code = (
            exc.response.status_code
            if exc.response is not None
            else "unknown"
        )

        add_error_message(
            "The MerchantMate API returned an error "
            f"(HTTP {status_code})."
        )

        return

    add_error_message(
        "MerchantMate received an invalid response "
        "from the backend."
    )


def refresh_business_summary() -> bool:
    """
    Refresh dashboard metrics without adding the internal
    business-summary request to the visible chat history.
    """

    try:
        result = send_chat_message(
            "Give me a business summary",
            state=empty_conversation_state(),
        )

        if (
            result.get("status") == "success"
            and result.get("intent")
            == "business_summary"
            and isinstance(
                result.get("data"),
                dict,
            )
        ):
            st.session_state.business_summary = (
                result["data"]
            )

            return True

        return False

    except (
        requests.RequestException,
        ValueError,
    ):
        return False


def process_user_message(
    message: str,
) -> None:
    """
    Process a message typed by the user.

    These messages are displayed in chat history.
    """

    message = message.strip()

    if not message:
        return

    st.session_state.messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    try:
        with st.spinner(
            "MerchantMate is working..."
        ):
            result = send_chat_message(
                message
            )

        st.session_state.api_error = None

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        handle_request_error(
            exc
        )

        return

    apply_response_state(
        result
    )

    append_assistant_response(
        result
    )

    update_business_summary(
        result
    )


def process_confirmation_action(
    action: str,
) -> None:
    """
    Process a UI-generated confirmation or cancellation.

    The raw command is deliberately not displayed as a user
    chat message because it came from a button rather than
    from typed conversation.
    """

    try:
        with st.spinner(
            "Processing invoice..."
        ):
            result = send_chat_message(
                action
            )

        st.session_state.api_error = None

    except (
        requests.RequestException,
        ValueError,
    ) as exc:
        handle_request_error(
            exc
        )

        return

    apply_response_state(
        result
    )

    append_assistant_response(
        result
    )

    if (
        result.get("status") == "confirmed"
        and isinstance(
            result.get("data"),
            dict,
        )
        and result["data"].get(
            "sent"
        )
    ):
        refresh_business_summary()


# ---------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------

def format_currency(
    value: Any,
    currency: str = "AUD",
) -> str:
    try:
        amount = float(
            value
        )

        return (
            f"{currency} "
            f"{amount:,.2f}"
        )

    except (
        TypeError,
        ValueError,
    ):
        return "—"


def get_metric(
    summary: dict[str, Any] | None,
    *keys: str,
) -> Any:
    if not summary:
        return None

    for key in keys:
        if key in summary:
            return summary[key]

    return None


def render_invoice_preview(
    invoice: dict[str, Any],
) -> None:
    customer_name = (
        invoice.get(
            "customer_name"
        )
        or "Not provided"
    )

    customer_email = (
        invoice.get(
            "customer_email"
        )
        or "Not provided"
    )

    description = (
        invoice.get(
            "description"
        )
        or "Not provided"
    )

    currency = (
        invoice.get(
            "currency"
        )
        or "AUD"
    )

    amount = format_currency(
        invoice.get(
            "amount"
        ),
        currency,
    )

    st.markdown(
        "#### Invoice Preview"
    )

    preview = st.container(
        border=True
    )

    with preview:
        left, right = (
            st.columns(2)
        )

        with left:
            st.caption(
                "CUSTOMER"
            )

            st.write(
                customer_name
            )

            st.caption(
                "EMAIL"
            )

            st.write(
                customer_email
            )

        with right:
            st.caption(
                "AMOUNT"
            )

            st.markdown(
                f"### {amount}"
            )

            st.caption(
                "STATUS"
            )

            st.write(
                "Awaiting confirmation"
            )

        st.divider()

        st.caption(
            "DESCRIPTION"
        )

        st.write(
            description
        )

        st.info(
            "This invoice has not been sent. "
            "MerchantMate requires explicit confirmation "
            "before creating or sending anything through PayPal."
        )


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

api_connected, api_status = (
    check_api_health()
)

with st.sidebar:
    st.title(
        "MerchantMate AI"
    )

    st.caption(
        "AI-powered PayPal business assistant"
    )

    st.divider()

    st.subheader(
        "System Status"
    )

    if api_connected:
        st.success(
            f"API: {api_status}"
        )

    else:
        st.error(
            f"API: {api_status}"
        )

    st.info(
        "PayPal Sandbox Mode\n\n"
        "No real money is moved."
    )

    st.caption(
        "AI provider: Ollama"
    )

    st.caption(
        "Model: llama3.2:3b"
    )

    st.divider()

    st.subheader(
        "Try asking"
    )

    st.markdown(
        """
- Create an invoice for Sarah for $250
- Show my outstanding invoices
- How much is outstanding?
- What is my total invoiced amount?
- Who is my top customer?
- Give me a business summary
        """
    )

    st.divider()

    if st.button(
        "New conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []

        st.session_state.conversation_state = (
            empty_conversation_state()
        )

        st.session_state.last_response = None
        st.session_state.api_error = None

        st.rerun()


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

st.title(
    "MerchantMate AI"
)

st.write(
    "Your conversational business assistant for "
    "invoicing, payments and business insights."
)

st.info(
    "PayPal Sandbox — MerchantMate is currently connected "
    "to the PayPal test environment. No real money is moved."
)


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

dashboard_title, dashboard_action = (
    st.columns(
        [4, 1]
    )
)

with dashboard_title:
    st.subheader(
        "Business Snapshot"
    )

with dashboard_action:
    if st.button(
        "Refresh snapshot",
        use_container_width=True,
        disabled=not api_connected,
    ):
        with st.spinner(
            "Refreshing..."
        ):
            refreshed = (
                refresh_business_summary()
            )

        if refreshed:
            st.rerun()

        else:
            st.error(
                "Unable to refresh business data."
            )


summary = (
    st.session_state.business_summary
)

total_invoiced = get_metric(
    summary,
    "total_invoiced",
)

outstanding = get_metric(
    summary,
    "outstanding_amount",
)

paid = get_metric(
    summary,
    "paid_amount",
)

average = get_metric(
    summary,
    "average_invoice_value",
)

metric_1, metric_2, metric_3, metric_4 = (
    st.columns(4)
)

with metric_1:
    st.metric(
        "Total Invoiced",
        format_currency(
            total_invoiced
        ),
    )

with metric_2:
    st.metric(
        "Outstanding",
        format_currency(
            outstanding
        ),
    )

with metric_3:
    st.metric(
        "Paid",
        format_currency(
            paid
        ),
    )

with metric_4:
    st.metric(
        "Average Invoice",
        format_currency(
            average
        ),
    )

if summary is None:
    st.caption(
        "Ask MerchantMate for a business summary "
        "or select Refresh snapshot to load "
        "PayPal Sandbox metrics."
    )


# ---------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------

st.divider()

st.subheader(
    "MerchantMate Chat"
)

if not st.session_state.messages:
    with st.chat_message(
        "assistant"
    ):
        st.markdown(
            """
Hi! I'm **MerchantMate**.

I can help you:

- create PayPal invoices,
- check outstanding payments,
- review invoice activity,
- calculate business metrics,
- identify your top customer.

Try:

**Create an invoice for Sarah for $250.**
            """
        )


for index, message in enumerate(
    st.session_state.messages
):
    role = message.get(
        "role",
        "assistant",
    )

    with st.chat_message(
        role
    ):
        st.markdown(
            message.get(
                "content",
                "",
            )
        )

        invoice_draft = (
            message.get(
                "invoice_draft"
            )
        )

        requires_confirmation = (
            message.get(
                "requires_confirmation",
                False,
            )
        )

        status = message.get(
            "status"
        )

        if (
            invoice_draft
            and requires_confirmation
            and status
            == "confirmation_required"
        ):
            render_invoice_preview(
                invoice_draft
            )

            is_latest_message = (
                index
                == len(
                    st.session_state.messages
                )
                - 1
            )

            awaiting_confirmation = (
                st.session_state
                .conversation_state
                .get(
                    "awaiting_confirmation",
                    False,
                )
            )

            if (
                is_latest_message
                and awaiting_confirmation
            ):
                confirm_col, cancel_col = (
                    st.columns(2)
                )

                with confirm_col:
                    if st.button(
                        "Confirm & Send",
                        type="primary",
                        use_container_width=True,
                        key=(
                            "confirm_invoice_"
                            f"{index}"
                        ),
                    ):
                        process_confirmation_action(
                            "confirm"
                        )

                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        use_container_width=True,
                        key=(
                            "cancel_invoice_"
                            f"{index}"
                        ),
                    ):
                        process_confirmation_action(
                            "cancel"
                        )

                        st.rerun()

        data = message.get(
            "data"
        )

        if (
            status == "confirmed"
            and isinstance(
                data,
                dict,
            )
            and data.get(
                "paypal_invoice_id"
            )
        ):
            st.success(
                "Invoice successfully sent through "
                "PayPal Sandbox."
            )

            st.caption(
                "PayPal Invoice ID"
            )

            st.code(
                str(
                    data[
                        "paypal_invoice_id"
                    ]
                ),
                language=None,
            )

        if (
            status == "error"
            and isinstance(
                data,
                dict,
            )
            and data.get(
                "paypal_invoice_id"
            )
        ):
            st.warning(
                "PayPal created the invoice, but sending "
                "did not complete. MerchantMate retained "
                "the invoice ID so retrying will not "
                "create a duplicate."
            )

            st.caption(
                "PayPal Invoice ID"
            )

            st.code(
                str(
                    data[
                        "paypal_invoice_id"
                    ]
                ),
                language=None,
            )


# ---------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------

if not api_connected:
    st.warning(
        "The FastAPI backend is currently unavailable. "
        "Start it before sending messages."
    )


prompt = st.chat_input(
    "Ask MerchantMate about invoices or your business...",
    disabled=not api_connected,
)

if prompt:
    process_user_message(
        prompt
    )

    st.rerun()


# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------

st.divider()

st.caption(
    "MerchantMate AI • FastAPI • Streamlit • "
    "Ollama • PayPal Sandbox"
)