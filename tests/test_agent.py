"""Unit tests for dynamic MCP server sandbox building and user RBAC in agent.py."""

from home_genie.agent import build_mcp_servers_for_user
from home_genie.config import UserPermissions


def test_build_mcp_servers_empty_tokens() -> None:
    perms = UserPermissions(name="UserNoTokens")
    servers = build_mcp_servers_for_user(perms)
    assert len(servers) == 0


def test_build_mcp_servers_with_paperless_and_home_connect() -> None:
    perms = UserPermissions(
        name="UserWithTools",
        paperless_token="token_paperless_123",
        home_connect_token="token_hc_456",
        home_connect_client_id="client_id_789",
    )
    servers = build_mcp_servers_for_user(perms)
    assert len(servers) == 2

    server_names = {s.name for s in servers}
    assert "paperless-ngx" in server_names
    assert "home-connect" in server_names

    hc_server = next(s for s in servers if s.name == "home-connect")
    assert hc_server.env["HOME_CONNECT_TOKEN"] == "token_hc_456"
    assert hc_server.env["HOME_CONNECT_CLIENT_ID"] == "client_id_789"


def test_build_mcp_servers_with_all_services() -> None:
    perms = UserPermissions(
        name="SuperUser",
        paperless_token="p_token",
        github_token="g_token",
        home_assistant_token="ha_token",
        cloudflare_token="cf_token",
        home_connect_token="hc_token",
    )
    servers = build_mcp_servers_for_user(perms)
    assert len(servers) == 5

    names = [s.name for s in servers]
    assert names == [
        "paperless-ngx",
        "github-wiki",
        "home-assistant",
        "cloudflare",
        "home-connect",
    ]
