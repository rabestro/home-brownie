# Agent Guidelines for home-genie

This document defines the rules, stack, standards, and workflow conventions for AI agents collaborating on the `home-genie` project. It is canonical; `CLAUDE.md` and `GEMINI.md` are thin shims that point here.

## Stack & Architecture

- **Core**: Python 3.14 (managed with `uv` package manager).
- **Telegram Bot**: Async Telegram Bot (`pyTelegramBotAPI`/`telebot.async_telebot`).
- **AI Integration**: Google Antigravity SDK (`Agent`, `LocalAgentConfig`, `CapabilitiesConfig`).
- **MCP integrations**:
  - Paperless-ngx MCP (`@baruchiro/paperless-mcp`)
  - GitHub Wiki MCP
  - Home Assistant MCP
  - Cloudflare MCP
- **HTTP client**: `httpx` (async).
- **Formatting / Linting**: `ruff` (linter and formatter).
- **Type Checking**: `mypy` (strict mode).
- **Testing**: `pytest`.
- **Infrastructure**: Docker, Docker Compose, GitHub Actions.

## Quality & Checks

Use `mise run` or raw `uv run` commands before submitting code:
- Format code: `mise run format` (`uv run ruff format src tests && uv run ruff check src tests --fix`)
- Lint code: `mise run lint` (`uv run ruff check src tests`)
- Type check: `mise run mypy` (`uv run mypy src`)
- Run unit tests: `mise run test` (`uv run pytest`)
- Check all files with pre-commit: `uv run pre-commit run --all-files`

## Git & PR Workflow

- **Branch Naming**: `<type>/<short-desc>` (e.g. `feat/wiki-mcp`, `fix/rbac-parsing`).
- **Commits**: Follow Conventional Commits style (e.g. `feat: ...`, `fix: ...`, `chore: ...`).
- **Language**: English only for code, comments, commit messages, and docs.
- **Security**: Never commit secrets or credentials. Multi-tenant RBAC permissions are enforced per Telegram user ID.
