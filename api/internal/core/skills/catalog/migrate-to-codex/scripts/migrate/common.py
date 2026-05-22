"""Shared data models, frontmatter rendering, reporting, and path helpers.

Defines the artifact/report model used by every migration section, the
YAML-frontmatter adapter used for skills/agents/commands, Claude-model and
permission-mode partial mappings, and generic filesystem/report helpers. This
module should not know about one migration surface's control flow.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields as dataclass_fields
from enum import Enum
from pathlib import Path
from typing import TypeAlias

from migrate.settings import CLAUDE_SETTINGS_JSON_RELATIVE
from utils.util import (
    format_yaml_mapping,
    parse_yaml_mapping,
    read_json_mapping_file,
)


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)
CODEX_CONFIG_PATH = Path(".codex") / "config.toml"
CODEX_AGENTS_ROOT = Path(".codex") / "agents"
CODEX_SKILLS_ROOT = Path(".agents") / "skills"
SUMMARY_LABELS = {
    "mcp_servers": "mcp servers",
}
PERMISSION_MODE_MAPPINGS = {
    "acceptEdits": "workspace-write",
    "readOnly": "read-only",
}
YamlScalar: TypeAlias = str | bool | int | float | None
YamlValue: TypeAlias = YamlScalar | Sequence[YamlScalar]


@dataclass(frozen=True)
class ScopePaths:
    source: Path
    is_global: bool


@dataclass(frozen=True)
class ModelMapping:
    source_prefix: str
    target_model: str
    effort_mapping: tuple[tuple[str, str], ...]

    def map_effort(self, effort: str) -> str:
        for source_effort, target_effort in self.effort_mapping:
            if effort == source_effort:
                return target_effort
        return effort


MODEL_PREFIX_MAPPINGS = (
    ModelMapping(
        "claude-opus",
        "gpt-5.4",
        (("low", "low"), ("medium", "medium"), ("high", "high"), ("max", "xhigh")),
    ),
    ModelMapping(
        "claude-sonnet",
        "gpt-5.4-mini",
        (("low", "medium"), ("medium", "high"), ("high", "xhigh"), ("max", "xhigh")),
    ),
    ModelMapping(
        "claude-haiku",
        "gpt-5.4-mini",
        (("low", "low"), ("medium", "medium"), ("high", "high"), ("max", "xhigh")),
    ),
)


class ArtifactKind(Enum):
    FILE = "file"
    SKILL = "skill"
    AGENT = "agent"


@dataclass(frozen=True)
class GeneratedText:
    content: str


@dataclass(frozen=True)
class SourceCopy:
    source_path: Path


@dataclass(frozen=True)
class SourceSymlink:
    source_path: Path


ArtifactPayload: TypeAlias = GeneratedText | SourceCopy | SourceSymlink


@dataclass(frozen=True)
class MigrationReportItem:
    status: str
    path: Path
    detail: str


@dataclass(frozen=True)
class SimpleYamlFrontmatter:
    values: dict[str, YamlValue]

    def required_string(self, key: str) -> str:
        return str(self.values[key])

    def optional_string(self, key: str) -> str | None:
        value = self.values.get(key)
        if value is None:
            return None
        return str(value)

    def string_tuple(self, key: str) -> tuple[str, ...]:
        value = self.values.get(key)
        if value is None:
            return ()

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return tuple(str(item).strip() for item in value if str(item).strip())

        return tuple(
            split_item
            for split_item in (part.strip() for part in str(value).split(","))
            if split_item
        )

    def to_dict(self) -> dict[str, YamlValue]:
        return self.values


@dataclass(frozen=True)
class ParsedDocument:
    frontmatter: SimpleYamlFrontmatter
    body: str
    path: Path | None = None

    @classmethod
    def from_file(cls, source_file: Path) -> ParsedDocument:
        return parse_frontmatter(source_file.read_text(), source_file)


@dataclass(frozen=True)
class PlannedArtifact:
    relative_path: Path
    payload: ArtifactPayload
    kind: ArtifactKind = ArtifactKind.FILE

    @classmethod
    def for_skill(cls, source_file: Path, content: str) -> PlannedArtifact:
        return cls(
            relative_path=CODEX_SKILLS_ROOT / source_file.parent.name / "SKILL.md",
            payload=GeneratedText(content),
            kind=ArtifactKind.SKILL,
        )

    @classmethod
    def for_agent(cls, source_file: Path, content: str) -> PlannedArtifact:
        return cls(
            relative_path=CODEX_AGENTS_ROOT / f"{source_file.stem}.toml",
            payload=GeneratedText(content),
            kind=ArtifactKind.AGENT,
        )

    @classmethod
    def from_source_file(
        cls, source_file: Path, relative_path: Path
    ) -> PlannedArtifact:
        return cls(
            relative_path=relative_path,
            payload=SourceCopy(source_file),
        )

    def prefixed(self, prefix: Path) -> PlannedArtifact:
        return PlannedArtifact(
            relative_path=prefix / self.relative_path,
            payload=self.payload,
            kind=self.kind,
        )

    def without_prefix(self) -> PlannedArtifact:
        return PlannedArtifact(
            relative_path=Path(*self.relative_path.parts[1:]),
            payload=self.payload,
            kind=self.kind,
        )

@dataclass
class MigrationSummary:
    instructions: int = 0
    skills: int = 0
    subagents: int = 0
    mcp_servers: int = 0
    orphaned_skills: int = 0
    orphaned_subagents: int = 0

    def add(self, other: MigrationSummary) -> None:
        for summary_field in dataclass_fields(self):
            field_name = summary_field.name
            setattr(
                self,
                field_name,
                getattr(self, field_name) + getattr(other, field_name),
            )

    def render(self, deploy_mode: object, dry_run: bool) -> str:
        suffix = " (dry-run)" if dry_run else ""
        deploy_mode_value = getattr(deploy_mode, "value", str(deploy_mode))
        lines = [
            f"Migration summary{suffix}:",
            f"  deploy mode: {deploy_mode_value}",
        ]
        for summary_field in dataclass_fields(self):
            field_name = summary_field.name
            value = getattr(self, field_name)
            label = SUMMARY_LABELS.get(field_name, field_name.replace("_", " "))
            lines.append(f"  {label}: {value}")
        return "\n".join(lines)


@dataclass
class ConversionResult:
    summary: MigrationSummary = field(default_factory=MigrationSummary)
    artifacts: list[PlannedArtifact] = field(default_factory=list)
    report_items: list[MigrationReportItem] = field(default_factory=list)

    def add(self, other: ConversionResult) -> None:
        self.summary.add(other.summary)
        self.artifacts.extend(other.artifacts)
        self.report_items.extend(other.report_items)

    def prefixed(self, prefix: Path) -> ConversionResult:
        return ConversionResult(
            summary=self.summary,
            artifacts=[artifact.prefixed(prefix) for artifact in self.artifacts],
            report_items=[
                MigrationReportItem(
                    item.status,
                    prefix / item.path,
                    item.detail,
                )
                for item in self.report_items
            ],
        )


def json_object(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def json_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def json_string_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item) for item in value)
    return (str(value),)


def load_scope_settings(scope_root: Path) -> Mapping[str, object]:
    settings: dict[str, object] = {}
    for rel in CLAUDE_SETTINGS_JSON_RELATIVE:
        outcome = read_json_mapping_file(scope_root / rel)
        if outcome.exists and outcome.ok:
            settings.update(json_object(outcome.data))
    return settings


def format_bullets(values: Sequence[str], prefix: str = "") -> str:
    return "\n".join(f"- {prefix}{value}" for value in values)


def format_manual_migration_block(notes: Sequence[str]) -> str:
    return "## MANUAL MIGRATION REQUIRED\n\n" + "\n\n".join(
        note.rstrip() for note in notes if note.strip()
    )


def unsupported_frontmatter_fields(
    frontmatter_values: Mapping[str, YamlValue],
    supported_fields: Sequence[str],
) -> tuple[str, ...]:
    supported = frozenset(supported_fields)
    return tuple(
        sorted(
            field_name
            for field_name in frontmatter_values
            if field_name not in supported
        )
    )


def append_report_item(
    report_items: list[MigrationReportItem],
    requires_manual_fix: object,
    path: Path,
    manual_detail: str,
    rewritten_detail: str,
) -> None:
    if requires_manual_fix:
        report_items.append(manual_report_item(path, manual_detail))
        return
    report_items.append(MigrationReportItem("rewritten", path, rewritten_detail))


def manual_report_item(path: Path, detail: str) -> MigrationReportItem:
    return MigrationReportItem("manual_fix_required", path, detail)


def report_manual_paths(
    scope: ScopePaths,
    path_labels: Sequence[tuple[Path, str]],
) -> ConversionResult:
    result = ConversionResult()

    for relative_path, label in path_labels:
        if path_exists_with_exact_case(scope.source / relative_path):
            result.report_items.append(
                manual_report_item(
                    relative_path,
                    f"Manual review required for {label}; not converted by this tool.",
                )
            )

    return result


def path_exists_with_exact_case(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return path.name in {child.name for child in path.parent.iterdir()}
    except FileNotFoundError:
        return False


def is_path_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def parse_frontmatter(content: str, path: Path | None = None) -> ParsedDocument:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return ParsedDocument(SimpleYamlFrontmatter({}), content, path)

    raw_frontmatter, body = match.groups()
    return ParsedDocument(parse_yaml_frontmatter(raw_frontmatter, path), body, path)


def parse_yaml_frontmatter(
    content: str,
    path: Path | None = None,
) -> SimpleYamlFrontmatter:
    return SimpleYamlFrontmatter(parse_yaml_mapping(content))


def format_frontmatter(frontmatter: SimpleYamlFrontmatter, body: str) -> str:
    rendered = format_yaml_mapping(frontmatter.to_dict())
    return f"---\n{rendered}\n---\n\n{body.lstrip()}"


def map_model_name(model: str) -> str:
    for mapping in MODEL_PREFIX_MAPPINGS:
        if model.startswith(mapping.source_prefix):
            return mapping.target_model
    return model


def map_model_effort(model: str | None, effort: str) -> str:
    if not model:
        return effort
    for mapping in MODEL_PREFIX_MAPPINGS:
        if model.startswith(mapping.source_prefix):
            return mapping.map_effort(effort)
    return effort


def map_permission_mode(permission_mode: str | None) -> str | None:
    if not permission_mode:
        return None
    return PERMISSION_MODE_MAPPINGS.get(permission_mode)
