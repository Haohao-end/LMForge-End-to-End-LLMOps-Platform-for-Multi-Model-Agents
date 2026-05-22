"""Discover and classify source instruction files for AGENTS.md migration.

Chooses the first supported instruction file for a project/global scope. Neutral
instruction files are safe for `AGENTS.md` symlinks; content with obvious
Claude-only lifecycle, hook, subagent, or permission assumptions is treated as
requiring a generated Codex-specific copy and manual rewrite.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from migrate.common import MigrationReportItem


INSTRUCTION_SOURCE_CANDIDATES = (
    Path(".claude") / "CLAUDE.md",
    Path("CLAUDE.md"),
    Path("claude.md"),
    Path("AGENTS.md"),
)

CLAUDE_ONLY_INSTRUCTION_MARKERS = (
    "/hooks",
    ".claude/agents/",
    ".claude/settings",
    "Subagent",
    "subagent",
    "permissionMode",
    "ExitPlanMode",
)
MAX_AGENTS_MD_BYTES = 32 * 1024


def instruction_source_file(
    source_root: Path,
    is_global: bool,
    path_exists_with_exact_case: Callable[[Path], bool],
) -> Path | None:
    candidates = INSTRUCTION_SOURCE_CANDIDATES
    if not is_global:
        candidates = tuple(
            candidate
            for candidate in candidates
            if candidate != Path(".claude") / "CLAUDE.md"
        )

    for candidate in candidates:
        source_file = source_root / candidate
        if path_exists_with_exact_case(source_file):
            return source_file
    return None


def should_symlink_instructions(content: str) -> bool:
    return not any(marker in content for marker in CLAUDE_ONLY_INSTRUCTION_MARKERS)


def validate_agents_md_files(target_root: Path) -> list[MigrationReportItem]:
    report_items: list[MigrationReportItem] = []
    for agents_file in sorted(target_root.rglob("AGENTS.md")):
        relative_path = agents_file.relative_to(target_root)
        size_bytes = agents_file.stat().st_size
        if size_bytes > MAX_AGENTS_MD_BYTES:
            report_items.append(
                MigrationReportItem(
                    "warning",
                    relative_path,
                    f"{size_bytes / 1024:.1f}KB exceeds the 32KB review threshold.",
                )
            )
            continue
        report_items.append(
            MigrationReportItem(
                "ok",
                relative_path,
                f"{size_bytes / 1024:.1f}KB is under the 32KB review threshold.",
            )
        )
    return report_items
