"""Convert supported Claude Code hooks into Codex hook config."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from migrate.common import (
    ConversionResult,
    GeneratedText,
    MigrationReportItem,
    PlannedArtifact,
    ScopePaths,
    json_object,
    json_string,
    path_exists_with_exact_case,
    read_json_mapping_file,
)
from migrate.settings import CLAUDE_SETTINGS_JSON_RELATIVE


CODEX_HOOKS_PATH = Path(".codex") / "hooks.json"
CODEX_HOOK_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
)
CODEX_HOOK_MATCHER_EVENTS = frozenset(("PreToolUse", "PostToolUse", "SessionStart"))


@dataclass(frozen=True)
class ClaudeHookCommand:
    command: str
    timeout_sec: int | None = None
    status_message: str | None = None

    @classmethod
    def from_mapping(cls, hook_config: Mapping[str, object]) -> ClaudeHookCommand | None:
        command = json_string(hook_config.get("command"))
        if command is None or not command.strip():
            return None

        timeout_value = hook_config.get("timeout")
        if timeout_value is None:
            timeout_value = hook_config.get("timeoutSec")

        return cls(
            command=command,
            timeout_sec=json_int(timeout_value),
            status_message=json_string(hook_config.get("statusMessage")),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "type": "command",
            "command": self.command,
        }
        if self.timeout_sec is not None:
            result["timeout"] = self.timeout_sec
        if self.status_message is not None:
            result["statusMessage"] = self.status_message
        return result


@dataclass(frozen=True)
class ClaudeHookMatcherGroup:
    event_name: str
    matcher: str | None
    hooks: tuple[ClaudeHookCommand, ...]

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "hooks": [hook.to_mapping() for hook in self.hooks],
        }
        if self.matcher is not None:
            result["matcher"] = self.matcher
        return result


@dataclass(frozen=True)
class ClaudeHooks:
    matcher_groups: tuple[ClaudeHookMatcherGroup, ...] = ()
    source_paths: tuple[Path, ...] = ()
    unsupported_fields: tuple[str, ...] = ()

    @classmethod
    def from_scope(cls, scope_root: Path) -> ClaudeHooks:
        hook_sets = [
            cls.from_settings_mapping(relative_path, outcome.data)
            for relative_path in CLAUDE_SETTINGS_JSON_RELATIVE
            if path_exists_with_exact_case(scope_root / relative_path)
            for outcome in (read_json_mapping_file(scope_root / relative_path),)
            if outcome.exists and outcome.ok
        ]
        return cls(
            matcher_groups=tuple(
                matcher_group
                for hook_set in hook_sets
                for matcher_group in hook_set.matcher_groups
            ),
            source_paths=tuple(
                source_path
                for hook_set in hook_sets
                for source_path in hook_set.source_paths
            ),
            unsupported_fields=tuple(
                unsupported_field
                for hook_set in hook_sets
                for unsupported_field in hook_set.unsupported_fields
            ),
        )

    @classmethod
    def from_settings_mapping(
        cls,
        relative_path: Path,
        settings: Mapping[str, object],
    ) -> ClaudeHooks:
        hooks_config = json_object(settings.get("hooks"))
        if not hooks_config:
            return cls()

        matcher_groups: list[ClaudeHookMatcherGroup] = []
        unsupported_fields: list[str] = []
        for event_name, groups_value in hooks_config.items():
            if event_name not in CODEX_HOOK_EVENTS:
                unsupported_fields.append(f"hooks.{event_name}")
                continue

            for group_config in json_object_tuple(groups_value):
                matcher = json_string(group_config.get("matcher"))
                if matcher is not None and event_name not in CODEX_HOOK_MATCHER_EVENTS:
                    unsupported_fields.append(f"hooks.{event_name}.matcher")
                    matcher = None
                if "if" in group_config:
                    unsupported_fields.append(f"hooks.{event_name}.if")

                hook_commands: list[ClaudeHookCommand] = []
                for hook_config in json_object_tuple(group_config.get("hooks")):
                    hook_type = json_string(hook_config.get("type")) or "command"
                    if hook_type != "command":
                        unsupported_fields.append(
                            f"hooks.{event_name}.hooks[].type:{hook_type}"
                        )
                        continue
                    if bool(hook_config.get("async")):
                        unsupported_fields.append(f"hooks.{event_name}.hooks[].async")
                        continue

                    hook_command = ClaudeHookCommand.from_mapping(hook_config)
                    if hook_command is None:
                        unsupported_fields.append(f"hooks.{event_name}.hooks[].command")
                        continue
                    hook_commands.append(hook_command)

                if hook_commands:
                    matcher_groups.append(
                        ClaudeHookMatcherGroup(
                            event_name=event_name,
                            matcher=matcher,
                            hooks=tuple(hook_commands),
                        )
                    )

        return cls(
            matcher_groups=tuple(matcher_groups),
            source_paths=(relative_path,),
            unsupported_fields=tuple(sorted(set(unsupported_fields))),
        )

    def render_codex_file(self) -> str:
        hooks_payload: dict[str, list[dict[str, object]]] = {}
        for matcher_group in self.matcher_groups:
            hooks_payload.setdefault(matcher_group.event_name, []).append(
                matcher_group.to_mapping()
            )
        return json.dumps({"hooks": hooks_payload}, indent=2) + "\n"

    def report_detail(self) -> str:
        runtime_caveats = (
            "Rewritten for Codex hooks; review behavior before relying on it. "
            "Codex hooks require `[features].codex_hooks = true`, only execute "
            "`command` handlers, skip `async` / `prompt` / `agent` handlers, ignore "
            "`matcher` for `UserPromptSubmit` and `Stop`, and `PreToolUse` / "
            "`PostToolUse` currently run for shell commands only."
        )
        if not self.unsupported_fields:
            return runtime_caveats
        return (
            "Unsupported Claude hook fields need review: "
            + ", ".join(f"`{field_name}`" for field_name in self.unsupported_fields)
            + f". {runtime_caveats}"
        )


def has_convertible_hooks(scope_root: Path) -> bool:
    return bool(ClaudeHooks.from_scope(scope_root).matcher_groups)


def report_hooks(scope: ScopePaths) -> ConversionResult:
    claude_hooks = ClaudeHooks.from_scope(scope.source)
    if not claude_hooks.matcher_groups:
        return ConversionResult()

    return ConversionResult(
        artifacts=[
            PlannedArtifact(
                relative_path=CODEX_HOOKS_PATH,
                payload=GeneratedText(claude_hooks.render_codex_file()),
            )
        ],
        report_items=[
            MigrationReportItem(
                "rewritten",
                CODEX_HOOKS_PATH,
                claude_hooks.report_detail(),
            )
        ],
    )


def json_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def json_object_tuple(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(json_object(item) for item in value)
    return ()
