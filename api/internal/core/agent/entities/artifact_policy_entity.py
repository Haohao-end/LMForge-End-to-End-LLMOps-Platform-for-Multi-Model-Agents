from __future__ import annotations

import os
import re
import textwrap
from typing import Any, Callable
from xml.etree import ElementTree as ET


_FENCED_CODE_BLOCK_PATTERN = re.compile(
    r"```(?:[a-zA-Z0-9_+\-]+)?\s*\n(?P<body>.*?)\n```",
    re.IGNORECASE | re.DOTALL,
)
_WRITE_FILE_TOOL_CALL_PATTERN = re.compile(
    r"<tool_call>\s*write_file\s*<arg_key>path</arg_key><arg_value>(?P<path>.*?)"
    r"<arg_key>content</arg_key><arg_value>(?P<content>.*)",
    re.IGNORECASE | re.DOTALL,
)
_GENERATED_ARTIFACT_BLOCK_PATTERN = re.compile(
    r"(?is)<generated_artifacts>(?P<body>.*?)</generated_artifacts>",
)
_GENERATED_ARTIFACT_ENTRY_PATTERN = re.compile(
    r"(?is)<artifact\b(?P<attrs>[^>]*)>(?P<body>.*?)</artifact\s*>",
)
_ARTIFACT_ATTRIBUTE_PATTERN = re.compile(
    r'(?P<name>[A-Za-z_][\w:.-]*)\s*=\s*(?P<quote>["\'])(?P<value>.*?)(?P=quote)',
    re.DOTALL,
)
_REQUESTED_ARTIFACT_FILENAME_PATTERN = re.compile(
    r"(?is)(?:保存为|另存为|保存成|保存到|导出为|导出成|写入为|生成为|write as|save as|save to|output as|export as)\s*[:：]?\s*"
    r"(?P<filename>[^\s。！？；;，,、<>\"'`]{1,160}\.(?:txt|md|markdown|csv|json|html|docx|xlsx|pdf|py|ipynb|log))",
)
_ANY_ARTIFACT_FILENAME_PATTERN = re.compile(
    r"(?is)(?P<filename>[A-Za-z0-9_\-\u4e00-\u9fff./\\]{1,160}\.(?:txt|md|markdown|csv|json|html|docx|xlsx|pdf|py|ipynb|log))",
)
_GENERIC_ARTIFACT_TITLE_TOKENS = {
    "generate",
    "generated",
    "document",
    "documents",
    "file",
    "files",
    "attachment",
    "attachments",
    "download",
    "downloads",
    "save",
    "saved",
    "output",
    "outputs",
    "write",
    "written",
    "draft",
    "drafts",
    "report",
    "reports",
    "analysis",
    "analyses",
    "research",
    "proposal",
    "plan",
    "plans",
    "plan.",
    "txt",
    "md",
    "markdown",
    "json",
    "csv",
    "html",
    "xml",
    "yaml",
    "yml",
    "log",
    "prospectus",
    "travel",
    "trip",
    "itinerary",
}
_PLAIN_TEXT_ARTIFACT_PREAMBLE_PATTERNS = (
    re.compile(
        r"(?i)^(?:无法|不能|暂不|不支持|我无法|当前对话环境).*?(?:可下载附件|下载附件|可下载文件|附件)"
    ),
    re.compile(r"(?i)^(?:您可以|请(?:您|你)?).*?(?:复制|保存).*(?:以下|全部内容|完整内容)"),
    re.compile(r"(?i)^(?:以下为|以下内容|下面为).*(?:完整|可直接复制|复制保存)"),
    re.compile(r"(?i)^说明[:：]"),
)
_PLAIN_TEXT_ARTIFACT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".html",
    ".htm",
    ".xml",
    ".yaml",
    ".yml",
    ".py",
    ".log",
    ".tsv",
}
_STRUCTURED_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".html",
    ".htm",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
}
_ARTIFACT_SUFFIX_EXTENSIONS = _STRUCTURED_DOCUMENT_EXTENSIONS | {
    ".docx",
    ".xlsx",
    ".pdf",
    ".ipynb",
}
_PYTHON_PATH_ASSIGNMENT_NAMES = (
    "file_path",
    "filepath",
    "path",
    "output_path",
    "target_path",
    "destination_path",
    "dest_path",
    "filename",
)
_PYTHON_CONTENT_ASSIGNMENT_NAMES = (
    "content",
    "file_content",
    "text",
    "payload",
    "document",
    "body",
)
_XML_TOOL_CALL_TAG_NAMES = {"tool_call", "invoke", "tool", "function"}
_XML_PARAMETER_TAG_NAMES = {"parameter", "param", "arg"}
_XML_WRITE_FILE_TOOL_NAMES = {"write_file", "save_file"}
_XML_WRITE_FILE_PATH_NAMES = (
    "file_name",
    "path",
    "filepath",
    "file_path",
    "output_path",
    "destination_path",
    "dest_path",
    "filename",
)
_XML_WRITE_FILE_CONTENT_NAMES = (
    "content",
    "file_content",
    "text",
    "payload",
    "document",
    "body",
)
_ARTIFACT_FILENAME_NAMES = (
    "file_name",
    "path",
    "filepath",
    "file_path",
    "output_path",
    "destination_path",
    "dest_path",
    "filename",
)
_ARTIFACT_TITLE_NAMES = (
    "title",
    "name",
)


