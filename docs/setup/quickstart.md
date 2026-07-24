# 🚀 Quickstart Guide

Get Home Genie running locally in minutes.

---

## Prerequisites

- **Python 3.14+**
- **[`uv`](https://github.com/astral-sh/uv)** package manager
- **Node.js 24+** (for Node-based MCP tools)

---

## Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/rabestro/home-genie.git
cd home-genie

# 2. Install all dependencies (including dev and docs tooling)
uv sync --all-groups

# 3. Create environment configuration
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
GEMINI_API_KEY="AIzaSy..."
FAMILY_USERS='{"123456789": {"name": "Jegors", "paperless_token": "token_abc"}}'
```

---

## Running Quality Checks & Bot

```bash
# Run linters, type checks, and unit tests
mise run format
mise run lint
mise run mypy
mise run test

# Run the Telegram bot locally
mise run run
```
