"""Convert Claude Code MCP/settings JSON into Codex config TOML.

Reads Claude settings plus `.mcp.json` / `.claude.json`, maps model and sandbox
settings when there is a known Codex equivalent, and renders MCP server entries
for `.codex/config.toml`. Header/env forms are partially normalized to Codex
`bearer_token_env_var`, `env_http_headers`, `http_headers`, `env_vars`, and
literal `env` tables.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Mapping
from pathlib import Path

from migrate.common import (
    CODEX_CONFIG_PATH,
    MigrationReportItem,
    json_object,
    json_string,
    json_string_tuple,
    path_exists_with_exact_case,
)
from migrate.settings import CLAUDE_MCP_JSON_RELATIVE
from utils.util import TomlValue


ENV_VAR_RE = re.compile(r"\A\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}\Z")
BEARER_ENV_VAR_RE = re.compile(
    r"\ABearer\s+\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}\Z"
)


def mcp_server_toml_table(
    server_name: str,
    server_config: Mapping[str, object],
    enabled_servers: tuple[str, ...],
    disabled_servers: frozenset[str],
) -> dict[str, TomlValue]:
    table: dict[str, TomlValue] = {}
    enabled = mcp_enabled_state(server_config)
    if enabled is False:
        table["enabled"] = False
    elif enabled_servers and server_name not in enabled_servers:
        table["enabled"] = False
    elif server_name in disabled_servers:
        table["enabled"] = False
    if url := json_string(server_config.get("url")):
        table["url"] = url
    if command := json_string(server_config.get("command")):
        table["command"] = command
    if args := json_string_tuple(server_config.get("args")):
        table["args"] = list(args)
    if "headers" in server_config:
        append_header_config(table, json_object(server_config["headers"]))
    if "env" in server_config:
        append_env_config(table, json_object(server_config["env"]))
    return table


def mcp_report_items(
    mcp_servers: tuple[tuple[str, dict[str, object]], ...],
) -> list[MigrationReportItem]:
    report_items = [
        MigrationReportItem(
            "rewritten",
            CODEX_CONFIG_PATH,
            f"Converted {len(mcp_servers)} MCP server entries.",
        )
    ]
    for server_name, server_config in mcp_servers:
        notes = mcp_manual_notes(server_name, server_config)
        if notes:
            report_items.append(
                MigrationReportItem(
                    "manual_fix_required",
                    CODEX_CONFIG_PATH,
                    f"MCP server `{server_name}` needs review: {' '.join(notes)}",
                )
            )
    return report_items


def append_header_config(
    table: dict[str, TomlValue],
    headers: Mapping[str, object],
) -> None:
    static_headers: dict[str, str] = {}
    env_headers: dict[str, str] = {}

    for key, value in headers.items():
        header_value = str(value)
        bearer_match = BEARER_ENV_VAR_RE.match(header_value)
        if key.lower() == "authorization" and bearer_match:
            table["bearer_token_env_var"] = bearer_match.group(1)
            continue

        env_match = ENV_VAR_RE.match(header_value)
        if env_match:
            env_headers[key] = env_match.group(1)
            continue

        static_headers[key] = header_value

    if static_headers:
        table["http_headers"] = static_headers
    if env_headers:
        table["env_http_headers"] = env_headers


def append_env_config(
    table: dict[str, TomlValue],
    env: Mapping[str, object],
) -> None:
    static_env: dict[str, str] = {}
    env_vars: list[str] = []

    for key, value in env.items():
        env_value = str(value)
        env_match = ENV_VAR_RE.match(env_value)
        if env_match and env_match.group(1) == key:
            env_vars.append(key)
            continue

        static_env[key] = env_value

    if env_vars:
        table["env_vars"] = env_vars
    if static_env:
        table["env"] = static_env


def mcp_manual_notes(
    server_name: str,
    server_config: Mapping[str, object],
) -> tuple[str, ...]:
    notes: list[str] = []
    source_type = json_string(server_config.get("type"))
    if source_type and source_type not in {"http", "stdio"}:
        notes.append(
            f"Claude MCP `type: {source_type}` was not written to Codex config; verify that the generated `url` or `command` is a supported Codex transport."
        )
    unsupported_fields = unsupported_mcp_server_fields(server_config)
    if unsupported_fields:
        notes.append(
            "Review unsupported Claude MCP fields manually: "
            + ", ".join(f"`{field_name}`" for field_name in unsupported_fields)
            + "."
        )
    return tuple(notes)


def mcp_enabled_state(server_config: Mapping[str, object]) -> bool | None:
    if server_config.get("enabled") is False:
        return False
    if server_config.get("disabled") is True:
        return False
    return None


def unsupported_mcp_server_fields(
    server_config: Mapping[str, object],
) -> tuple[str, ...]:
    supported = {
        "args",
        "command",
        "disabled",
        "enabled",
        "env",
        "headers",
        "name",
        "scope",
        "type",
        "url",
    }
    return tuple(sorted(key for key in server_config if key not in supported))


def read_claude_mcp_servers(source_root: Path) -> tuple[tuple[str, dict[str, object]], ...]:
    servers: list[tuple[str, dict[str, object]]] = []
    for relative_path in CLAUDE_MCP_JSON_RELATIVE:
        source_file = source_root / relative_path
        if not path_exists_with_exact_case(source_file):
            continue
        mcp_config = json_object(json.loads(source_file.read_text()))
        for server_name, server_config in json_object(mcp_config.get("mcpServers")).items():
            servers.append((server_name, json_object(server_config)))
    return tuple(servers)


def validate_mcp_commands(config: dict[str, object]) -> list[MigrationReportItem]:
    mcp_servers = config.get("mcp_servers")
    if not isinstance(mcp_servers, dict):
        return []

    report_items: list[MigrationReportItem] = []
    for server_name, server_config in sorted(mcp_servers.items()):
        if not isinstance(server_config, dict):
            continue
        command = server_config.get("command")
        if not command:
            continue
        command_text = str(command)
        if shutil.which(command_text):
            report_items.append(
                MigrationReportItem(
                    "ok",
                    CODEX_CONFIG_PATH,
                    f"MCP server `{server_name}` command `{command_text}` is on PATH.",
                )
            )
        else:
            report_items.append(
                MigrationReportItem(
                    "warning",
                    CODEX_CONFIG_PATH,
                    f"MCP server `{server_name}` command `{command_text}` was not found on PATH.",
                )
            )
    return report_items
