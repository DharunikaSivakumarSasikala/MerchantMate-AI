import os
import re

from dotenv import load_dotenv
from ollama import Client, ResponseError

from app.models import AIIntent


load_dotenv()

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:3b",
)

client = Client(host=OLLAMA_BASE_URL)


SYSTEM_PROMPT = """
You are the natural-language understanding component of MerchantMate AI.

Your job is to classify the CURRENT user's request and extract only
information explicitly present in that request.

Never copy values from examples.

SUPPORTED INTENTS:

create_invoice
list_invoices
outstanding_invoices
outstanding_amount
total_invoiced
paid_amount
average_invoice_value
top_customer
business_summary
help
unknown

UNSUPPORTED ACTIONS:

- paying another person
- sending money
- refunds
- deleting invoices
- cancelling invoices
- transferring money
- withdrawing money

Unsupported actions must be classified as unknown.

IMPORTANT DISTINCTIONS:

"Send Sarah an invoice for $300"
→ create_invoice

"Send $300 to Sarah"
→ unknown

"How much have I been paid?"
→ paid_amount

"How much is still unpaid?"
→ outstanding_amount

"Show unpaid invoices"
→ outstanding_invoices

For create_invoice:
- customer_name must be explicitly present
- customer_email must be explicitly present
- amount must be explicitly present
- currency must be explicitly present or inferred as AUD from $
- description must describe the invoiced work/service
- requires_confirmation = true

For every other intent:
requires_confirmation = false

Missing information must be null.

Return only data matching the supplied schema.
"""


UNSUPPORTED_ACTION_PATTERNS = [
    r"\brefund\b",
    r"\bdelete\b",
    r"\bcancel\b",
    r"\btransfer\b",
    r"\bwithdraw\b",
    r"\bsend money\b",
    r"\bpay\s+(?!invoice\b)",
]


