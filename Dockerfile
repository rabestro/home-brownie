FROM node:24-slim AS node-builder

# Install pinned MCP binaries in the Node stage
ARG PAPERLESS_MCP_VERSION=2.0.1
ARG HOME_ASSISTANT_MCP_VERSION=1.0.10
RUN npm install -g \
    "@baruchiro/paperless-mcp@${PAPERLESS_MCP_VERSION}" \
    "@jarahkon/hass-mcp-server@${HOME_ASSISTANT_MCP_VERSION}"

# --- Final image ---
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy Node.js runtime and globally installed MCP packages from the builder stage
COPY --from=node:24-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node-builder  /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=node-builder  /usr/local/bin/npm          /usr/local/bin/npm
COPY --from=node-builder  /usr/local/bin/npx          /usr/local/bin/npx
COPY --from=node-builder  /usr/local/bin/paperless-mcp      /usr/local/bin/paperless-mcp
COPY --from=node-builder  /usr/local/bin/hass-mcp-server    /usr/local/bin/hass-mcp-server

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
# Install only third-party dependencies from pre-built wheels (no sdist build scripts),
# then install the project itself from its pre-built wheel
RUN uv build --wheel --out-dir dist/ \
    && uv sync --frozen --no-dev --no-install-project --no-build \
    && uv pip install --no-build dist/home_brownie-*.whl

CMD ["uv", "run", "python", "-m", "home_brownie"]
