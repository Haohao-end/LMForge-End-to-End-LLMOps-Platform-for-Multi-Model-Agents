from __future__ import annotations

import glob
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias


YamlScalar: TypeAlias = str | bool | int | float | None
YamlValue: TypeAlias = YamlScalar | Sequence[YamlScalar]
TomlScalar: TypeAlias = str | bool | int | float | None
TomlValue: TypeAlias = object


def detected_json_keys(content: str, keys: Sequence[str]) -> tuple[str, ...]:
    return tuple(key for key in keys if re.search(rf'"{re.escape(key)}"\s*:', content))


def strip_jsonc_comments(content: str) -> str:
    lines: list[str] = []
    for line in content.splitlines():
        in_string = False
        escaped = False
        result: list[str] = []
        index = 0
        while index < len(line):
            char = line[index]
            if escaped:
                result.append(char)
                escaped = False
                index += 1
                continue
            if char == "\\" and in_string:
                result.append(char)
                escaped = True
                index += 1
                continue
            if char == '"':
                in_string = not in_string
                result.append(char)
                index += 1
                continue
            if (
                not in_string
                and char == "/"
                and index + 1 < len(line)
                and line[index + 1] == "/"
            ):
                break
            result.append(char)
            index += 1
        lines.append("".join(result))
    return "\n".join(lines)


def load_jsonc_object(content: str, json_object: callable) -> Mapping[str, object]:
    without_comments = strip_jsonc_comments(content)
    without_trailing_commas = re.sub(r",\s*([}\]])", r"\1", without_comments)
    return json_object(json.loads(without_trailing_commas))


def parse_jsonc_mapping_text(text: str) -> Mapping[str, object] | None:
    """Return the top-level JSON object, or None if the text is not a JSON object."""
    try:
        without_comments = strip_jsonc_comments(text)
        without_trailing_commas = re.sub(r",\s*([}\]])", r"\1", without_comments)
        parsed = json.loads(without_trailing_commas)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if isinstance(parsed, Mapping):
        return parsed
    return None


@dataclass(frozen=True)
class JsonMappingFileRead:
    exists: bool
    ok: bool
    data: Mapping[str, object]


def read_json_mapping_file(path: Path) -> JsonMappingFileRead:
    """Read a JSON/JSONC file. ``ok`` is False when the file exists but could not be parsed."""
    if not path.is_file():
        return JsonMappingFileRead(exists=False, ok=True, data={})
    text = path.read_text()
    parsed = parse_jsonc_mapping_text(text)
    if parsed is None:
        return JsonMappingFileRead(exists=True, ok=False, data={})
    return JsonMappingFileRead(exists=True, ok=True, data=parsed)


@dataclass(frozen=True)
class TomlMultilineString:
    value: str


def parse_yaml_mapping(content: str) -> dict[str, YamlValue]:
    """Parse the small YAML-frontmatter subset used by Claude metadata."""
    result: dict[str, YamlValue] = {}
    current_key: str | None = None

    for raw_line in content.splitlines():
        if not raw_line.strip():
            continue

        if raw_line.startswith("  - ") and current_key:
            current_value = result.setdefault(current_key, [])
            if not isinstance(current_value, list):
                current_value = [current_value]
                result[current_key] = current_value
            current_value.append(parse_yaml_value(raw_line[4:].strip()))
            continue

        key, separator, value = raw_line.partition(":")
        if not separator:
            continue

        current_key = key.strip()
        value = value.strip()
        result[current_key] = parse_yaml_value(value) if value else []

    return result


def parse_yaml_value(value: str) -> YamlValue:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        return tuple(
            parse_yaml_value(item)
            for item in split_delimited_values(value[1:-1])
            if item
        )
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def split_delimited_values(content: str) -> tuple[str, ...]:
    values: list[str] = []
    token: list[str] = []
    quote: str | None = None
    escaped = False
    for char in content:
        if escaped:
            token.append(char)
            escaped = False
            continue
        if char == "\\" and quote == '"':
            token.append(char)
            escaped = True
            continue
        if quote:
            token.append(char)
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            token.append(char)
            quote = char
            continue
        if char == ",":
            values.append("".join(token).strip())
            token = []
            continue
        token.append(char)
    values.append("".join(token).strip())
    return tuple(values)


def format_yaml_mapping(values: Mapping[str, YamlValue]) -> str:
    return "\n".join(
        f"{key}: {format_yaml_value(value)}" for key, value in values.items()
    )


def format_yaml_value(value: YamlValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "[" + ", ".join(format_yaml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def render_toml_document(values: Mapping[str, TomlValue]) -> str:
    lines: list[str] = []
    append_toml_entries(lines, values)
    for key, value in values.items():
        if isinstance(value, Mapping):
            append_toml_table(lines, (key,), value)
    return "\n".join(lines).rstrip() + "\n"


def append_toml_table(
    lines: list[str],
    path: tuple[str, ...],
    values: Mapping[str, TomlValue],
) -> None:
    append_blank_line(lines)
    lines.append("[" + ".".join(format_toml_key(path_part) for path_part in path) + "]")
    append_toml_entries(lines, values)

    for key, value in values.items():
        if isinstance(value, Mapping):
            append_toml_table(lines, (*path, key), value)


def append_toml_entries(lines: list[str], values: Mapping[str, TomlValue]) -> None:
    for key, value in values.items():
        if isinstance(value, Mapping):
            continue
        lines.append(f"{format_toml_key(key)} = {format_toml_value(value)}")


def append_blank_line(lines: list[str]) -> None:
    if lines and lines[-1]:
        lines.append("")


def format_toml_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    return json.dumps(key)


def format_toml_value(value: TomlValue) -> str:
    if isinstance(value, TomlMultilineString):
        return format_toml_multiline_string(value.value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return "[" + ", ".join(format_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def format_toml_multiline_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""{escaped}"""'


def slugify_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-").lower()
    return result or "migrated-command"


def first_markdown_heading(content: str) -> str | None:
    for line in content.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return None


def format_backtick_list(values: Sequence[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return f"`{values[0]}`"
    return ", ".join(f"`{value}`" for value in values[:-1]) + f", and `{values[-1]}`"


def normalize_source_scope_root(
    path: Path, source_scope_markers: Sequence[Path]
) -> Path:
    resolved = path
    for marker in source_scope_markers:
        if resolved.parts[-len(marker.parts) :] == marker.parts:
            return resolved.parents[len(marker.parts) - 1]
    return resolved


def resolve_source_root(source: str) -> Path:
    if not glob.has_magic(source):
        return Path(source)

    matches = [Path(match) for match in glob.glob(source, recursive=True)]
    if not matches:
        raise FileNotFoundError(f"No matches for source pattern: {source}")

    for match in matches:
        if (
            match.is_dir()
            and (match / "global").exists()
            and (match / "project").exists()
        ):
            return match

    static_prefix = source.split("*", 1)[0].rstrip("/")
    return Path(static_prefix)
