# Leila IT Help Desk

Leila is an AI-powered IT help desk application. Employees can ask questions about IT support and track conversations, while IT teams manage knowledge articles, escalations, access requests, and operational workflows.

## Features

- AI-assisted IT support chat with conversation history, step-by-step troubleshooting, and feedback.
- Searchable knowledge articles with review, approval, and lifecycle management.
- Escalation tracking, SLA status checks, and optional Jira issue synchronization.
- Access request and resource catalogue management.
- Role-based administration for analytics, audit logs, guardrails, automated actions, and user management.
- JWT-based authentication and a local SQLite database by default.

## Technology

- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite by default; an alternate SQLAlchemy database URL can be configured.
- **AI:** Groq chat completion API; knowledge article embeddings are generated locally.
- **Integrations:** Jira and SMTP email notifications are configurable.

## Requirements

- Python and pip
- Node.js and npm
- A Groq API key for AI chat
- Optional: Jira credentials and SMTP settings for those integrations

## Setup

### 1. Configure the backend

From the repository root, create and activate a virtual environment, then install the backend requirements:

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Create `backend/.env` and add your Groq API key:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

The backend also reads the following optional settings:

| Variable | Purpose | Default |
| --- | --- | --- |
| `GROQ_MODEL` | Groq chat model | `llama-3.1-8b-instant` |
| `GROQ_BASE_URL` | Groq-compatible API base URL | `https://api.groq.com/openai/v1` |
| `DATABASE_URL` | SQLAlchemy database connection URL | `sqlite:///./leila.db` |
| `SECRET_KEY` | JWT signing key; set a unique, strong value outside local demos | `your-secret-key-change-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes | `43200` |
| `JIRA_URL` | Jira site URL | unset |
| `JIRA_USERNAME` | Jira account username/email | unset |
| `JIRA_API_TOKEN` | Jira API token | unset |
| `JIRA_PROJECT_KEY` | Jira project for created issues | `IT` |
| `SMTP_SERVER` / `SMTP_PORT` | SMTP host and port | `smtp.gmail.com` / `587` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | SMTP credentials | unset |
| `SMTP_FROM_EMAIL` | Sender address for notifications | `leila.helpdesk@example.com` |

Keep `.env` files and API credentials private. The default JWT key and demo accounts are for local development only.

### 2. Start the backend

From the repository root:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

On first startup, the service creates the database tables and seeds sample users and knowledge articles if the database is empty. The default database file is `backend/leila.db` when launched from the `backend` directory.

### 3. Start the frontend

In a separate terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite development server proxies `/api` and `/health` requests to the backend at `http://localhost:8000`.

## Demo login accounts

The initial database seed creates these role accounts. They all use the same demo password:

| Role | Email |
| --- | --- |
| Employee | `alice@company.com` |
| IT content owner | `bob@company.com` |
| IT operations lead | `carol@company.com` |
| IT support agent | `dave@company.com` |
| IT operations manager | `eve@company.com` |
| Administrator | `frank@company.com` |

**Demo password:** `Password123!`

These credentials are publicly known and must not be used in a deployed environment. The seed only creates these users when the database has no users.

## API and database

- Interactive API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- Main API routes are grouped under `/api` for chat, authentication, articles, escalations, analytics, audit, users, access requests, resources, guardrails, configuration, faithfulness review, and automated actions.
- To use another database, set `DATABASE_URL` in `backend/.env` to a supported SQLAlchemy URL.

## Production notes

The development server and default configuration are intended for local use. Before deployment, configure a strong `SECRET_KEY`, replace or remove demo accounts and sample content, restrict CORS to trusted origins, and provide secure database and integration credentials.

---

Open to contributions.

Created by [Keerthan Narra](https://github.com/keerthannarra).

---
