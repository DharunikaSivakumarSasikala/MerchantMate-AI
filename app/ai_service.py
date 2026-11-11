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
that is explicitly present in the CURRENT user's message.

Examples in these instructions are examples only.
NEVER copy names, emails, amounts, currencies, descriptions, or other
values from an example into the current user's request.

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
- copy values from examples
- use "unknown" as a value for a missing field

Missing information MUST be null.


SUPPORTED INTENTS

create_invoice:
The user explicitly wants to create, generate, send, bill, issue,
or charge through an invoice.

Examples:
"Create an invoice for Sarah"
"Invoice Sarah for $300"
"Bill Sarah $300 for consulting"
"Send Sarah an invoice for $300"
"Charge sarah@example.com $300 for consulting"


list_invoices:
The user wants to view invoices generally.


outstanding_invoices:
The user wants to see or list individual unpaid/outstanding invoices
or customers awaiting payment.


outstanding_amount:
The user wants the total amount of money currently owed or outstanding.


total_invoiced:
The user wants the total amount invoiced.


paid_amount:
The user wants the amount of invoice money already paid or received.


average_invoice_value:
The user wants the average invoice amount.


top_customer:
The user wants their highest-value or highest-paying customer.


business_summary:
The user wants an overall business or invoice summary.


help:
The user asks what MerchantMate can do.


unknown:
The request does not match a supported MerchantMate operation.


UNSUPPORTED ACTIONS

MerchantMate does NOT currently support:
- making payments
- paying another person
- refunds
- deleting invoices
- cancelling invoices
- transferring money
- sending money to another person
- withdrawing money

These MUST be classified as unknown.

"Pay Sarah $300"
→ unknown

"Refund John $50"
→ unknown

"Delete all invoices"
→ unknown

"Transfer $100 to John"
→ unknown

"Send $200 to Sarah and call it an invoice"
→ unknown


IMPORTANT DISTINCTION

Sending an invoice TO a customer is supported:

"Send Sarah an invoice for $300"
→ create_invoice

Sending money TO a person is unsupported:

"Send $300 to Sarah"
→ unknown

Adding the words "invoice" or "call it an invoice" does not turn a
money-transfer request into an invoice request.


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
Extract only a customer name explicitly present in the CURRENT message.

Never infer a name from an email address.

"Invoice Sarah"
→ Sarah

"Create an invoice for Emma"
→ Emma

"Invoice customer@example.com $150"
→ customer_name = null

If no explicit customer name exists:
→ null


customer_email:
Extract an email only if the exact email address appears in the
CURRENT user's message.

Never generate, infer, complete, or guess an email address.

If no explicit email exists:
→ null


amount:
Extract the numeric invoice amount only if explicitly present in
the CURRENT user's message.

If no amount exists:
→ null


currency:
If an explicit currency is provided, use its uppercase three-letter
currency code.

If an invoice amount uses "$" without another explicit currency,
use AUD.

If a create_invoice request contains an amount but no explicit currency,
use AUD.

If there is no amount:
→ null


description:
Only use this field for the product, service, work, or reason belonging
to a create_invoice request.

Return the description itself without introductory words such as
"for" or "regarding".

"for maintenance"
→ maintenance

"for website design"
→ website design

For every non-create_invoice intent:
→ null


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

Otherwise:
→ null


CONFIRMATION

create_invoice:
requires_confirmation = true

Every other intent:
requires_confirmation = false


FINAL RULE

Only extract facts from the CURRENT user's message.
Never reuse values from examples.

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
    """
    Extract email addresses literally present in the user's message.
    """

    email_pattern = (
        r"\b[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    return re.findall(
        email_pattern,
        user_message,
    )


def _extract_numbers(
    user_message: str,
) -> list[float]:
    """
    Extract numeric values literally present in the user's message.

    Supports:
    250
    89.50
    1,000
    1,000,000
    -50
    """

    number_pattern = (
        r"(?<!\w)-?\d[\d,]*(?:\.\d+)?"
    )

    numbers = []

    for value in re.findall(
        number_pattern,
        user_message,
    ):
        try:
            numbers.append(
                float(
                    value.replace(",", "")
                )
            )
        except ValueError:
            continue

    return numbers


def _normalise_description(
    description: str | None,
) -> str | None:
    """
    Remove harmless leading words from invoice descriptions.
    """

    description = _clean_optional_text(
        description
    )

    if description is None:
        return None

    cleaned = re.sub(
        r"^(?:for|regarding)\s+(?:the\s+)?",
        "",
        description,
        flags=re.IGNORECASE,
    ).strip()

    return cleaned or None


def _is_send_money_request(
    user_message: str,
) -> bool:
    """
    Detect requests to send money to another person.

    This distinguishes:

    Supported:
        "Send Sarah an invoice for $300"

    Unsupported:
        "Send $300 to Sarah"
        "Send $200 to Sarah and call it an invoice"
    """

    message = user_message.lower()

    money_after_send = re.search(
        (
            r"\bsend\s+"
            r"(?:aud|usd|gbp|eur)?\s*"
            r"\$?\s*"
            r"\d[\d,]*(?:\.\d+)?"
            r"\s+(?:aud|usd|gbp|eur)?"
            r"\s+to\b"
        ),
        message,
        flags=re.IGNORECASE,
    )

    if money_after_send:
        return True

    return False


