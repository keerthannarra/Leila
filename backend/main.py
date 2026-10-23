"""
main.py — FastAPI application entry point for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, SessionLocal, engine
from models import Article, ArticleChunk, User
from services.auth_service import get_password_hash
from services.groq_service import get_embedding
from services.sla_service import check_sla_breaches, get_sla_status
from routers import (
    actions,
    analytics,
    articles,
    audit,
    auth,
    escalations,
    faithfulness,
    guardrails,
    users,
    access_requests,
    chat,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_USERS = [
    {
        "name": "Alice Johnson",
        "email": "alice@company.com",
        "role": "employee",
        "employment_type": "full_time",
    },
    {
        "name": "Bob Chen",
        "email": "bob@company.com",
        "role": "it_content_owner",
        "employment_type": "full_time",
    },
    {
        "name": "Carol Martinez",
        "email": "carol@company.com",
        "role": "it_operations_lead",
        "employment_type": "full_time",
    },
    {
        "name": "Dave Williams",
        "email": "dave@company.com",
        "role": "it_support_agent",
        "employment_type": "full_time",
    },
    {
        "name": "Eve Thompson",
        "email": "eve@company.com",
        "role": "it_operations_manager",
        "employment_type": "full_time",
    },
    {
        "name": "Frank Adams",
        "email": "frank@company.com",
        "role": "administrator",
        "employment_type": "full_time",
    },
]

DEFAULT_SEED_PASSWORD = "Password123!"

SEED_ARTICLES = [
    {
        "title": "Wi-Fi Troubleshooting Guide",
        "category": "Network",
        "context_tags": ["wifi", "network", "internet", "connectivity"],
        "content": (
            "This guide helps employees resolve common Wi-Fi connectivity issues during the hackathon event. "
            "The office network SSID is 'HackathonNet' and the password is distributed at registration. "
            "Ensure your device's Wi-Fi adapter is enabled and not in airplane mode. "
            "If you see the network but cannot connect, try forgetting the network and reconnecting. "
            "For persistent issues, contact IT support at the help desk station near the main entrance."
        ),
        "steps": [
            "Confirm Wi-Fi is turned on and airplane mode is off on your device.",
            "Search for the 'HackathonNet' SSID in your available networks list.",
            "Select 'HackathonNet', enter the password provided at registration, and click Connect.",
            "If connection fails, right-click the network and choose 'Forget', then reconnect from scratch.",
            "If the SSID does not appear, restart your device's Wi-Fi adapter (disable then re-enable).",
            "If still failing, check whether other devices nearby can connect to confirm the network is up.",
            "As a last resort, visit the IT Help Desk kiosk or use the wired Ethernet cable at your workstation.",
        ],
    },
    {
        "title": "Laptop Not Turning On — Diagnosis & Recovery",
        "category": "Hardware",
        "context_tags": ["laptop", "power", "boot", "startup", "black screen"],
        "content": (
            "If your laptop does not power on or shows a black screen at startup, follow this guide. "
            "Most issues are caused by drained batteries, loose power connections, or corrupted boot configurations. "
            "Do not attempt to open the device casing — contact IT for hardware repair. "
            "Bring your equipment tag ID when visiting the IT Help Desk for hardware replacement requests."
        ),
        "steps": [
            "Connect the laptop to its power adapter and ensure the adapter is plugged into a working power outlet.",
            "Hold the power button for 10 seconds to perform a hard reset, then press it once to power on.",
            "Watch for any LED indicators — a charging LED should be orange/amber; a power LED should be white/green.",
            "If no LEDs illuminate, try a different power outlet or swap the charging cable with a known-good one.",
            "If the laptop powers on but shows a black screen, hold Fn + F4 (or Fn + F7) to cycle display output.",
            "If a 'No bootable device' message appears, press F12 at startup to access the boot menu and select your OS drive.",
            "If none of the above steps work, submit a hardware replacement request via the IT portal or visit the Help Desk.",
        ],
    },
    {
        "title": "VPN Access Setup and Troubleshooting",
        "category": "Access & Security",
        "context_tags": ["vpn", "remote access", "cisco", "globalprotect", "tunnel"],
        "content": (
            "The company uses GlobalProtect VPN for secure remote access to internal systems. "
            "VPN access is required to reach internal tools such as Confluence, Jira, and the internal code repositories. "
            "VPN is pre-approved for all full-time employees. Contractors require manager approval before receiving VPN credentials. "
            "Download GlobalProtect from the Software Center or from https://vpn.company.internal/globalprotect. "
            "Contact IT if you receive an authentication error after entering correct credentials."
        ),
        "steps": [
            "Download and install the GlobalProtect VPN client from the Software Center on your managed device.",
            "Open GlobalProtect and enter the portal address: vpn.company.internal.",
            "Log in using your company Single Sign-On (SSO) credentials (same as your email login).",
            "Complete the MFA prompt on your registered mobile device.",
            "Once connected, verify VPN status shows 'Connected' in the GlobalProtect tray icon.",
            "If authentication fails, ensure your SSO password has not expired at accounts.company.internal.",
            "If the portal address cannot be reached, check that you are on the corporate network or a known public network (not a blocked guest Wi-Fi).",
        ],
    },
    {
        "title": "Password Reset Procedures",
        "category": "Account Management",
        "context_tags": ["password", "reset", "locked", "account", "sso", "login"],
        "content": (
            "This article describes the self-service and IT-assisted password reset procedures for company accounts. "
            "Employees can reset their own password at https://accounts.company.internal/reset using their registered mobile number for MFA. "
            "If your account is locked due to multiple failed attempts, it will automatically unlock after 15 minutes, "
            "or IT can unlock it manually. Admin accounts require IT Operations Lead involvement for resets."
        ),
        "steps": [
            "Navigate to https://accounts.company.internal/reset in your browser.",
            "Enter your company email address and click 'Send Reset Code'.",
            "Check your registered mobile number for a one-time SMS code and enter it on the reset page.",
            "Create a new password that meets requirements: minimum 12 characters, at least one uppercase, one number, one special character.",
            "Log in with the new password to confirm the reset was successful.",
            "If you do not receive the SMS, verify your registered phone number with IT or use the backup email code option.",
            "If your account is locked, wait 15 minutes for automatic unlock, or call the IT Help Desk hotline for immediate assistance.",
        ],
    },
    {
        "title": "Software Installation Request Process",
        "category": "Software & Licensing",
        "context_tags": ["software", "install", "license", "request", "application"],
        "content": (
            "All software installations on company-managed devices must go through the approved request process. "
            "Employees cannot install unlicensed or unapproved software on managed devices. "
            "Common approved software is available in the Software Center without a request. "
            "For software not in the Software Center, submit a request through the IT portal. "
            "Standard requests are processed within 2 business days. Urgent requests can be expedited with manager approval. "
            "Open-source tools listed on the approved open-source list can be installed via package managers without a request."
        ),
        "steps": [
            "First check the Software Center on your device (Start Menu → Software Center) to see if the software is already available.",
            "If not in Software Center, visit the IT Portal at https://itportal.company.internal and log in.",
            "Navigate to 'Software Requests' and click 'New Request'.",
            "Fill in the software name, version, business justification, and anticipated number of users.",
            "Submit the request; your manager will receive an approval email automatically.",
            "Once approved, IT will deploy the software to your device via Software Center within 2 business days.",
            "You will receive an email notification when the software is ready to install from Software Center.",
        ],
    },
]


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def seed_data() -> None:
    """Insert sample users and articles if the DB is empty."""
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            # Update any legacy placeholder user hashes for existing seed users.
            updated = False
            for user in db.query(User).filter(User.password_hash == "default_password_hash").all():
                user.password_hash = get_password_hash(DEFAULT_SEED_PASSWORD)
                updated = True
            if updated:
                db.commit()
            return

        print("Seeding database with sample data...")

        # Create users
        user_ids: dict[str, str] = {}
        for u in SEED_USERS:
            user = User(
                id=_new_uuid(),
                name=u["name"],
                email=u["email"],
                password_hash=get_password_hash(DEFAULT_SEED_PASSWORD),
                role=u["role"],
                employment_type=u.get("employment_type"),
                created_at=_utcnow(),
            )
            db.add(user)
            user_ids[u["role"]] = user.id

        db.commit()
        print(f"  Created {len(SEED_USERS)} users.")

        # Determine author and reviewer IDs
        author_id = user_ids.get("it_content_owner", list(user_ids.values())[0])
        reviewer_id = user_ids.get("it_operations_lead", list(user_ids.values())[0])

        # Create articles
        for art_data in SEED_ARTICLES:
            article = Article(
                id=_new_uuid(),
                title=art_data["title"],
                content=art_data["content"],
                steps=json.dumps(art_data["steps"]),
                category=art_data["category"],
                context_tags=json.dumps(art_data["context_tags"]),
                author_id=author_id,
                author_type="human",
                reviewer_id=reviewer_id,
                lifecycle_status="published",
                review_cycle_days=90,
                last_reviewed_date=_utcnow(),
                version=1,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            db.add(article)
            db.commit()
            db.refresh(article)

            # Build full text for chunking
            full_text = f"{article.title}\n\n{article.content}"
            steps_list = art_data["steps"]
            if steps_list:
                full_text += "\n\nTroubleshooting Steps:\n" + "\n".join(
                    f"{i+1}. {s}" for i, s in enumerate(steps_list)
                )

            # Chunk and embed
            raw_chunks = _chunk_text(full_text, chunk_size=500, overlap=50)
            for order, chunk_text in enumerate(raw_chunks):
                emb = get_embedding(chunk_text)
                chunk = ArticleChunk(
                    id=_new_uuid(),
                    article_id=article.id,
                    chunk_text=chunk_text,
                    embedding_json=json.dumps(emb),
                    chunk_order=order,
                    approved_status=True,  # Published articles → approved chunks
                    created_at=_utcnow(),
                )
                db.add(chunk)
            db.commit()

            print(f"  Created article: '{article.title}' ({len(raw_chunks)} chunks)")

        print("Database seeding complete.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield
    # Shutdown (nothing to clean up for SQLite)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Leila IT Help Desk API",
    description=(
        "AI-powered IT Help Desk chatbot backend. "
        "Agent Code: AG-IT-0426-001"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(articles.router, prefix="/api/articles", tags=["Articles"])
app.include_router(escalations.router, prefix="/api/escalations", tags=["escalations"])

@app.get("/jira-test")
def test_jira_connection():
    """Test Jira API connection and return status."""
    try:
        from services.jira_service import test_connection
        result = test_connection()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])

# Access requests and resources share a router; mount at /api
app.include_router(access_requests.router, prefix="/api", tags=["Access Requests"])

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(faithfulness.router, prefix="/api/faithfulness-failures", tags=["Faithfulness"])
app.include_router(guardrails.router, prefix="/api", tags=["Guardrails & Config"])
app.include_router(actions.router, prefix="/api/actions", tags=["Automated Actions"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Leila IT Help Desk API",
        "version": "1.0.0",
    }


@app.get("/api/sla/check", tags=["SLA"])
def check_sla():
    """Manually trigger SLA breach check and send alerts."""
    try:
        alerted_escalations = check_sla_breaches()
        return {
            "success": True,
            "alerted_count": len(alerted_escalations),
            "alerted_escalations": alerted_escalations,
            "message": f"SLA breach alerts sent for {len(alerted_escalations)} escalations"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to check SLA breaches"
        }


@app.get("/api/sla/status", tags=["SLA"])
def sla_status():
    """Get current SLA status summary."""
    try:
        status = get_sla_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get SLA status"
        }
