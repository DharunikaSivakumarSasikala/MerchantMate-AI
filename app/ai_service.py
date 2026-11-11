import os

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
- fill missing customer details
- use the string "unknown" for missing fields

Missing information MUST be null.


SUPPORTED INTENTS

create_invoice:
The user wants to create, generate, send, bill, or charge using an invoice.

list_invoices:
The user wants to see invoices generally.

outstanding_invoices:
The user wants to see which invoices are unpaid, outstanding, or awaiting payment.

outstanding_amount:
The user asks HOW MUCH MONEY remains unpaid or outstanding.

total_invoiced:
The user asks how much has been invoiced in total.

paid_amount:
The user asks how much invoice money has ALREADY BEEN PAID or received.

average_invoice_value:
The user asks for the average invoice amount/value.

top_customer:
The user asks which customer is highest-paying, highest-value,
best by invoice value, or has spent the most.

business_summary:
The user requests an overall business or invoice summary.

help:
The user asks what MerchantMate can do or asks for help.

unknown:
The request does not match a supported MerchantMate capability.


IMPORTANT INTENT DISTINCTIONS

"Which invoices are outstanding?"
→ outstanding_invoices

"How much money is outstanding?"
→ outstanding_amount

"How much has already been paid?"
→ paid_amount

"How much have I invoiced?"
→ total_invoiced

Do not confuse paid_amount with outstanding_amount.


EXTRACTION RULES

customer_name:
Extract a person's/customer's name when explicitly supplied.

Examples:
"invoice Sarah" → Sarah
"Bill John" → John
"Create an invoice for Emma" → Emma

Do NOT put "unknown" in this field.
If there is no customer name, return null.


customer_email:
Extract an email address only when it literally appears in the message.

Example:
"john@example.com" → john@example.com

Never generate or guess an email address.
If no email is present, return null.


amount:
Extract the numeric amount when explicitly present.

Examples:
"350 AUD" → 350
"$125" → 125
"for $99.50" → 99.50

If no amount is present, return null.


currency:
If AUD, USD, GBP, EUR, etc. is explicitly stated, return that
three-letter uppercase currency code.

MerchantMate is an Australian business application.

If an invoice amount is given using "$" without another currency
being explicitly specified, use AUD.

If an invoice amount is given as a plain number without a currency,
use AUD as MerchantMate's default invoice currency.

If there is no monetary amount, return null.


description:
ONLY use this field for the product, service, work, or reason associated
with a create_invoice request.

Examples:
"for logo design" → logo design
"for website maintenance" → website maintenance
"for consulting services" → consulting services

For analytics, help, invoice listing, and unknown requests,
description MUST be null.

Never use description to answer the user.


period:
Extract a time period only when explicitly present.

Examples include:
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
requires_confirmation MUST be true.

Every other intent:
requires_confirmation MUST be false.


EXAMPLES

User:
Create an invoice for Sarah for 350 AUD for logo design.

Output meaning:
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

Output meaning:
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

Output meaning:
intent = create_invoice
customer_name = Emma
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = true


User:
How much invoice revenue has already been paid?

Output meaning:
intent = paid_amount
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
Who is my highest-paying customer?

Output meaning:
intent = top_customer
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
What can you help me with?

Output meaning:
intent = help
customer_name = null
customer_email = null
amount = null
currency = null
description = null
period = null
requires_confirmation = false


User:
What's the weather in Melbourne?

Output meaning:
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


def _clean_optional_text(value: str | None) -> str | None:
    """
    Normalise optional text returned by the model.
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


def _normalise_intent(result: AIIntent) -> AIIntent:
    """
    Apply deterministic safety and consistency rules after LLM extraction.

    The LLM understands language, while this function enforces
    MerchantMate's application rules.
    """

    result.customer_name = _clean_optional_text(result.customer_name)
    result.customer_email = _clean_optional_text(result.customer_email)
    result.description = _clean_optional_text(result.description)
    result.period = _clean_optional_text(result.period)

    if result.currency:
        result.currency = result.currency.strip().upper()

        if result.currency.lower() in {
            "unknown",
            "none",
            "null",
            "n/a",
        }:
            result.currency = None

    # Only invoice creation should contain invoice-specific information.
    if result.intent != "create_invoice":
        result.customer_name = None
        result.customer_email = None
        result.amount = None
        result.currency = None
        result.description = None

    # Financial actions require confirmation.
    result.requires_confirmation = result.intent == "create_invoice"

    return result


def interpret_user_message(user_message: str) -> AIIntent:
    """
    Convert a natural-language MerchantMate request into a validated,
    normalised AIIntent.
    """

    if not user_message or not user_message.strip():
        raise ValueError("User message cannot be empty.")

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
                    "content": user_message.strip(),
                },
            ],
            format=AIIntent.model_json_schema(),
            options={
                "temperature": 0,
            },
        )

        content = response.message.content

        if not content:
            raise ValueError("Ollama returned an empty response.")

        result = AIIntent.model_validate_json(content)

        return _normalise_intent(result)

    except ResponseError as exc:
        raise RuntimeError(
            f"Ollama model error: {exc}"
        ) from exc

    except ConnectionError as exc:
        raise ConnectionError(
            "Could not connect to Ollama. Make sure Ollama is running."
        ) from exc

    except ValueError:
        raise

    except Exception as exc:
        raise RuntimeError(
            f"Unable to interpret the user request: {exc}"
        ) from exc