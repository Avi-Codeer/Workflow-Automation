"""
Central configuration module.
All environment variables are loaded here using python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
APOLLO_API_KEY: str = os.getenv("APOLLO_API_KEY", "")
# GMAIL_API_KEY is reserved for future use when migrating from SMTP to the
# Gmail REST API (google-auth / googleapiclient). Currently unused.
GMAIL_API_KEY: str = os.getenv("GMAIL_API_KEY", "")

# ---------------------------------------------------------------------------
# Email settings
# ---------------------------------------------------------------------------
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", SMTP_USER)

# Rate-limit: max emails per minute
EMAIL_RATE_LIMIT: int = int(os.getenv("EMAIL_RATE_LIMIT", "10"))

# ---------------------------------------------------------------------------
# OpenAI settings
# ---------------------------------------------------------------------------
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

# ---------------------------------------------------------------------------
# Apollo settings
# ---------------------------------------------------------------------------
APOLLO_BASE_URL: str = "https://api.apollo.io/v1"

# Decision-maker title keywords (case-insensitive match)
DECISION_MAKER_TITLES: list[str] = [
    "ceo",
    "founder",
    "co-founder",
    "head of hr",
    "vp hr",
    "vp of hr",
    "head of sales",
    "vp sales",
    "vp of sales",
    "director",
]

# ---------------------------------------------------------------------------
# Follow-up schedule (days after initial send)
# ---------------------------------------------------------------------------
FOLLOWUP_DAYS: list[int] = [3, 7, 14]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPANIES_CSV: str = os.path.join(BASE_DIR, "data", "companies.csv")
