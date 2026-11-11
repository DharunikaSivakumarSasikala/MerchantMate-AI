from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.assistant_service import process_message
from app.models import (
    AssistantResponse,
    ConversationState,
)


app = FastAPI(
    title="MerchantMate AI API",
    description=(
        "Backend API for MerchantMate AI, a conversational "
        "PayPal-powered small-business assistant."
    ),
    version="1.0.0",
)


# Local development configuration.
#
# Streamlit normally runs on port 8501 while FastAPI runs on 8000.
# Explicit origins are preferable to "*" because this API can trigger
# financial side effects after user confirmation.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
    ],
    allow_headers=[
        "Content-Type",
    ],
)


class ChatRequest(BaseModel):
    """
    One conversational MerchantMate API request.

    Conversation state is supplied by the client rather than stored
    globally on the FastAPI server.
    """

    message: str = Field(
        min_length=1,
        max_length=2000,
    )

    state: Optional[
        ConversationState
    ] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get(
    "/",
    tags=["System"],
)
def root():
    """
    Basic API information endpoint.
    """

    return {
        "service": "MerchantMate AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health():
    """
    Lightweight service health endpoint.

    This deliberately does not call Ollama or PayPal.
    """

    return HealthResponse(
        status="ok",
        service="MerchantMate AI API",
        version="1.0.0",
    )


@app.post(
    "/api/chat",
    response_model=AssistantResponse,
    tags=["MerchantMate"],
)
def chat(
    request: ChatRequest,
) -> AssistantResponse:
    """
    Process one MerchantMate conversation turn.

    The assistant service owns:
    - intent interpretation
    - invoice validation
    - multi-turn invoice collection
    - explicit confirmation
    - PayPal execution
    - analytics routing

    FastAPI only exposes that tested orchestration layer over HTTP.
    """

    return process_message(
        user_message=request.message,
        state=request.state,
    )