def _contains_unsupported_action(
    user_message: str,
) -> bool:
    """
    Detect destructive or unsupported money-moving requests.
    """

    if _is_send_money_request(
        user_message
    ):
        return True

    message = user_message.lower()

    for pattern in UNSUPPORTED_ACTION_PATTERNS:
        if re.search(
            pattern,
            message,
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


def _correct_financial_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    """
    Correct high-confidence financial intent distinctions.
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
        r"\bcustomers paid me\b",
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
        if re.search(
            pattern,
            message,
        ):
            result.intent = "paid_amount"
            return result

    for pattern in outstanding_amount_patterns:
        if re.search(
            pattern,
            message,
        ):
            result.intent = (
                "outstanding_amount"
            )
            return result

    return result


def _ground_customer_email(
    result: AIIntent,
    user_message: str,
) -> None:
    """
    Ground the email against the original user message.

    If the user explicitly supplied exactly one email address,
    MerchantMate uses that literal email rather than depending on
    the LLM to reproduce it.
    """

    literal_emails = _extract_emails(
        user_message
    )

    if not literal_emails:
        result.customer_email = None
        return

    if len(literal_emails) == 1:
        result.customer_email = (
            literal_emails[0]
        )
        return

    # Multiple email addresses are ambiguous.
    # Only preserve the model's selection if it exactly matches one
    # of the addresses supplied by the user.
    if result.customer_email:
        matching_email = next(
            (
                email
                for email in literal_emails
                if email.lower()
                == result.customer_email.lower()
            ),
            None,
        )

        result.customer_email = (
            matching_email
        )

    else:
        result.customer_email = None


def _ground_amount(
    result: AIIntent,
    user_message: str,
) -> None:
    """
    Prevent invoice amounts from being invented by the model.
    """

    if result.amount is None:
        return

    literal_numbers = _extract_numbers(
        user_message
    )

    amount_is_present = any(
        abs(
            number - result.amount
        )
        < 0.000001
        for number in literal_numbers
    )

    if not amount_is_present:
        result.amount = None
        result.currency = None


def _ground_customer_name(
    result: AIIntent,
    user_message: str,
) -> None:
    """
    Prevent names from being copied from examples or inferred solely
    from an email address.
    """

    if not result.customer_name:
        return

    name = result.customer_name.strip()

    # Remove emails before checking for a customer name.
    # This prevents:
    #
    # customer@example.com
    #
    # from becoming:
    #
    # customer_name = "customer"
    message_without_emails = re.sub(
        (
            r"\b[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        " ",
        user_message,
    )

    name_pattern = (
        r"(?<!\w)"
        + re.escape(name)
        + r"(?!\w)"
    )

    if not re.search(
        name_pattern,
        message_without_emails,
        flags=re.IGNORECASE,
    ):
        result.customer_name = None


def _ground_description(
    result: AIIntent,
    user_message: str,
) -> None:
    """
    Prevent descriptions from being copied from prompt examples.
    """

    result.description = (
        _normalise_description(
            result.description
        )
    )

    if not result.description:
        return

    if (
        result.description.lower()
        not in user_message.lower()
    ):
        result.description = None


def _normalise_intent(
    result: AIIntent,
    user_message: str,
) -> AIIntent:
    """
    Apply deterministic safety, grounding and consistency rules.
    """

    if _contains_unsupported_action(
        user_message
    ):
        return _unknown_intent()

    result = _correct_financial_intent(
        result,
        user_message,
    )

    result.customer_name = (
        _clean_optional_text(
            result.customer_name
        )
    )

    result.customer_email = (
        _clean_optional_text(
            result.customer_email
        )
    )

    result.period = _clean_optional_text(
        result.period
    )

    if result.currency:
        result.currency = (
            result.currency
            .strip()
            .upper()
        )

        if result.currency.lower() in {
            "unknown",
            "none",
            "null",
            "n/a",
        }:
            result.currency = None

    if result.intent == "create_invoice":
        _ground_customer_email(
            result,
            user_message,
        )

        _ground_customer_name(
            result,
            user_message,
        )

        _ground_amount(
            result,
            user_message,
        )

        _ground_description(
            result,
            user_message,
        )

        if result.amount is None:
            result.currency = None

    else:
        result.customer_name = None
        result.customer_email = None
        result.amount = None
        result.currency = None
        result.description = None

    result.requires_confirmation = (
        result.intent == "create_invoice"
    )

    return result


def interpret_user_message(
    user_message: str,
) -> AIIntent:
    """
    Convert natural language into a validated, grounded and
    safety-checked MerchantMate intent.
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

    # Unsupported operations are rejected before invoking Ollama.
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