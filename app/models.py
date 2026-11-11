from typing import Any, Literal, Optional

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


AssistantStatus = Literal[
    "success",
    "needs_information",
    "confirmation_required",
    "confirmed",
    "cancelled",
    "unsupported",
    "error",
]


InvoiceField = Literal[
    "customer_email",
    "amount",
    "description",
]


class AIIntent(BaseModel):
    """
    Structured representation of a user's MerchantMate request.

    The AI layer understands the request.
    Business validation, calculations, confirmation state, and
    PayPal operations are handled elsewhere.
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


class PendingInvoice(BaseModel):
    """
    Invoice information collected across multiple conversation turns.
    """

    customer_name: Optional[str] = None
    customer_email: Optional[str] = None

    amount: Optional[float] = Field(
        default=None,
        ge=0,
    )

    currency: Optional[str] = None
    description: Optional[str] = None


class InvoiceDraft(BaseModel):
    """
    Fully validated invoice ready for explicit user confirmation.
    """

    customer_name: Optional[str] = None
    customer_email: str

    amount: float = Field(
        gt=0
    )

    currency: str
    description: str


class ConversationState(BaseModel):
    """
    MerchantMate state for one active conversation.

    The frontend/API owns this state and passes it back to the
    assistant service on each message.

    paypal_invoice_id is populated immediately after PayPal creates
    the invoice. Keeping this ID allows MerchantMate to retry sending
    the same invoice instead of creating a duplicate.
    """

    pending_invoice: Optional[PendingInvoice] = None

    requested_field: Optional[InvoiceField] = None

    awaiting_confirmation: bool = False

    paypal_invoice_id: Optional[str] = None


class AssistantResponse(BaseModel):
    """
    Standard response from the MerchantMate orchestration layer.
    """

    status: AssistantStatus

    intent: IntentType

    message: str

    data: Optional[Any] = None

    missing_fields: list[str] = Field(
        default_factory=list
    )

    invoice_draft: Optional[InvoiceDraft] = None

    requires_confirmation: bool = False

    state: ConversationState = Field(
        default_factory=ConversationState
    )