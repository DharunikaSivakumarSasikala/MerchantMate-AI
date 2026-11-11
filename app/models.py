from typing import Literal, Optional

from pydantic import BaseModel, Field


IntentType = Literal[
    "create_invoice",
    "list_invoices",
    "outstanding_invoices",
    "outstanding_amount",
    "total_invoiced",
    "paid_amount",
    "average_invoice_value",
    "top_customer",
    "business_summary",
    "help",
    "unknown",
]


class AIIntent(BaseModel):
    """
    Structured representation of a user's MerchantMate request.

    The AI layer is responsible only for understanding the user's request.
    Financial calculations and PayPal operations are handled elsewhere.
    """

    intent: IntentType = Field(
        description="The MerchantMate action requested by the user."
    )

    customer_name: Optional[str] = Field(
        default=None,
        description="Customer name explicitly provided by the user.",
    )

    customer_email: Optional[str] = Field(
        default=None,
        description="Customer email explicitly provided by the user.",
    )

    amount: Optional[float] = Field(
        default=None,
        ge=0,
        description="Invoice amount explicitly provided by the user.",
    )

    currency: Optional[str] = Field(
        default=None,
        description="Three-letter currency code such as AUD or USD.",
    )

    description: Optional[str] = Field(
        default=None,
        description="Description of the product or service being invoiced.",
    )

    period: Optional[str] = Field(
        default=None,
        description=(
            "Time period mentioned by the user, such as today, "
            "this week, this month, or this year."
        ),
    )

    requires_confirmation: bool = Field(
        default=False,
        description="Whether the requested operation changes financial data.",
    )