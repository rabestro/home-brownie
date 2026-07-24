"""AI agent wiring, dynamic multi-tenant MCP sandboxing, and execution loop for home-genie."""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig
from google.antigravity.types import McpStdioServer

from home_genie.config import Config, UserPermissions

logger = logging.getLogger(__name__)

# Regex to strip markdown links containing file:// URLs, e.g. [Title](file:///path)
_FILE_LINK_RE = re.compile(r"\[([^\]]+)\]\(file://[^)]+\)")
# Regex to strip bare file:// URLs
_BARE_FILE_URL_RE = re.compile(r"file://\S+")

_MCP_ENV_PASSTHROUGH: tuple[str, ...] = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "NODE_EXTRA_CA_CERTS",
)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _clean_agent_response(text: str) -> str:
    """Removes internal file:// links from the agent response.

    Args:
        text: The raw agent response text.

    Returns:
        Cleaned text suitable for sending to Telegram.
    """
    text = _FILE_LINK_RE.sub(r"\1", text)
    text = _BARE_FILE_URL_RE.sub("", text)
    return text.strip()


def _build_mcp_env(extra_vars: dict[str, str] | None = None) -> dict[str, str]:
    """Builds a sanitized environment dictionary for an MCP subprocess.

    Args:
        extra_vars: Optional dictionary of service-specific environment variables.

    Returns:
        Environment dictionary with allowed system environment variables plus extra_vars.
    """
    env: dict[str, str] = {}
    for key in _MCP_ENV_PASSTHROUGH:
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    if extra_vars:
        env.update(extra_vars)
    return env


def build_mcp_servers_for_user(perms: UserPermissions) -> list[McpStdioServer]:
    """Dynamically constructs the list of MCP servers authorized for a user.

    If a user lacks a token for a given service, that MCP server is excluded
    from the list, isolating user capabilities at the LLM prompt level.

    Args:
        perms: The UserPermissions object for the user.

    Returns:
        List of McpStdioServer instances configured with user tokens.
    """
    servers: list[McpStdioServer] = []

    # 1. Paperless-ngx MCP
    if perms.paperless_token:
        paperless_binary = "paperless-mcp"
        cmd = paperless_binary if shutil.which(paperless_binary) else "npx"
        args = [] if cmd == paperless_binary else ["-y", "@baruchiro/paperless-mcp@2.0.1"]
        env = _build_mcp_env(
            {
                "PAPERLESS_URL": Config.PAPERLESS_URL,
                "PAPERLESS_API_TOKEN": perms.paperless_token,
                "PAPERLESS_API_KEY": perms.paperless_token,
            }
        )
        servers.append(
            McpStdioServer(
                name="paperless-ngx",
                command=cmd,
                args=args,
                env=env,
            )
        )

    # 2. GitHub Wiki MCP
    if perms.github_token:
        servers.append(
            McpStdioServer(
                name="github-wiki",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env=_build_mcp_env({"GITHUB_PERSONAL_ACCESS_TOKEN": perms.github_token}),
            )
        )

    # 3. Home Assistant MCP
    if perms.home_assistant_token:
        servers.append(
            McpStdioServer(
                name="home-assistant",
                command="npx",
                args=["-y", "@home-assistant/mcp-server"],
                env=_build_mcp_env(
                    {
                        "HOME_ASSISTANT_URL": Config.HOME_ASSISTANT_URL,
                        "HOME_ASSISTANT_TOKEN": perms.home_assistant_token,
                    }
                ),
            )
        )

    # 4. Cloudflare MCP
    if perms.cloudflare_token:
        servers.append(
            McpStdioServer(
                name="cloudflare",
                command="npx",
                args=["-y", "@cloudflare/mcp-server-cloudflare"],
                env=_build_mcp_env({"CLOUDFLARE_API_TOKEN": perms.cloudflare_token}),
            )
        )

    # 5. Home Connect MCP (Bosch/Siemens appliances)
    if perms.home_connect_token:
        extra_env = {"HOME_CONNECT_TOKEN": perms.home_connect_token}
        if perms.home_connect_client_id:
            extra_env["HOME_CONNECT_CLIENT_ID"] = perms.home_connect_client_id
        servers.append(
            McpStdioServer(
                name="home-connect",
                command="npx",
                args=["-y", "mcp-server-home-connect"],
                env=_build_mcp_env(extra_env),
            )
        )

    return servers


def load_base_instructions() -> str:
    """Loads system instructions from base_instructions.md.

    Returns:
        Content of base_instructions.md file.
    """
    instructions_file = PROMPTS_DIR / "base_instructions.md"
    if instructions_file.exists():
        return instructions_file.read_text(encoding="utf-8")
    return "You are Home Genie, a helpful homelab AI assistant."


async def run_agent_query(perms: UserPermissions, prompt: str) -> str:
    """Runs the Antigravity agent against user-authorized MCP tools.

    Args:
        perms: The requesting user's UserPermissions.
        prompt: User natural language prompt.

    Returns:
        Cleaned agent response text.
    """
    mcp_servers = build_mcp_servers_for_user(perms)
    instructions = load_base_instructions()

    with tempfile.TemporaryDirectory() as temp_dir:
        agent_config = LocalAgentConfig(
            system_instructions=instructions,
            mcp_servers=mcp_servers,
            capabilities=CapabilitiesConfig(allow_file_write=False, allow_command_execution=False),
            save_dir=temp_dir,
            model=Config.GEMINI_MODEL,
        )

        async with Agent(agent_config) as agent:
            response = await agent.chat(prompt)
            report = ""
            async for token in response:
                report += token

    return _clean_agent_response(report)
