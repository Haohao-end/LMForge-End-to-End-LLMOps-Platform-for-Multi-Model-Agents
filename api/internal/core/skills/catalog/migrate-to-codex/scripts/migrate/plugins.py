"""Report Claude Code plugin surfaces that need manual Codex migration.

Claude Code plugins and plugin marketplaces can bundle commands, agents, MCP
servers, skills, and hooks with provider-specific metadata. The migrator reports
their presence as manual follow-up; it does not install Codex plugins, copy
plugin trees, or read marketplace `source` entries.
"""

from __future__ import annotations

from migrate.common import ConversionResult, ScopePaths, report_manual_paths
from migrate.settings import CLAUDE_PLUGIN_MANUAL_PATHS


def report_plugins(scope: ScopePaths) -> ConversionResult:
    return report_manual_paths(scope, CLAUDE_PLUGIN_MANUAL_PATHS)
