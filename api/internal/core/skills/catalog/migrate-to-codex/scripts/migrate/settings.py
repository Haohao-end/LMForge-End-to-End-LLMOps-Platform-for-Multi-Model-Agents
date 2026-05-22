"""Shared source path constants for migration discovery/reporting.

Constants here describe where Claude Code commonly stores instructions,
commands, skills, agents, MCP config, plugin references, and hooks. Paths are
relative to `ScopePaths.source`, the directory containing `.claude`, `.mcp.json`,
and similar source roots.
"""

from __future__ import annotations

from pathlib import Path

CLAUDE_SETTINGS_JSON_RELATIVE = (
    Path(".claude") / "settings.json",
    Path(".claude") / "settings.local.json",
)

CLAUDE_MCP_JSON_RELATIVE = (
    Path(".mcp.json"),
    Path(".claude.json"),
)

CLAUDE_PLUGIN_MANUAL_PATHS = (
    (Path(".claude") / "plugins", "Claude Code plugins"),
    (
        Path(".claude") / "plugin-marketplaces.json",
        "Claude Code plugin marketplace registry",
    ),
    (
        Path(".claude-plugin") / "marketplace.json",
        "Claude Code plugin marketplace",
    ),
)

SOURCE_SCAN_ROOTS = (
    (Path(".claude"), "primary source"),
)

SOURCE_SCOPE_MARKERS = (
    Path(".claude"),
)
