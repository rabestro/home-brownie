# 🤎 Home Brownie (`home-brownie`)

[![CI](https://github.com/rabestro/home-brownie/actions/workflows/ci.yaml/badge.svg)](https://github.com/rabestro/home-brownie/actions/workflows/ci.yaml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=rabestro_home-genie&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=rabestro_home-genie)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=rabestro_home-genie&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=rabestro_home-genie)
[![Docs](https://img.shields.io/badge/docs-site-indigo.svg)](https://jc.id.lv/home-brownie/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

**Home Brownie** is an autonomous, AI-powered Telegram household spirit and assistant for personal homelabs. Powered by the **Google Antigravity SDK** and **Gemini**, it integrates multiple Model Context Protocol (MCP) servers to manage family documents, household wikis, smart home automation, and network infrastructure directly from Telegram.

---

## ✨ Features

- 📄 **Paperless-ngx Archive Integration**: Upload documents, auto-assign metadata, and search PDF archives.
- 📚 **GitHub Wiki / Quartz Integration**: Search, create, and update family notes and home documentation.
- 🏠 **Home Assistant Integration**: Query smart sensors, devices, and control home automations.
- ☁️ **Cloudflare Integration**: Query DNS, Tunnels, and Zero Trust access policies.
- 🔒 **Multi-Tenant Family RBAC**: Per-user permission mapping. If a user lacks an API token for a service, that MCP server is dynamically excluded from their session.
- 💬 **Natural Language Agent**: Intelligent tool routing via Gemini — ask questions in plain text or voice messages in any language.

---

## 🛠️ Stack

- **Language**: Python 3.14
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv)
- **AI Engine**: Google Antigravity SDK & Gemini 3.1 Flash
- **Framework**: `telebot` (Async)
- **Quality Tools**: `ruff`, `mypy` (strict), `pytest`

---

## 🚀 Local Development & Setup

### Prerequisites

- Python 3.14+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [`mise`](https://mise.jdx.dev/) (optional, for task runner shortcuts)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/rabestro/home-brownie.git
cd home-brownie

# Install all dependencies (including dev tools)
uv sync --all-groups

# Copy and configure environment variables
cp .env.example .env

# Run checks
mise run format
mise run lint
mise run mypy
mise run test

# Start the bot locally
mise run run
```

---

## 📄 License

This project is open-source under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).
