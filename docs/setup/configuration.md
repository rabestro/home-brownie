# ⚙️ Environment & RBAC Configuration

Home Genie relies on environment variables and a structured JSON string to enforce multi-tenant family RBAC.

---

## Environment Variables

| Variable | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Yes | Token from @BotFather | `123456789:ABC...` |
| `GEMINI_API_KEY` | Yes | API key from Google AI Studio | `AIzaSy...` |
| `GEMINI_MODEL` | No | Gemini model selection | `gemini-3.1-flash-lite` |
| `PAPERLESS_URL` | Optional | Endpoint for Paperless-ngx | `https://docs.petera9a.id.lv` |
| `HOME_ASSISTANT_URL` | Optional | Endpoint for Home Assistant | `https://home.petera9a.id.lv` |
| `FAMILY_USERS` | Yes | JSON string mapping Telegram User IDs to tokens | *See JSON schema below* |

---

## `FAMILY_USERS` JSON Schema

```json
{
  "123456789": {
    "name": "Jegors",
    "paperless_token": "token_abc123",
    "github_token": "ghp_xyz789",
    "home_assistant_token": "eyJ...",
    "cloudflare_token": "token_cf...",
    "home_connect_token": "token_hc...",
    "home_connect_client_id": "client_id_..."
  }
}
```

If a user lacks a token for a specific service (e.g. `paperless_token` is omitted or set to `null`), that MCP server is excluded from their agent session.
