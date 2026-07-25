FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install Node.js 24 from the official image — no curl | bash, integrity guaranteed by Docker
COPY --from=node:24-slim /usr/local/bin/node   /usr/local/bin/node
COPY --from=node:24-slim /usr/local/bin/npm    /usr/local/bin/npm
COPY --from=node:24-slim /usr/local/bin/npx    /usr/local/bin/npx
COPY --from=node:24-slim /usr/local/lib/node_modules /usr/local/lib/node_modules

# Install pinned Paperless & Home Assistant MCP binaries
ARG PAPERLESS_MCP_VERSION=2.0.1
ARG HOME_ASSISTANT_MCP_VERSION=1.0.10
RUN npm install -g \
    "@baruchiro/paperless-mcp@${PAPERLESS_MCP_VERSION}" \
    "@jarahkon/hass-mcp-server@${HOME_ASSISTANT_MCP_VERSION}"

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Create unprivileged user
RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

# Copy project configuration, docs, and source
COPY --chown=app:app pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=app:app src ./src

# Install dependencies
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "python", "-m", "home_brownie"]