class ArtifactPolicy:
    """文档型 artifact 的命名、解析与清洗策略。"""

    @staticmethod
    def _normalize_requested_artifact_filename(candidate: str) -> str:
        normalized = str(candidate or "").strip().strip("`'\"")
        if not normalized:
            return ""

        normalized = normalized.replace("\\", "/")
        normalized = os.path.basename(normalized)
        normalized = normalized.strip(" .。、；;，,：:!！?？")
        if not normalized:
            return ""
        if not os.path.splitext(normalized)[1]:
            normalized = f"{normalized}.txt"
        return normalized

    @classmethod
    def _build_generated_artifact_filename(cls, title: str) -> str:
        candidate = str(title or "").strip()
        if not candidate:
            return ""

        candidate = candidate.replace("\\", "_").replace("/", "_")
        candidate = re.sub(r"\s+", "_", candidate, flags=re.UNICODE)
        candidate = re.sub(r"[^\w.\-]+", "_", candidate, flags=re.UNICODE)
        candidate = candidate.strip("._")
        if not candidate:
            return ""
        if not os.path.splitext(candidate)[1]:
            candidate = f"{candidate}.txt"
        return candidate

    @classmethod
    def build_generated_artifact_filename(cls, title: str) -> str:
        return cls._build_generated_artifact_filename(title)

    @classmethod
    def _infer_document_title_from_text(cls, text: str) -> str:
        normalized = textwrap.dedent(str(text or "")).strip()
        if not normalized:
            return ""

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        if not lines:
            return ""

        for line in lines[:8]:
            if line.startswith("#"):
                candidate = line.lstrip("#").strip()
                if candidate:
                    return candidate

        title_lines: list[str] = []
        for line in lines[:6]:
            if cls._looks_like_plain_text_artifact_preamble_line(line):
                continue
            if line.startswith(("```", "-", "*", "|", ">", "(", ")", "=", "—")):
                continue
            if len(line) > 120:
                continue
            title_lines.append(line)
            if len(title_lines) >= 2:
                break

        return " ".join(title_lines[:2]).strip()

    @classmethod
    def _looks_like_plain_text_artifact_preamble_line(cls, line: str) -> bool:
        normalized = str(line or "").strip()
        if not normalized:
            return False

        if normalized in {"text", "markdown", "md", "txt", "python", "复制代码"}:
            return True

        if normalized.startswith("说明：") or normalized.startswith("说明:"):
            return True

        return any(pattern.search(normalized) for pattern in _PLAIN_TEXT_ARTIFACT_PREAMBLE_PATTERNS)

    @classmethod
    def _contains_plain_text_artifact_preamble(cls, text: str) -> bool:
        if not text:
            return False

        for raw_line in str(text).splitlines():
            if cls._looks_like_plain_text_artifact_preamble_line(raw_line):
                return True
        return False

    @classmethod
    def contains_plain_text_artifact_preamble(cls, text: str) -> bool:
        return cls._contains_plain_text_artifact_preamble(text)

    @classmethod
    def _infer_artifact_title(cls, query: str, deep_answer: str = "") -> str:
        normalized = str(query or "").strip()
        lower = normalized.lower()

        if any(keyword in normalized for keyword in ("招股说明书", "招股書", "招股书")) or "prospectus" in lower:
            title_parts: list[str] = []
            latin_tokens = [
                token
                for token in re.findall(r"\b[A-Za-z][A-Za-z0-9&._-]{1,}\b", normalized)
                if token.lower() not in _GENERIC_ARTIFACT_TITLE_TOKENS
            ]
            if any(token.lower() == "spacex" for token in latin_tokens):
                title_parts.append("SpaceX")
            elif latin_tokens:
                title_parts.append(latin_tokens[0])
            if "ipo" in lower or "IPO" in normalized:
                title_parts.append("IPO")
            title_parts.append("Prospectus Draft")
            return " ".join(title_parts).strip() or "Prospectus Draft"

        if any(keyword in normalized for keyword in ("旅行", "行程", "旅游", "游玩", "trip", "travel", "itinerary")):
            content_title = cls._infer_document_title_from_text(deep_answer)
            if content_title:
                return content_title
            return "Travel Plan"

        if any(keyword in lower for keyword in ("report", "analysis", "research", "proposal")) or any(
            keyword in normalized for keyword in ("报告", "分析", "研究", "提案")
        ):
            return "Report"

        content_title = cls._infer_document_title_from_text(deep_answer)
        if content_title:
            return content_title

        if any(keyword in normalized for keyword in ("文档", "文件", "附件")):
            return "Generated Document"

        return "Generated Document"

    @classmethod
    def _infer_artifact_extension(cls, query: str, deep_answer: str = "") -> str:
        normalized = f"{str(query or '').strip()}\n{str(deep_answer or '').strip()}".strip()
        lower = normalized.lower()

        if "markdown" in lower or ".md" in lower:
            return ".md"
        if ".html" in lower or " html " in f" {lower} ":
            return ".html"
        if ".htm" in lower or " htm " in f" {lower} ":
            return ".htm"
        if ".json" in lower or " json " in f" {lower} ":
            return ".json"
        if ".csv" in lower or " csv " in f" {lower} ":
            return ".csv"
        if ".xml" in lower or " xml " in f" {lower} ":
            return ".xml"
        if ".yaml" in lower or " yaml " in f" {lower} " or ".yml" in lower or " yml " in f" {lower} ":
            return ".yaml"
        if ".log" in lower or " log " in f" {lower} ":
            return ".log"
        if ".tsv" in lower or " tsv " in f" {lower} ":
            return ".tsv"
        if ".py" in lower or " python " in f" {lower} ":
            return ".py"

        if any(keyword in normalized for keyword in ("招股说明书", "招股書", "招股书")) or "prospectus" in lower:
            return ".txt"

        if any(keyword in normalized for keyword in ("旅行", "行程", "旅游", "游玩", "trip", "travel", "itinerary")):
            return ".md"

        if any(keyword in lower for keyword in ("report", "analysis", "research", "proposal")) or any(
            keyword in normalized for keyword in ("报告", "分析", "研究", "提案")
        ):
            return ".md"

        return ".txt"

    @classmethod
    def infer_requested_artifact_filename(cls, query: str, deep_answer: str = "") -> str:
        for source in (query, deep_answer):
            if not source:
                continue

            text = str(source)
            match = _REQUESTED_ARTIFACT_FILENAME_PATTERN.search(text)
            if match:
                filename = cls._normalize_requested_artifact_filename(match.group("filename"))
                if filename:
                    return filename

            if not any(keyword in text for keyword in ("保存", "导出", "生成", "文件", "附件", "save", "export", "write")):
                continue

            for candidate in _ANY_ARTIFACT_FILENAME_PATTERN.findall(text):
                filename = cls._normalize_requested_artifact_filename(candidate)
                if filename:
                    return filename

        return ""

    @classmethod
    def resolve_artifact_filename(
        cls,
        query: str,
        deep_answer: str = "",
        *,
        allow_default_filename: bool = False,
    ) -> str:
        explicit_filename = cls.infer_requested_artifact_filename(query, deep_answer)
        if explicit_filename:
            return explicit_filename
        if not allow_default_filename:
            return ""

        title = cls._infer_artifact_title(query, deep_answer)
        extension = cls._infer_artifact_extension(query, deep_answer)
        candidate = cls._build_generated_artifact_filename(f"{title}{extension}")
        if candidate:
            return candidate

        fallback_title = cls._build_generated_artifact_filename(f"Generated Document{extension}")
        return fallback_title or ""

    @classmethod
    def humanize_filename_stem(cls, filename: str) -> str:
        stem = os.path.basename(str(filename or "").strip()).strip()
        while True:
            next_stem, extension = os.path.splitext(stem)
            if not extension or extension.lower() not in _ARTIFACT_SUFFIX_EXTENSIONS:
                break
            stem = next_stem.strip()
        if not stem:
            return "Generated Document"
        stem = stem.replace("_", " ").replace("-", " ")
        stem = re.sub(r"\s+", " ", stem, flags=re.UNICODE).strip()
        return stem or "Generated Document"

    @classmethod
    def is_text_document_artifact_extension(cls, filename: str) -> bool:
        extension = os.path.splitext(str(filename or "").strip().lower())[1]
        return extension in _STRUCTURED_DOCUMENT_EXTENSIONS

    @classmethod
    def score_plain_text_artifact_content(cls, text: str) -> tuple[int, int, int, int]:
        normalized = str(text or "").strip()
        if not normalized:
            return (0, 0, 0, 0)

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        markers = (
            "PROSPECTUS",
            "招股说明书",
            "PROSPECTUS SUMMARY",
            "RISK FACTORS",
            "BUSINESS",
            "MD&A",
            "USE OF PROCEEDS",
            "LEGAL",
            "第一章",
            "第二章",
            "第三章",
            "封面摘要",
            "业务概览",
            "风险因素",
            "募集资金用途",
            "法律声明",
        )
        upper_text = normalized.upper()
        section_hits = sum(1 for marker in markers if marker.upper() in upper_text)
        heading_hits = sum(
            1
            for line in lines
            if (
                line.startswith("#")
                or re.match(r"^\d+(?:\.\d+)*\s+", line)
                or re.match(r"^[一二三四五六七八九十]+[、\.]", line)
            )
        )
        return (section_hits, heading_hits, len(lines), len(normalized))

    @classmethod
    def looks_like_plain_text_artifact_content(cls, text: str) -> bool:
        normalized = str(text or "").strip()
        if not normalized:
            return False

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        markers = (
            "PROSPECTUS",
            "招股说明书",
            "PROSPECTUS SUMMARY",
            "RISK FACTORS",
            "BUSINESS",
            "MD&A",
            "USE OF PROCEEDS",
            "LEGAL",
            "第一章",
            "第二章",
            "第三章",
            "封面摘要",
            "业务概览",
            "风险因素",
            "募集资金用途",
            "法律声明",
        )
        upper_text = normalized.upper()
        section_hits = sum(1 for marker in markers if marker.upper() in upper_text)
        if section_hits >= 2 and len(lines) >= 4 and len(normalized) >= 180:
            return True

        if len(lines) >= 6 and normalized.startswith("#") and len(normalized) >= 240:
            return True

        if len(normalized) >= 800 and len(lines) >= 8:
            return True

        return section_hits >= 1 and len(normalized) >= 1200 and len(lines) >= 10

    @classmethod
    def strip_plain_text_artifact_preamble(cls, text: str) -> str:
        if not text:
            return ""

        sanitized_lines: list[str] = []
        for raw_line in str(text).splitlines():
            line = raw_line.strip()
            if cls._looks_like_plain_text_artifact_preamble_line(line):
                continue

            sanitized_lines.append(raw_line)

        return "\n".join(sanitized_lines).strip()

    @classmethod
    def select_plain_text_artifact_source(
        cls,
        query: str,
        *candidates: str,
        sanitize_text: Callable[[str], str] | None = None,
    ) -> str:
        sanitize = sanitize_text or (lambda value: value)
        for candidate in candidates:
            normalized_candidate = cls.strip_plain_text_artifact_preamble(candidate)
            normalized_candidate = sanitize(normalized_candidate)
            if not normalized_candidate:
                continue

            if not cls.looks_like_plain_text_artifact_content(normalized_candidate):
                continue

            return normalized_candidate

        return ""

    @classmethod
    def build_plain_text_artifact_payload(
        cls,
        query: str,
        deep_answer: str,
        *,
        allow_default_filename: bool = False,
        sanitize_text: Callable[[str], str] | None = None,
    ) -> tuple[str, str] | None:
        filename = cls.resolve_artifact_filename(
            query,
            deep_answer,
            allow_default_filename=allow_default_filename,
        )
        if not filename:
            return None

        if os.path.splitext(filename)[1].lower() not in _PLAIN_TEXT_ARTIFACT_EXTENSIONS:
            return None

        sanitize = sanitize_text or (lambda value: value)
        content = cls.strip_plain_text_artifact_preamble(deep_answer)
        content = sanitize(content)
        if not content or not cls.looks_like_plain_text_artifact_content(content):
            return None

        return filename, content

    @classmethod
    def _normalize_xml_tool_call_text(cls, text: str) -> str:
        """将带命名空间前缀的工具调用 XML 规范化为可解析的本地标签。"""
        if not text:
            return ""

        def _replace_tag(match: re.Match[str]) -> str:
            raw = match.group(0)
            local_tag = str(match.group("tag") or "").lower()
            prefix = "/" if raw.startswith("</") else ""
            return f"<{prefix}{local_tag}"

        return re.sub(
            r"</?(?:[\w.-]+:)?(?P<tag>tool_call|invoke|tool|function|parameter|param|arg)\b",
            _replace_tag,
            str(text),
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _xml_local_tag_name(tag: Any) -> str:
        raw = str(tag or "")
        if "}" in raw:
            raw = raw.rsplit("}", 1)[-1]
        if ":" in raw:
            raw = raw.rsplit(":", 1)[-1]
        return raw.lower().strip()

    @classmethod
    def _pick_first_parameter_value(cls, params: dict[str, str], names: tuple[str, ...]) -> str:
        for name in names:
            value = str(params.get(name, "") or "").strip()
            if value:
                return value
        return ""

    @classmethod
    def _extract_xml_write_file_payload_from_root(cls, root: ET.Element) -> tuple[str, str] | None:
        for element in root.iter():
            if cls._xml_local_tag_name(element.tag) not in _XML_TOOL_CALL_TAG_NAMES:
                continue

            tool_name = str(element.attrib.get("name", "") or "").strip().lower()
            if tool_name not in _XML_WRITE_FILE_TOOL_NAMES:
                continue

            params: dict[str, str] = {}
            for child in element.iter():
                if child is element:
                    continue
                if cls._xml_local_tag_name(child.tag) not in _XML_PARAMETER_TAG_NAMES:
                    continue

                param_name = str(child.attrib.get("name", "") or "").strip().lower()
                if not param_name or param_name in params:
                    continue

                value = textwrap.dedent("".join(child.itertext())).strip()
                if value:
                    params[param_name] = value

            path = cls._pick_first_parameter_value(params, _XML_WRITE_FILE_PATH_NAMES)
            content = cls._pick_first_parameter_value(params, _XML_WRITE_FILE_CONTENT_NAMES)
            if path and content:
                return path, content

        return None

    @classmethod
    def extract_xml_write_file_payload(cls, text: str) -> tuple[str, str] | None:
        if not text:
            return None

        normalized = cls._normalize_xml_tool_call_text(text)
        if normalized:
            try:
                root = ET.fromstring(f"<root>{normalized}</root>")
            except ET.ParseError:
                root = None
            if root is not None:
                payload = cls._extract_xml_write_file_payload_from_root(root)
                if payload is not None:
                    return payload

        xml_pattern = re.compile(
            r"(?is)<(?:[\w.-]+:)?(?P<tag>invoke|tool|function)\b[^>]*\bname\s*=\s*(?P<quote>['\"])(?P<tool_name>write_file|save_file)(?P=quote)[^>]*>(?P<body>.*?)</(?:[\w.-]+:)?(?P=tag)\s*>",
            re.IGNORECASE | re.DOTALL,
        )
        parameter_pattern = re.compile(
            r"(?is)<(?:[\w.-]+:)?parameter\b[^>]*\bname\s*=\s*(?P<quote>['\"])(?P<name>[^'\"]+)(?P=quote)[^>]*>(?P<value>.*?)</(?:[\w.-]+:)?parameter\s*>",
            re.IGNORECASE | re.DOTALL,
        )
        for match in xml_pattern.finditer(str(text)):
            body = str(match.group("body") or "")
            params: dict[str, str] = {}
            for parameter_match in parameter_pattern.finditer(body):
                param_name = str(parameter_match.group("name") or "").strip().lower()
                if not param_name or param_name in params:
                    continue
                value = textwrap.dedent(str(parameter_match.group("value") or "")).strip()
                if value:
                    params[param_name] = value

            path = cls._pick_first_parameter_value(params, _XML_WRITE_FILE_PATH_NAMES)
            content = cls._pick_first_parameter_value(params, _XML_WRITE_FILE_CONTENT_NAMES)
            if path and content:
                return path, content

        return None

    @classmethod
    def parse_attribute_pairs(cls, text: str) -> dict[str, str]:
        attrs: dict[str, str] = {}
        for match in _ARTIFACT_ATTRIBUTE_PATTERN.finditer(str(text or "")):
            name = str(match.group("name") or "").strip().lower()
            if not name or name in attrs:
                continue
            value = textwrap.dedent(str(match.group("value") or "")).strip()
            if value:
                attrs[name] = value
        return attrs

    @classmethod
    def extract_generated_artifact_payloads(cls, text: str) -> list[tuple[str, str]]:
        if not text or "<generated_artifacts>" not in text:
            return []

        payloads: list[tuple[str, str]] = []
        for block in _GENERATED_ARTIFACT_BLOCK_PATTERN.finditer(str(text)):
            body = str(block.group("body") or "")
            for match in _GENERATED_ARTIFACT_ENTRY_PATTERN.finditer(body):
                attrs = cls.parse_attribute_pairs(match.group("attrs"))
                content = textwrap.dedent(str(match.group("body") or ""))
                content = re.sub(r"</?(?:generated_artifacts|artifact)>\s*$", "", content, flags=re.IGNORECASE)
                content = content.strip()
                if not content:
                    continue

                path = cls._pick_first_parameter_value(attrs, _ARTIFACT_FILENAME_NAMES)
                if not path:
                    title = cls._pick_first_parameter_value(attrs, _ARTIFACT_TITLE_NAMES)
                    path = cls._build_generated_artifact_filename(title)

                if path:
                    payloads.append((path, content))

        return payloads

    @classmethod
    def extract_code_blocks(cls, text: str) -> list[str]:
        blocks: list[str] = []
        for match in _FENCED_CODE_BLOCK_PATTERN.finditer(str(text or "")):
            body = str(match.group("body") or "").strip()
            if body:
                blocks.append(body)
        return blocks

    @classmethod
    def _extract_quoted_assignment_value(cls, text: str, variable_names: tuple[str, ...]) -> str:
        if not text:
            return ""

        variable_pattern = "|".join(re.escape(name) for name in variable_names)
        assignment_pattern = re.compile(
            rf"(?im)^\s*(?:{variable_pattern})\s*=\s*(?:Path\(\s*)?(?P<quote>'''|\"\"\"|'|\")",
            re.MULTILINE,
        )
        match = assignment_pattern.search(str(text))
        if not match:
            return ""

        quote = str(match.group("quote") or "")
        if not quote:
            return ""

        start = match.end()
        end = str(text).find(quote, start)
        if end < 0:
            end = len(str(text))

        value = str(text)[start:end]
        value = re.sub(r"\s*```[\w+\-]*\s*$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"</?(?:tool_call|arg_key|arg_value)>\s*$", "", value, flags=re.IGNORECASE)
        return textwrap.dedent(value).strip()

    @classmethod
    def extract_direct_write_file_payload(cls, text: str) -> tuple[str, str] | None:
        if not text:
            return None

        direct_pattern = re.compile(
            r"(?is)\b(?:write_file|save_file)\s*\(\s*(?P<path_quote>'''|\"\"\"|'|\")"
            r"(?P<path>.*?)(?P=path_quote)\s*,\s*(?P<content_quote>'''|\"\"\"|'|\")"
            r"(?P<content>.*?)(?P=content_quote)\s*\)",
            re.DOTALL,
        )
        match = direct_pattern.search(str(text))
        if not match:
            return None

        path = textwrap.dedent(str(match.group("path") or "")).strip()
        content = textwrap.dedent(str(match.group("content") or ""))
        content = re.sub(r"\s*```[\w+\-]*\s*$", "", content, flags=re.IGNORECASE)
        content = re.sub(r"</?(?:tool_call|arg_key|arg_value)>\s*$", "", content, flags=re.IGNORECASE)
        content = content.strip()
        if not path or not content:
            return None
        return path, content

    @classmethod
    def extract_python_write_file_payload(cls, text: str) -> tuple[str, str] | None:
        if not text:
            return None

        candidate_text = str(text)
        path = cls._extract_quoted_assignment_value(candidate_text, _PYTHON_PATH_ASSIGNMENT_NAMES)
        if not path:
            direct_path_pattern = re.compile(
                r"(?is)\b(?:write_file|save_file|open)\s*\(\s*(?P<quote>'''|\"\"\"|'|\")(?P<path>.*?)(?P=quote)",
                re.DOTALL,
            )
            direct_path_match = direct_path_pattern.search(candidate_text)
            if direct_path_match:
                path = textwrap.dedent(str(direct_path_match.group("path") or "")).strip()

        content = cls._extract_quoted_assignment_value(candidate_text, _PYTHON_CONTENT_ASSIGNMENT_NAMES)
        if not content:
            direct_payload = cls.extract_direct_write_file_payload(candidate_text)
            if direct_payload is not None:
                path, content = direct_payload

        if not path or not content:
            return None
        return path, content

    @classmethod
    def extract_write_file_payload(cls, deep_answer: str) -> tuple[str, str] | None:
        if not deep_answer:
            return None

        payload = cls.extract_xml_write_file_payload(deep_answer)
        if payload is not None:
            return payload

        generated_artifacts = cls.extract_generated_artifact_payloads(deep_answer)
        if generated_artifacts:
            return generated_artifacts[0]

        match = _WRITE_FILE_TOOL_CALL_PATTERN.search(str(deep_answer))
        if not match:
            for code_block in cls.extract_code_blocks(deep_answer):
                payload = cls.extract_python_write_file_payload(code_block)
                if payload is not None:
                    return payload
            payload = cls.extract_python_write_file_payload(str(deep_answer))
            if payload is not None:
                return payload
            return None

        path = str(match.group("path") or "").strip()
        content = str(match.group("content") or "")
        content = re.sub(r"</?(?:tool_call|arg_key|arg_value)>", "", content, flags=re.IGNORECASE)
        content = content.strip()
        if not path or not content:
            return None
        return path, content
