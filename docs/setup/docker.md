# 🐳 Docker Deployment

Home Genie provides a multi-stage `Dockerfile` and `docker-compose.yml` for self-hosted deployment.

---

## Docker Compose Setup

1. Copy `.env.example` to `.env` and fill in your tokens.
2. Build and start the container:

```bash
docker compose up -d --build
```

---

## Docker Image Specification

- **Base Image**: `python:3.14-slim`
- **Node.js**: 24+ preinstalled (required for Node-based MCP tools)
- **Preinstalled Binaries**: Pinned `@baruchiro/paperless-mcp@2.0.1`
- **User Security**: Runs as unprivileged `app` user (UID 1000)
