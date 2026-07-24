FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install Node.js 24+ for Node-based MCP tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pinned Paperless MCP binary
ARG PAPERLESS_MCP_VERSION=2.0.1
RUN npm install -g --ignore-scripts "@baruchiro/paperless-mcp@${PAPERLESS_MCP_VERSION}"

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

CMD ["uv", "run", "python", "-m", "home_genie"]
