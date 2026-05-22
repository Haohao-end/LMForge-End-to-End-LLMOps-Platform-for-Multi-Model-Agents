"""Convert Claude Code subagents into Codex custom-agent TOML.

Reads `.claude/agents/*.md` files, parses their frontmatter/body, and emits
`.codex/agents/<name>.toml` artifacts. Partially mapped metadata such as
skills, tool allowlists, and unknown permission modes is preserved as prompt
guidance plus a manual-review report row.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from migrate.common import (
    CODEX_AGENTS_ROOT,
    ConversionResult,
    MigrationReportItem,
    ParsedDocument,
    PlannedArtifact,
    append_report_item,
    format_bullets,
    format_manual_migration_block,
    map_model_effort,
    map_model_name,
    map_permission_mode,
    unsupported_frontmatter_fields,
)
from utils.util import (
    TomlMultilineString,
    first_markdown_heading,
    render_toml_document,
    slugify_name,
)


AGENT_SOURCE_ROOTS = (
    Path(".claude") / "agents",
)
SUPPORTED_AGENT_FRONTMATTER = (
    "name",
    "description",
    "model",
    "permissionMode",
    "skills",
    "tools",
    "disallowedTools",
    "effort",
)


def iter_agent_files(source_root: Path) -> tuple[Path, ...]:
    if not source_root.exists():
        return ()
    return tuple(
        source_file
        for source_file in sorted(source_root.glob("*.md"))
        if source_file.stem != "README"
    )


def agent_metadata(source_file: Path, document: ParsedDocument) -> dict[str, object]:
    inferred_fields: list[str] = []
    name = document.frontmatter.optional_string("name")
    if not name:
        name = slugify_name(source_file.stem)
        inferred_fields.append("name")

    description = document.frontmatter.optional_string("description")
    if not description:
        heading = first_markdown_heading(document.body)
        if heading:
            description = f"Migrated Claude subagent inferred from heading `{heading}`."
        else:
            description = f"Migrated Claude subagent inferred from `{source_file.name}`."
        inferred_fields.append("description")

    return {
        "name": name,
        "description": description,
        "model": document.frontmatter.optional_string("model"),
        "permission_mode": document.frontmatter.optional_string("permissionMode"),
        "skills": document.frontmatter.string_tuple("skills"),
        "tools": document.frontmatter.string_tuple("tools"),
        "disallowed_tools": document.frontmatter.string_tuple("disallowedTools"),
        "effort": document.frontmatter.optional_string("effort"),
        "unsupported_fields": unsupported_frontmatter_fields(
            document.frontmatter.to_dict(),
            SUPPORTED_AGENT_FRONTMATTER,
        )
        + tuple(inferred_fields),
    }


def convert_agent_file(source_file: Path) -> tuple[PlannedArtifact, MigrationReportItem]:
    document = ParsedDocument.from_file(source_file)
    metadata = agent_metadata(source_file, document)
    artifact = PlannedArtifact.for_agent(
        source_file,
        render_agent_toml(document.body, **metadata),
    )
    return artifact, agent_report_item(source_file, **metadata)


def render_agent_toml(
    body: str,
    *,
    name: str,
    description: str,
    model: str | None,
    permission_mode: str | None,
    skills: tuple[str, ...],
    tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
    effort: str | None,
    unsupported_fields: tuple[str, ...],
) -> str:
    document = {
        "name": name,
        "description": description,
    }

    if model:
        document["model"] = map_model_name(model)
    if effort:
        document["model_reasoning_effort"] = map_model_effort(model, effort)
    sandbox_mode = map_permission_mode(permission_mode)
    if sandbox_mode:
        document["sandbox_mode"] = sandbox_mode

    document["developer_instructions"] = TomlMultilineString(
        render_agent_body(
            body,
            permission_mode=permission_mode,
            skills=skills,
            tools=tools,
            disallowed_tools=disallowed_tools,
            unsupported_fields=unsupported_fields,
        ).strip()
    )

    return render_toml_document(document)


def render_agent_body(
    body: str,
    *,
    permission_mode: str | None,
    skills: tuple[str, ...],
    tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
    unsupported_fields: tuple[str, ...],
) -> str:
    sections = []
    manual_notes: list[str] = []

    sandbox_mode = map_permission_mode(permission_mode)
    if permission_mode and not sandbox_mode:
        manual_notes.append(
            f"Claude `permissionMode: {permission_mode}` has no direct Codex mapping. "
            "Manually choose `sandbox_mode`, `[permissions]`, MCP tool filters, or app tool filters before relying on this agent."
        )

    if skills:
        sections.append(
            "## Skills\n\n"
            "You're allowed to use these skills when working on this task:\n\n"
            f"{format_bullets(skills, '$')}"
        )
        manual_notes.append(
            "Claude `skills` preload semantics were preserved as prompt guidance. Verify this agent still discovers the intended skills at runtime."
        )

    if tools or disallowed_tools:
        tool_section_lines = [
            "## Tools",
            "",
            "Claude tool allow/deny lists were preserved as prompt guidance, not Codex permissions.",
        ]
        if tools:
            tool_section_lines.extend(
                [
                    "",
                    "You're allowed to use these tools:",
                    "",
                    format_bullets(tools),
                ]
            )
        if disallowed_tools:
            tool_section_lines.extend(
                [
                    "",
                    "Don't use these tools:",
                    "",
                    format_bullets(disallowed_tools),
                ]
            )
        sections.append("\n".join(tool_section_lines))
        manual_notes.append(
            "Rebuild Claude `tools` / `disallowedTools` intent with Codex sandbox, MCP tool filters, or app tool filters if you need hard enforcement."
        )

    if unsupported_fields:
        manual_notes.append(
            "Review unsupported Claude subagent fields manually: "
            f"{', '.join(f'`{field_name}`' for field_name in unsupported_fields)}."
        )

    if manual_notes:
        sections.append(format_manual_migration_block(manual_notes))

    if not sections:
        return body

    joined_sections = "\n\n".join(sections)
    return f"{body.rstrip()}\n\n{joined_sections}\n"


def agent_report_detail(
    *,
    permission_mode: str | None,
    skills: tuple[str, ...],
    tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
    unsupported_fields: tuple[str, ...],
    **_: object,
) -> str:
    caveats: list[str] = []
    if skills:
        caveats.append("skills")
    if tools:
        caveats.append("tools")
    if disallowed_tools:
        caveats.append("disallowedTools")
    if permission_mode and not map_permission_mode(permission_mode):
        caveats.append("permissionMode")
    caveats.extend(unsupported_fields)
    if not caveats:
        return "Converted Claude subagent."
    return (
        "Manual review required for Claude subagent fields: "
        + ", ".join(f"`{field_name}`" for field_name in caveats)
        + "."
    )


def agent_report_item(
    source_file: Path,
    *,
    permission_mode: str | None,
    skills: tuple[str, ...],
    tools: tuple[str, ...],
    disallowed_tools: tuple[str, ...],
    unsupported_fields: tuple[str, ...],
    **metadata: object,
) -> MigrationReportItem:
    report_items: list[MigrationReportItem] = []
    detail = agent_report_detail(
        permission_mode=permission_mode,
        skills=skills,
        tools=tools,
        disallowed_tools=disallowed_tools,
        unsupported_fields=unsupported_fields,
        **metadata,
    )
    append_report_item(
        report_items,
        skills
        or tools
        or disallowed_tools
        or (permission_mode and not map_permission_mode(permission_mode))
        or unsupported_fields,
        CODEX_AGENTS_ROOT / f"{source_file.stem}.toml",
        detail,
        detail,
    )
    return report_items[0]


def convert_agents(source_root: Path) -> ConversionResult:
    return convert_agent_files(source_root / ".claude" / "agents")


def convert_agent_files(source_root: Path) -> ConversionResult:
    result = ConversionResult()
    for source_file in iter_agent_files(source_root):
        artifact, report_item = convert_agent_file(source_file)
        result.artifacts.append(artifact)
        result.summary.subagents += 1
        result.report_items.append(report_item)
    return result


def validate_agent_files(target_root: Path) -> list[MigrationReportItem]:
    agents_root = target_root / CODEX_AGENTS_ROOT
    if not agents_root.exists():
        return []

    report_items: list[MigrationReportItem] = []
    for agent_file in sorted(agents_root.glob("*.toml")):
        relative_path = agent_file.relative_to(target_root)
        try:
            parsed = tomllib.loads(agent_file.read_text())
        except tomllib.TOMLDecodeError as exc:
            report_items.append(
                MigrationReportItem("error", relative_path, f"invalid TOML: {exc}.")
            )
            continue

        missing = [
            key
            for key in ("name", "description", "developer_instructions")
            if not parsed.get(key)
        ]
        if missing:
            report_items.append(
                MigrationReportItem(
                    "error",
                    relative_path,
                    "agent TOML missing " + ", ".join(missing) + ".",
                )
            )
            continue
        report_items.append(
            MigrationReportItem("ok", relative_path, "agent TOML has required fields.")
        )
    return report_items
