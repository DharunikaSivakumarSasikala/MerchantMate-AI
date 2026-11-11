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

MerchantMate is an AI-powered small-business assistant that works with
PayPal invoice and business data.

Your ONLY task is to classify the user's request and extract information
that is explicitly present in the user's message.

You DO NOT:
- answer the user's question
- create or send invoices
- calculate financial values
- access PayPal
- provide explanations
- invent information
- invent customer names
- invent customer email addresses
- invent invoice amounts
- use "unknown" as a value for a missing field

Missing information MUST be null.


SUPPORTED INTENTS

create_invoice:
The user explicitly wants to CREATE, GENERATE, SEND, BILL, or ISSUE
an INVOICE.

Examples:
"Create an invoice for Sarah"
"Invoice Sarah for $300"
"Bill Sarah $300 for consulting"
"Send Sarah an invoice for $300"


list_invoices:
The user wants to view invoices generally.


outstanding_invoices:
The user wants to SEE or LIST individual unpaid/outstanding invoices
or customers awaiting payment.

Examples:
"Show my unpaid invoices"
"Which invoices are outstanding?"
"Show me everyone I'm waiting on payment from"


outstanding_amount:
The user wants the TOTAL AMOUNT OF MONEY currently owed or outstanding.

Examples:
"How much is outstanding?"
"How much money am I waiting for?"
"How much do customers still owe me?"
"How much do people still owe me?"


total_invoiced:
The user wants the total amount invoiced.

Examples:
"How much have I invoiced?"
"What is my total invoiced amount?"


paid_amount:
The user wants the amount of invoice money already paid or received.

Examples:
"How much has already been paid?"
"Have I been paid anything yet?"
"How much have I been paid this month?"
"How much money have I received?"


average_invoice_value:
The user wants the average invoice amount.

Examples:
"What is my average invoice value?"
"What is the average amount of my invoices?"


top_customer:
The user wants their highest-value or highest-paying customer.

Examples:
"Who is my highest-paying customer?"
"Who spends the most with me?"


business_summary:
The user wants an overall business or invoice summary.

Examples:
"Give me a business summary"
"How is my business doing overall?"


help:
The user asks what MerchantMate can do or requests help.


unknown:
The request does not match a supported MerchantMate operation.


UNSUPPORTED FINANCIAL ACTIONS

MerchantMate does NOT currently support:

- making payments
- paying another person
- refunds
- deleting invoices
- cancelling invoices
- transferring money
- sending money
- withdrawing money

These MUST be classified as unknown.

IMPORTANT:

"Pay Sarah $300"
→ unknown

This means SEND MONEY TO Sarah.
It is NOT an invoice request.

"Refund John $50"
→ unknown

It is NOT an invoice request.

"Delete all invoices"
→ unknown

"Transfer $100 to John"
→ unknown


INTENT DISTINCTIONS

"Which invoices are outstanding?"
→ outstanding_invoices

"Show unpaid invoices"
→ outstanding_invoices

"How much money is outstanding?"
→ outstanding_amount

"How much do people still owe me?"
→ outstanding_amount

"Have I actually been paid anything yet?"
→ paid_amount

"How much have I been paid this month?"
→ paid_amount

"How much has already been paid?"
→ paid_amount

"How much have I invoiced?"
→ total_invoiced


EXTRACTION RULES

customer_name:
Extract only a customer name explicitly present in the message.

Examples:

"Invoice Sarah"
→ Sarah

"Bill John"
→ John

"Create an invoice for Emma"
→ Emma

Never invent a customer name.

Never infer a customer name solely from an email address.

For example:

"Charge alex@example.com $100"
→ customer_name = null
→ customer_email = alex@example.com

If no explicit customer name exists, return null.


customer_email:
Extract an email ONLY if that exact email address literally appears
in the user's message.

Never generate, infer, complete, or guess an email address.

If the message contains:

john@example.com

then customer_email may be:

john@example.com

If the message only says:

John

customer_email MUST be null.


amount:
Extract the numeric invoice amount only when explicitly provided.

Examples:

"$300"
→ 300

"350 AUD"
→ 350

"$99.50"
→ 99.50

Never invent an amount.


currency:
If a currency is explicitly provided, return its uppercase
three-letter currency code.

Examples:

AUD
USD
GBP
EUR

If an invoice amount uses "$" without another explicit currency,
use AUD.

If a create_invoice request contains an amount but no currency,
use AUD because MerchantMate's default business currency is AUD.

If no invoice amount exists, return null.


description:
Only use this field for the product, service, work, or reason belonging
to a create_invoice request.

Examples:

"for logo design"
→ logo design

"for website maintenance"
→ website maintenance

"for tutoring services"
→ tutoring services

For every other intent, description MUST be null.

Never use description to answer the user's question.


period:
Extract a time period only when explicitly present.

Examples:

today
yesterday
this week
last week
this month
last month
this year

Otherwise return null.


CONFIRMATION

create_invoice:
requires_confirmation = true

Every other intent:
requires_confirmation = false


EXAMPLES

User:
Create an invoice for Sarah for 350 AUD for logo design.

Result:
intent = create_invoice
customer_name = Sarah
customer_email = null
amount = 350
currency = AUD
description = logo design
period = null
requires_confirmation = true


