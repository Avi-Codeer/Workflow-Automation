# Workflow-Automation — AI-Powered SDR Agent

An AI-powered Sales Development Representative (SDR) agent that automates end-to-end outbound sales outreach workflows. It discovers decision-makers at target companies, researches each company, generates personalized cold emails, sends them via Gmail, schedules multi-step follow-ups, and monitors your inbox for replies — all orchestrated through a single pipeline.

---

## Table of Contents

- [Agent Capabilities](#agent-capabilities)
- [Workflow Automation Overview](#workflow-automation-overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup & Configuration](#setup--configuration)
- [Usage](#usage)
- [Current Limitations](#current-limitations)

---

## Agent Capabilities

This agent automates the complete outbound sales outreach lifecycle. Below is what each component is capable of doing:

### 1. Lead Discovery (`lead_agent`)
- Searches for decision-makers (CEO, Founder, VP of HR/Sales, Directors) at target companies using the [Apollo.io](https://www.apollo.io/) API.
- Filters contacts by job title and verified email availability.
- Returns structured lead data: name, title, email, and LinkedIn profile URL.

### 2. Company Research (`research_agent`)
- Uses an LLM (OpenAI GPT-4o-mini) to generate a concise company summary including industry classification and growth signals.
- Provides context that is later used to personalize outreach emails.

### 3. Personalized Email Generation (`email_agent`)
- Generates highly personalized cold emails (80–120 words) using an LLM.
- Incorporates the lead's name, job title, company name, and company research summary.
- Produces a conversational tone with soft calls-to-action; avoids buzzwords and generic templates.

### 4. Follow-Up Management (`followup_agent`)
- Automatically schedules follow-up emails at configurable intervals (default: 3, 7, and 14 days after the initial send).
- Generates unique follow-up emails (40–70 words) with varied tone for each follow-up round.
- Tracks follow-up status (sent/pending) per lead.
- Cancels remaining follow-ups when a positive or negative reply is detected.

### 5. Reply Detection & Classification (`reply_agent`)
- Monitors a Gmail inbox via IMAP for new (unseen) replies.
- Classifies each reply as **positive**, **negative**, or **neutral** using a fast keyword-based heuristic first, then falls back to an LLM for ambiguous cases.
- Triggers automated actions based on classification:
  - **Positive reply** → cancels pending follow-ups and notifies a human for next steps.
  - **Negative reply** → cancels pending follow-ups.

### 6. Email Delivery (`email_service`)
- Sends emails through Gmail SMTP with TLS encryption.
- Implements a token-bucket rate limiter to respect sending limits and avoid spam flags.
- Configurable rate limit (default: 10 emails per minute).

### 7. Pipeline Orchestration (`orchestrator`)
- Coordinates all agents and services into a single automated pipeline.
- Reads target companies from a CSV file and processes each one end-to-end.
- Handles errors gracefully with logging and fallback behavior so that a failure for one company or lead does not stop the entire run.

---

## Workflow Automation Overview

The agent automates the following outreach workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                   CSV Input (companies.csv)                  │
│              List of target company names                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   For Each Company:    │
              └────────────┬───────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼                               ▼
  ┌─────────────────┐            ┌──────────────────┐
  │  Lead Discovery │            │ Company Research  │
  │  (Apollo.io API)│            │ (OpenAI LLM)     │
  └────────┬────────┘            └────────┬─────────┘
           │                              │
           └──────────────┬───────────────┘
                          ▼
              ┌────────────────────────┐
              │   For Each Lead:       │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Generate Personalized  │
              │ Cold Email (LLM)       │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Send Email via Gmail   │
              │ (SMTP, rate-limited)   │
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ Schedule Follow-Ups    │
              │ (Days 3, 7, 14)        │
              └────────────────────────┘

        ─── Recurring Tasks ───

  ┌────────────────────────────────────────┐
  │ Process Due Follow-Ups                 │
  │ Generate & send follow-up emails       │
  └────────────────────────────────────────┘

  ┌────────────────────────────────────────┐
  │ Monitor Inbox for Replies              │
  │ Classify → positive / negative / neutral│
  │ Cancel follow-ups & notify as needed   │
  └────────────────────────────────────────┘
```

**Yes, this agent is designed to automate the outbound sales outreach workflow.** It handles the repetitive, time-consuming steps of lead discovery, research, email personalization, sending, follow-up scheduling, and reply monitoring — allowing sales teams to focus on closing deals rather than manual outreach.

---

## Architecture

The project follows a modular architecture with clear separation of concerns:

| Layer | Directory | Purpose |
|-------|-----------|---------|
| **Agents** | `ai_sdr_agent/agents/` | Business logic for each step (lead discovery, research, email generation, follow-ups, reply handling) |
| **Services** | `ai_sdr_agent/services/` | External API integrations (OpenAI, Apollo.io, Gmail SMTP) |
| **Config** | `ai_sdr_agent/config/` | Centralized settings loaded from environment variables |
| **Manager** | `ai_sdr_agent/manager/` | Pipeline orchestration tying all agents and services together |
| **Data** | `ai_sdr_agent/data/` | Input data (target companies CSV) |

---

## Project Structure

```
Workflow-Automation/
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
├── requirements.txt                # Python dependencies
└── ai_sdr_agent/
    ├── __init__.py
    ├── agents/
    │   ├── __init__.py
    │   ├── lead_agent.py           # Decision-maker discovery via Apollo.io
    │   ├── research_agent.py       # Company research via LLM
    │   ├── email_agent.py          # Personalized email generation via LLM
    │   ├── followup_agent.py       # Follow-up scheduling & generation
    │   └── reply_agent.py          # Inbox monitoring & reply classification
    ├── config/
    │   ├── __init__.py
    │   └── settings.py             # Centralized configuration
    ├── manager/
    │   ├── __init__.py
    │   └── orchestrator.py         # Pipeline coordinator
    ├── services/
    │   ├── __init__.py
    │   ├── openai_service.py       # OpenAI API wrapper
    │   ├── apollo_service.py       # Apollo.io API integration
    │   └── email_service.py        # Gmail SMTP sending with rate limiting
    └── data/
        └── companies.csv           # Target companies input
```

---

## Setup & Configuration

### Prerequisites

- Python 3.10 or higher
- An [OpenAI API key](https://platform.openai.com/api-keys)
- An [Apollo.io API key](https://www.apollo.io/)
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) (required for SMTP and IMAP access)

### Installation

```bash
# Clone the repository
git clone https://github.com/Avi-Codeer/Workflow-Automation.git
cd Workflow-Automation

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your actual API keys and credentials
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | *(required)* |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | LLM temperature (creativity) | `0.7` |
| `APOLLO_API_KEY` | Apollo.io API key for lead search | *(required)* |
| `SMTP_HOST` | SMTP server host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | Gmail address for SMTP auth | *(required)* |
| `SMTP_PASSWORD` | Gmail App Password | *(required)* |
| `SENDER_EMAIL` | "From" address for outgoing emails | *(required)* |
| `EMAIL_RATE_LIMIT` | Max emails sent per minute | `10` |

---

## Usage

1. Add your target companies to `ai_sdr_agent/data/companies.csv` with a `company` column header.
2. Ensure your `.env` file is configured with valid credentials.
3. Run the orchestrator to start the automated outreach pipeline.

The orchestrator will:
- Load companies from the CSV file.
- Discover decision-makers at each company.
- Research each company for personalization context.
- Generate and send personalized cold emails to each lead.
- Schedule follow-up emails at days 3, 7, and 14.
- Monitor the inbox for replies and act accordingly.

---

## Current Limitations

| Limitation | Details |
|------------|---------|
| **In-memory follow-up state** | Scheduled follow-ups are stored in memory and will be lost if the process restarts. No database or persistent storage is used. |
| **Gmail only** | Email sending (SMTP) and inbox monitoring (IMAP) are currently hardcoded for Gmail. |
| **No test suite** | The project does not yet include automated tests. |
| **No retry logic for API calls** | Transient API failures (OpenAI, Apollo.io) are caught and logged but not retried. |
| **No web UI or dashboard** | The agent runs as a command-line process with logging output only. |
