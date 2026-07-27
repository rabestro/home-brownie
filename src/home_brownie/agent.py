"""AI agent wiring, dynamic multi-tenant MCP sandboxing, and execution loop for home-genie."""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig
from google.antigravity.types import McpStdioServer

from home_brownie.config import Config, UserPermissions

logger = logging.getLogger(__name__)

_FILE_LINK_RE = re.compile(r"\[([^\]]+)\]\(file://[^)]+\)")
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

ARCHIVE_INSTRUCTIONS = (
    "You are an expert archiving assistant for the personal document archive in Paperless-ngx. "
    "You are processing a document that has already been successfully uploaded. "
    "Its ID is provided in the prompt.\n"
    "Adhere to these rules when updating this document:\n"
    "1. Call `get_document` with the given ID to fetch its text content and properties.\n"
    "2. Based on the document's text, determine the correct metadata "
    "(Title, Created Date, Correspondent, Document Type).\n"
    "3. Call `update_document` to update the document's Title, "
    "Created (in YYYY-MM-DD), Correspondent, and Document Type.\n"
    "4. Call `list_tags` to see every tag that exists in this archive "
    "(their names and IDs). Decide which existing tags match the document's "
    "content, judging by tag names.\n"
    "5. Update the document's tags via `update_document`, passing the complete "
    "final list of tag IDs.\n"
    "6. Call `create_document_note` to add a structured note "
    "describing the document, owner, and key details.\n"
    "7. Output a final report describing what actions were done.\n"
    "IMPORTANT LANGUAGE RULE:\n"
    "- Detect the language of the document's content and write the note "
    "and report in that same language.\n"
    "IMPORTANT FORMATTING RULES:\n"
    "- The response will be sent as a Telegram message. "
    "Do NOT use markdown links with URLs. "
    "Do NOT include any file:// or http:// links in the response.\n"
    "- Use plain text and emoji for formatting."
)


def _clean_agent_response(text: str) -> str:
    """Removes internal file:// links from the agent response."""
    text = _FILE_LINK_RE.sub(r"\1", text)
    text = _BARE_FILE_URL_RE.sub("", text)
    return text.strip()


def _build_mcp_env(extra_vars: dict[str, str] | None = None) -> dict[str, str]:
    """Builds a sanitized environment dictionary for an MCP subprocess."""
    env: dict[str, str] = {}
    for key in _MCP_ENV_PASSTHROUGH:
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    if extra_vars:
        env.update(extra_vars)
    return env


def build_mcp_servers_for_user(perms: UserPermissions) -> list[McpStdioServer]:
    """Dynamically constructs the list of MCP servers authorized for a user."""
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
        github_binary = "mcp-server-github"
        cmd = github_binary if shutil.which(github_binary) else "npx"
        args = [] if cmd == github_binary else ["-y", "@modelcontextprotocol/server-github"]
        servers.append(
            McpStdioServer(
                name="github-wiki",
                command=cmd,
                args=args,
                env=_build_mcp_env({"GITHUB_PERSONAL_ACCESS_TOKEN": perms.github_token}),
            )
        )

    # 3. Home Assistant MCP
    if perms.home_assistant_token:
        ha_binary = "hass-mcp-server"
        cmd = ha_binary if shutil.which(ha_binary) else "npx"
        args = [] if cmd == ha_binary else ["-y", "@jarahkon/hass-mcp-server@1.0.10"]
        env = _build_mcp_env(
            {
                "HOME_ASSISTANT_URL": Config.HOME_ASSISTANT_URL,
                "HOME_ASSISTANT_TOKEN": perms.home_assistant_token,
                "HA_URL": Config.HOME_ASSISTANT_URL,
                "HA_TOKEN": perms.home_assistant_token,
            }
        )
        servers.append(
            McpStdioServer(
                name="home-assistant",
                command=cmd,
                args=args,
                env=env,
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

    # 5. Home Connect MCP
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
    """Loads system instructions from base_instructions.md and renders wiki placeholders."""
    instructions_file = PROMPTS_DIR / "base_instructions.md"
    if instructions_file.exists():
        template = instructions_file.read_text(encoding="utf-8")
        return template.format(
            WIKI_REPO_OWNER=Config.WIKI_REPO_OWNER,
            WIKI_REPO_NAME=Config.WIKI_REPO_NAME,
            WIKI_REPO_PATH=Config.WIKI_REPO_PATH,
        )
    return "You are Home Genie, a helpful homelab AI assistant."


async def run_agent_query(perms: UserPermissions, prompt: str) -> str:
    """Runs the Antigravity agent against user-authorized MCP tools."""
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


async def run_archiving_agent(perms: UserPermissions, doc_id: int, file_name: str) -> str:
    """Runs the document archiving agent against Paperless MCP."""
    mcp_servers = build_mcp_servers_for_user(perms)
    prompt = (
        f"We have a new document to archive in Paperless-ngx.\n"
        f"Document ID: {doc_id}\n"
        f"Original Filename: {file_name}\n\n"
        f"Please retrieve this document using `get_document` with ID {doc_id}, "
        f"analyze its content, assign metadata and tags, write a structured note, "
        f"and output a final report."
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        agent_config = LocalAgentConfig(
            system_instructions=ARCHIVE_INSTRUCTIONS,
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