User:
Bill John at john@example.com $125 for website maintenance.

Result:
intent = create_invoice
customer_name = John
customer_email = john@example.com
amount = 125
currency = AUD
description = website maintenance
period = null
requires_confirmation = true


User:
Create an invoice for Emma.

Result:
intent = create_invoice
customer_name = Emma
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = true


User:
I need to charge alex@example.com 89.50 for consulting.

Result:
intent = create_invoice
customer_name = null
customer_email = alex@example.com
amount = 89.50
currency = AUD
description = consulting
period = null
requires_confirmation = true


User:
How much do people still owe me?

Result:
intent = outstanding_amount
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
Have I actually been paid anything yet?

Result:
intent = paid_amount
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
How much have I been paid this month?

Result:
intent = paid_amount
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = this month
requires_confirmation = false


User:
Pay Sarah $300.

Result:
intent = unknown
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
Refund John $50.

Result:
intent = unknown
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
Delete all my invoices.

Result:
intent = unknown
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


Return ONLY data matching the supplied schema.
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


def _clean_optional_text(value: str | None) -> str | None:
    """
    Convert empty or placeholder model values into None.
    """

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


def _extract_emails(user_message: str) -> set[str]:
    """
    Return email addresses that literally occur in the user's message.
    """

    email_pattern = (
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    return {
        email.lower()
        for email in re.findall(
            email_pattern,
            user_message,
        )
    }


def _contains_unsupported_action(
    user_message: str,
) -> bool:
    """
    Detect unsupported money-moving or destructive operations.

    These checks create a deterministic safety boundary around
    the language model.
    """

    message = user_message.lower()

    for pattern in UNSUPPORTED_ACTION_PATTERNS:
        if re.search(pattern, message):
            return True

    return False


def _unknown_intent() -> AIIntent:
    """
    Return a clean unsupported MerchantMate request.
    """

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


def _correct_financial_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    """
    Correct high-confidence financial intent distinctions that a
    smaller language model may occasionally confuse.

    This function does not calculate financial values.
    It only maps clearly expressed financial questions to the
    appropriate MerchantMate capability.
    """

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
    ]

    outstanding_amount_patterns = [
        r"\bhow much.*owe me\b",
        r"\bhow much.*owed\b",
        r"\bhow much.*outstanding\b",
        r"\bhow much.*unpaid\b",
        r"\bhow much.*waiting to receive\b",
        r"\bamount outstanding\b",
    ]

    for pattern in paid_patterns:
        if re.search(pattern, message):
            result.intent = "paid_amount"
            return result

    for pattern in outstanding_amount_patterns:
        if re.search(pattern, message):
            result.intent = "outstanding_amount"
            return result

    return result


def _normalise_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    """
    Apply deterministic MerchantMate safety and consistency rules
    after language-model interpretation.
    """

    # Unsupported financial or destructive actions must never
    # reach an execution path.
    if _contains_unsupported_action(user_message):
        return _unknown_intent()

    # Correct financial semantic distinctions that smaller models
    # may occasionally confuse.
    result = _correct_financial_intent(
        result,
        user_message,
    )

    result.customer_name = _clean_optional_text(
        result.customer_name
    )

    result.customer_email = _clean_optional_text(
        result.customer_email
    )

    result.description = _clean_optional_text(
        result.description
    )

    result.period = _clean_optional_text(
        result.period
    )

    # An email returned by the model is valid only if that exact
    # email literally appeared in the user's original message.
    if result.customer_email:
        literal_emails = _extract_emails(
            user_message
        )

        if (
            result.customer_email.lower()
            not in literal_emails
        ):
            result.customer_email = None

    if result.currency:
        result.currency = result.currency.strip().upper()

        if result.currency.lower() in {
            "unknown",
            "none",
            "null",
            "n/a",
        }:
            result.currency = None

    # Invoice-specific information is relevant only when the user
    # actually requested invoice creation.
    if result.intent != "create_invoice":
        result.customer_name = None
        result.customer_email = None
        result.amount = None
        result.currency = None
        result.description = None

    # Confirmation is determined by MerchantMate's application
    # rules rather than trusting the model's decision.
    result.requires_confirmation = (
        result.intent == "create_invoice"
    )

    return result


def interpret_user_message(
    user_message: str,
) -> AIIntent:
    """
    Convert a natural-language MerchantMate request into a
    validated, normalised, and safety-checked AIIntent.

    Args:
        user_message:
            Natural-language message entered by the user.

    Returns:
        A validated AIIntent.

    Raises:
        ValueError:
            If the supplied message is empty or the model response
            cannot be validated.

        ConnectionError:
            If MerchantMate cannot communicate with Ollama.

        RuntimeError:
            If Ollama returns another model-related error.
    """

    if not user_message or not user_message.strip():
        raise ValueError(
            "User message cannot be empty."
        )

    cleaned_message = user_message.strip()

    # Block clearly unsupported financial/destructive operations
    # before invoking the language model.
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
            format=AIIntent.model_json_schema(),
            options={
                "temperature": 0,
            },
        )

        content = response.message.content

        if not content:
            raise ValueError(
                "Ollama returned an empty response."
            )

        result = AIIntent.model_validate_json(
            content
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