EMAIL_PATTERN = (
    r"\b[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def _clean_optional_text(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    if not cleaned:
        return None

    if cleaned.lower() in {
        "unknown",
        "none",
        "null",
        "n/a",
        "not provided",
        "not specified",
    }:
        return None

    return cleaned


def _extract_emails(
    user_message: str,
) -> list[str]:
    return re.findall(
        EMAIL_PATTERN,
        user_message,
    )


def _is_send_money_request(
    user_message: str,
) -> bool:
    """
    Detect:
        Send $200 to Sarah
        Send 200 AUD to Sarah

    But do not block:
        Send Sarah an invoice for $200
    """

    pattern = (
        r"\bsend\s+"
        r"(?:AUD|USD|EUR|GBP)?\s*"
        r"\$?\s*"
        r"-?\d[\d,]*(?:\.\d+)?"
        r"\s*(?:AUD|USD|EUR|GBP)?"
        r"\s+to\b"
    )

    return bool(
        re.search(
            pattern,
            user_message,
            flags=re.IGNORECASE,
        )
    )


def _contains_unsupported_action(
    user_message: str,
) -> bool:
    if _is_send_money_request(
        user_message
    ):
        return True

    for pattern in UNSUPPORTED_ACTION_PATTERNS:
        if re.search(
            pattern,
            user_message,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _unknown_intent() -> AIIntent:
    return AIIntent(
        intent="unknown",
        customer_name=None,
        customer_email=None,
        amount=None,
        currency=None,
        description=None,
        period=None,
        requires_confirmation=False,
    )


def _extract_invoice_amount(
    user_message: str,
) -> float | None:
    """
    Extract a clearly expressed invoice amount.

    Supported:
        $350
        350 AUD
        AUD 350
        450 USD
        0 AUD
        -50 AUD
    """

    patterns = [
        r"\$\s*(-?\d[\d,]*(?:\.\d+)?)",
        (
            r"\b(?:AUD|USD|EUR|GBP)\s+"
            r"(-?\d[\d,]*(?:\.\d+)?)\b"
        ),
        (
            r"(?<![\w.])"
            r"(-?\d[\d,]*(?:\.\d+)?)"
            r"\s+(?:AUD|USD|EUR|GBP)\b"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            user_message,
            flags=re.IGNORECASE,
        )

        if match:
            return float(
                match.group(1).replace(
                    ",",
                    "",
                )
            )

    return None


def _extract_invoice_currency(
    user_message: str,
    amount: float | None,
) -> str | None:
    if amount is None:
        return None

    match = re.search(
        r"\b(AUD|USD|EUR|GBP)\b",
        user_message,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).upper()

    if "$" in user_message:
        return "AUD"

    # MerchantMate's default invoice currency.
    return "AUD"


def _extract_invoice_name(
    user_message: str,
) -> str | None:
    """
    Extract a customer name only from clear invoice grammar.

    Supported examples:
        Create an invoice for Sarah.
        Create an invoice for Sarah
        Create an invoice for John for $50
        Create an invoice for Sarah at sarah@example.com
        Create an invoice for Enterprise Corp for $100
        Invoice David 450 USD
        Invoice Sarah $250
        Bill Robert $400
        Send Sarah an invoice for $300

    Email-only invoice commands deliberately return None.
    """

    # First handle "create an invoice for <name>" while the email
    # is still present. This gives us reliable boundaries for:
    #
    # Create an invoice for Sarah.
    # Create an invoice for Sarah at sarah@example.com.
    # Create an invoice for Sarah for $300.
    #
    create_match = re.search(
        (
            r"\bcreate\s+(?:an?\s+)?invoice\s+for\s+"
            r"(.+?)"
            r"(?="
            r"\s+at\s+"
            + EMAIL_PATTERN
            + r"|"
            r"\s+for\s+(?:\$|-?\d|AUD\b|USD\b|EUR\b|GBP\b)"
            r"|"
            r"\s+(?:\$|-?\d|AUD\b|USD\b|EUR\b|GBP\b)"
            r"|"
            r"[.!?]?\s*$"
            r")"
        ),
        user_message,
        flags=re.IGNORECASE,
    )

    if create_match:
        name = (
            create_match.group(1)
            .strip()
            .rstrip(".!?")
            .strip()
        )

        # An email by itself must never become a customer name.
        if (
            name
            and not re.fullmatch(
                EMAIL_PATTERN,
                name,
                flags=re.IGNORECASE,
            )
        ):
            return name

    # Remove email addresses before processing the remaining
    # supported invoice grammar.
    message_without_email = re.sub(
        EMAIL_PATTERN,
        " ",
        user_message,
    )

    patterns = [
        # Invoice David 450 USD
        # Invoice Sarah $250
        (
            r"^\s*invoice\s+"
            r"(.+?)"
            r"(?=\s+(?:\$|-?\d|AUD\b|USD\b|EUR\b|GBP\b))"
        ),

        # Bill Sarah $300
        (
            r"^\s*bill\s+"
            r"(.+?)"
            r"(?=\s+(?:\$|-?\d|AUD\b|USD\b|EUR\b|GBP\b))"
        ),

        # Send Sarah an invoice for $300
        (
            r"^\s*send\s+"
            r"(.+?)\s+an?\s+invoice\b"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            message_without_email,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        name = (
            match.group(1)
            .strip()
            .rstrip(".!?")
            .strip()
        )

        # Remove trailing "at" left behind after email removal.
        name = re.sub(
            r"\s+at\s*$",
            "",
            name,
            flags=re.IGNORECASE,
        ).strip()

        # Remove trailing "for" where appropriate.
        name = re.sub(
            r"\s+for\s*$",
            "",
            name,
            flags=re.IGNORECASE,
        ).strip()

        if (
            name
            and not re.fullmatch(
                EMAIL_PATTERN,
                name,
                flags=re.IGNORECASE,
            )
        ):
            return name

    return None


def _extract_invoice_description(
    user_message: str,
) -> str | None:
    """
    Extract an explicit invoice description.

    Preferred form:
        monetary amount + "for" + description

    Also supports:
        Create an invoice for Sarah at email@example.com for tutoring

    without confusing the customer's name with the description.
    """

    amount_patterns = [
        # $300 for consulting
        # $300 AUD for consulting
        (
            r"\$\s*-?\d[\d,]*(?:\.\d+)?"
            r"\s*(?:AUD|USD|EUR|GBP)?"
            r"\s+for\s+(.+?)(?:[.!?]\s*)?$"
        ),

        # 300 AUD for consulting
        (
            r"-?\d[\d,]*(?:\.\d+)?"
            r"\s+(?:AUD|USD|EUR|GBP)"
            r"\s+for\s+(.+?)(?:[.!?]\s*)?$"
        ),

        # AUD 300 for consulting
        (
            r"(?:AUD|USD|EUR|GBP)"
            r"\s+-?\d[\d,]*(?:\.\d+)?"
            r"\s+for\s+(.+?)(?:[.!?]\s*)?$"
        ),
    ]

    for pattern in amount_patterns:
        match = re.search(
            pattern,
            user_message,
            flags=re.IGNORECASE,
        )

        if match:
            description = (
                match.group(1).strip()
            )

            if description:
                return description

    # Handles:
    #
    # Create an invoice for Sarah at
    # sarah@example.com for tutoring.
    #
    # Requiring "at <email>" gives us a clear boundary between
    # customer information and invoice description.
    email_description = re.search(
        (
            r"\bat\s+"
            + EMAIL_PATTERN
            + r"\s+for\s+"
            r"(.+?)(?:[.!?]\s*)?$"
        ),
        user_message,
        flags=re.IGNORECASE,
    )

    if email_description:
        description = (
            email_description.group(1)
            .strip()
        )

        if description:
            return description

    return None


def _extract_period(
    user_message: str,
) -> str | None:
    periods = [
        "today",
        "yesterday",
        "this week",
        "last week",
        "this month",
        "last month",
        "this year",
        "last year",
    ]

    message = user_message.lower()

    for period in periods:
        if period in message:
            return period

    return None


def _correct_financial_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    message = user_message.lower()

    paid_patterns = [
        r"\bhave i been paid\b",
        r"\bhave i actually been paid\b",
        r"\bhow much have i been paid\b",
        r"\bhow much has been paid\b",
        r"\balready been paid\b",
        r"\bamount paid\b",
        r"\bmoney received\b",
        r"\bpayment received\b",
        r"\bpayments received\b",
        r"\bcustomers paid me\b",
    ]

    outstanding_patterns = [
        r"\bhow much.*owe me\b",
        r"\bhow much.*owed\b",
        r"\bhow much.*outstanding\b",
        r"\bhow much.*unpaid\b",
        r"\bhow much.*waiting to receive\b",
        r"\bamount outstanding\b",
    ]

    for pattern in paid_patterns:
        if re.search(
            pattern,
            message,
        ):
            result.intent = "paid_amount"
            return result

    for pattern in outstanding_patterns:
        if re.search(
            pattern,
            message,
        ):
            result.intent = (
                "outstanding_amount"
            )
            return result

    return result


def _normalise_invoice(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    """
    Build invoice fields from values explicitly present in the
    current user message.

    Ollama determines that the request is an invoice request.

    Deterministic parsing then protects financial and customer fields
    from hallucination or omission.
    """

    emails = _extract_emails(
        user_message
    )

    if len(emails) == 1:
        result.customer_email = (
            emails[0]
        )

    elif len(emails) == 0:
        result.customer_email = None

    else:
        # Multiple customer emails are ambiguous.
        result.customer_email = None

    result.customer_name = (
        _extract_invoice_name(
            user_message
        )
    )

    amount = _extract_invoice_amount(
        user_message
    )

    # Negative invoice values must never become executable
    # invoice intents.
    if (
        amount is not None
        and amount < 0
    ):
        raise ValueError(
            "Invoice amount cannot be negative."
        )

    result.amount = amount

    result.currency = (
        _extract_invoice_currency(
            user_message,
            amount,
        )
    )

    result.description = (
        _extract_invoice_description(
            user_message
        )
    )

    result.period = _extract_period(
        user_message
    )

    result.requires_confirmation = True

    return result


def _normalise_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    if _contains_unsupported_action(
        user_message
    ):
        return _unknown_intent()

    result = _correct_financial_intent(
        result,
        user_message,
    )

    if result.intent == "create_invoice":
        return _normalise_invoice(
            result,
            user_message,
        )

    # Invoice-specific information must never leak into
    # analytics/help/unknown intents.
    result.customer_name = None
    result.customer_email = None
    result.amount = None
    result.currency = None
    result.description = None

    result.period = _extract_period(
        user_message
    )

    result.requires_confirmation = False

    return result


def interpret_user_message(
    user_message: str,
) -> AIIntent:
    """
    Convert a natural-language MerchantMate request into a validated
    AIIntent.

    Unsupported financial operations are rejected before the request
    reaches Ollama.
    """

    if (
        not user_message
        or not user_message.strip()
    ):
        raise ValueError(
            "User message cannot be empty."
        )

    cleaned_message = (
        user_message.strip()
    )

    # Deterministic safety gate before LLM processing.
    if _contains_unsupported_action(
        cleaned_message
    ):
        return _unknown_intent()

    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": cleaned_message,
                },
            ],
            format=(
                AIIntent.model_json_schema()
            ),
            options={
                "temperature": 0,
            },
        )

        content = (
            response.message.content
        )

        if not content:
            raise ValueError(
                "Ollama returned an empty response."
            )

        result = (
            AIIntent.model_validate_json(
                content
            )
        )

        return _normalise_intent(
            result,
            cleaned_message,
        )

    except ResponseError as exc:
        raise RuntimeError(
            f"Ollama model error: {exc}"
        ) from exc

    except ConnectionError as exc:
        raise ConnectionError(
            "Could not connect to Ollama. "
            "Make sure Ollama is running."
        ) from exc

    except ValueError:
        raise

    except Exception as exc:
        raise RuntimeError(
            "Unable to interpret the user request: "
            f"{exc}"
        ) from exc