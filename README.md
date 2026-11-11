# MerchantMind AI

MerchantMind AI is an AI-powered business assistant that helps small-business owners manage PayPal-related business tasks using natural language.

Instead of navigating multiple dashboards, users can interact with a conversational assistant to create invoices, view outstanding invoices, analyse revenue, and understand customer payment activity.

## Project Goal

MerchantMind AI aims to simplify everyday payment and invoice management for small businesses by combining:

- Artificial Intelligence for natural-language understanding
- PayPal APIs for invoice and payment operations
- Business analytics for revenue and customer insights

## Core Features

The initial version of MerchantMind AI supports or plans to support:

- Create PayPal invoices using natural-language commands
- Send invoices to customers
- View all invoices
- Identify unpaid or outstanding invoices
- Calculate revenue for selected periods
- Identify highest-paying customers
- Generate business insights from payment and invoice data
- Provide a conversational AI interface for business queries

Example queries:

```text
Create an invoice for Sarah for $350 for logo design.
```

```text
Show me my outstanding invoices.
```

```text
How much revenue did I make this week?
```

```text
Who is my highest-paying customer?
```

## System Architecture

```text
User
  |
  v
Streamlit Frontend
  |
  v
AI / LLM
  |
  v
Intent Detection
  |
  v
FastAPI Backend
  |
  +-------------------+
  |                   |
  v                   v
PayPal Services    Analytics
  |                   |
  +---------+---------+
            |
            v
      PayPal Sandbox
            |
            v
       AI Response
```

## Technology Stack

### Frontend

- Streamlit

### Backend

- Python
- FastAPI
- Uvicorn

### Artificial Intelligence

- OpenAI API
- Structured intent extraction
- Natural-language response generation

### Payments and Invoicing

- PayPal REST APIs
- PayPal Sandbox

### Data and Analytics

- Pandas
- SQLite
- Plotly

### Development Tools

- Git
- GitHub
- VS Code

## Project Structure

```text
merchantmind-ai/
│
├── app/
│   ├── main.py
│   ├── ai_service.py
│   ├── paypal_service.py
│   ├── analytics.py
│   └── models.py
│
├── frontend/
│   └── streamlit_app.py
│
├── data/
│   └── demo_customers.json
│
├── tests/
│
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Application Workflow

A typical request follows this workflow:

```text
User Request
    |
    v
AI interprets the request
    |
    v
Structured intent is generated
    |
    v
Backend selects the required action
    |
    +---------------------------+
    |                           |
    v                           v
PayPal API                  Analytics
    |                           |
    +-------------+-------------+
                  |
                  v
            Result returned
                  |
                  v
       AI formats the response
                  |
                  v
                User
```

For example:

```text
User:
Create an invoice for Sarah for $350 for logo design.
```

The AI converts the request into structured information such as:

```json
{
  "intent": "create_invoice",
  "customer_name": "Sarah",
  "amount": 350,
  "description": "Logo design"
}
```

The backend validates the request and sends the appropriate request to the PayPal API.

## Supported Intents

The MVP is designed around the following core intents:

```text
create_invoice
list_invoices
outstanding_invoices
revenue_summary
top_customer
help
```

Additional capabilities may be added later.

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd merchantmind-ai
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

Use `.env.example` as the template:

```env
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com

OPENAI_API_KEY=
```

Do not commit the real `.env` file or any API credentials to GitHub.

## Running the Application

Start the FastAPI backend:

```bash
uvicorn app.main:app --reload
```

Start the Streamlit frontend:

```bash
streamlit run frontend/streamlit_app.py
```

The exact development workflow may evolve as the project grows.

## PayPal Integration

MerchantMind AI uses the PayPal Sandbox for development and testing.

Planned PayPal capabilities include:

- OAuth authentication
- Invoice creation
- Invoice sending
- Invoice retrieval
- Invoice status tracking
- Invoice reminders

All financial actions should be confirmed by the user before execution.

## AI Integration

The AI layer is responsible for:

- Understanding user requests
- Extracting structured parameters
- Identifying the requested business operation
- Explaining analytics results
- Generating user-friendly responses

The AI is not responsible for calculating or inventing financial values.

Business calculations are performed by deterministic backend functions using available application or PayPal data.

## Security Principles

The project follows basic software security practices:

- API credentials are stored in environment variables
- `.env` is excluded from version control
- Sensitive PayPal credentials are never exposed to the frontend
- Financial actions require explicit confirmation
- Input data is validated before API requests
- Financial calculations are performed in backend logic instead of being generated by the LLM
- No payment card information is stored by MerchantMind AI

## Testing

Automated tests are stored inside:

```text
tests/
```

Testing will cover:

- AI intent parsing
- Request validation
- Analytics calculations
- PayPal service functions
- API endpoints
- Error handling

Tests should use mocked API responses where appropriate rather than depending only on live PayPal Sandbox requests.

## Software Engineering Practices

MerchantMind AI follows good software engineering practices including:

- Separation of concerns
- Modular architecture
- Environment-based configuration
- Secure secret management
- Meaningful Git commits
- Feature-based development
- Input validation
- Error handling
- Unit testing
- Documentation
- Small and reviewable changes

## Git Workflow

Development should use small, meaningful commits.

Example commit messages:

```text
chore: initialise project structure
```

```text
docs: add project documentation
```

```text
feat: add PayPal OAuth authentication
```

```text
feat: implement invoice creation service
```

```text
feat: add AI intent extraction
```

```text
test: add analytics unit tests
```

```text
fix: handle expired PayPal access tokens
```

Avoid unclear commit messages such as:

```text
update
```

```text
changes
```

```text
final
```

```text
working
```

## Branching Strategy

For a small hackathon team, a lightweight feature-branch workflow is recommended.

```text
main
  |
  +-- feature/paypal-integration
  |
  +-- feature/ai-assistant
  |
  +-- feature/dashboard
```

Each feature should be developed on its own branch and merged into `main` once it is working.

The `main` branch should always contain a runnable version of the project.

## Development Plan

### Phase 1 — Project Setup

- Repository structure
- Python environment
- Dependencies
- Environment configuration
- Documentation

### Phase 2 — PayPal Integration

- OAuth authentication
- Invoice creation
- Invoice sending
- Invoice retrieval
- Invoice status handling

### Phase 3 — AI Assistant

- Intent recognition
- Structured output
- Conversation handling
- Action routing

### Phase 4 — Business Analytics

- Revenue calculations
- Outstanding invoice totals
- Customer statistics
- Business insights

### Phase 5 — User Interface

- Dashboard
- Chat interface
- Invoice displays
- Charts

### Phase 6 — Testing and Deployment

- Unit tests
- Error handling
- UI testing
- Deployment
- Demo preparation

## Demo

Demo URL:

```text
Coming soon
```

Demo video:

```text
Coming soon
```

## Team

Developed for the PayPal AI Hackathon.

Team member details will be added before submission.

## License

This project is released under the license included in the `LICENSE` file.

## Disclaimer

MerchantMind AI is a hackathon prototype intended for demonstration and educational purposes.

The application currently uses the PayPal Sandbox and does not process real financial transactions.