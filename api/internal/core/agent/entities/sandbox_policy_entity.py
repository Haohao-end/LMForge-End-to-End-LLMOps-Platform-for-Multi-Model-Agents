from __future__ import annotations

import os
import re
import shlex


_SANDBOX_DOWNLOAD_LINK_PATTERN = re.compile(
    r"\[([^\]]+)\]\(((?:sandbox:)?(?:/workspace|/home/user|/tmp|/mnt/data)/[^\s)]+)\)"
)
_SANDBOX_LOCAL_PATH_PATTERN = re.compile(
    r"(?:sandbox:)?(?:/workspace|/home/user|/tmp|/mnt/data)/(?:[^\s)>]+)"
)


class SandboxPolicy:
    """沙箱运行时默认值与用户可见文本清洗策略。"""

    default_sandbox_profile: str = "lite"
    default_sandbox_template_alias: str = "llmops-code-interpreter-lite"
    default_sandbox_fallback_template_alias: str = "code-interpreter-v1"
    default_sandbox_timeout_seconds: int = 1800
    default_execute_timeout_seconds: int = 600
    default_artifact_base_dirs: tuple[str, ...] = ("/workspace", "/home/user", "/tmp", "/mnt/data")
    document_build_base_dir: str = "/tmp/openagent_doc_build"
    code_interpreter_data_dir: str = "/mnt/data"
    artifact_marker_prefix: str = ".openagent_artifact_marker_"

    @classmethod
    def build_default_artifact_root(cls, task_id: object) -> str:
        return f"/workspace/artifacts/{task_id}"

    @classmethod
    def build_candidate_artifact_roots(cls, primary_root: str) -> list[str]:
        normalized_primary = (primary_root or "").rstrip("/")
        task_id_segment = os.path.basename(normalized_primary)
        roots = [normalized_primary] if normalized_primary else []
        if task_id_segment:
            roots.extend(f"{base}/artifacts/{task_id_segment}" for base in cls.default_artifact_base_dirs)

        unique_roots: list[str] = []
        for root in roots:
            if root and root not in unique_roots:
                unique_roots.append(root)
        return unique_roots

    @classmethod
    def build_fallback_artifact_roots(cls, primary_root: str) -> list[str]:
        normalized_primary = (primary_root or "").rstrip("/")
        roots = []
        if normalized_primary:
            parent_root = os.path.dirname(normalized_primary.rstrip("/"))
            if parent_root and parent_root != "/":
                roots.append(parent_root)
        roots.extend(f"{base}/artifacts" for base in cls.default_artifact_base_dirs)
        roots.append(cls.code_interpreter_data_dir)

        unique_roots: list[str] = []
        for root in roots:
            if root and root not in unique_roots:
                unique_roots.append(root)
        return unique_roots

    @classmethod
    def build_artifact_marker_name(cls, primary_root: str) -> str:
        task_id_segment = os.path.basename((primary_root or "").rstrip("/"))
        if not task_id_segment:
            return f"{cls.artifact_marker_prefix}artifacts"
        return f"{cls.artifact_marker_prefix}{task_id_segment}"

    @classmethod
    def build_find_command(
        cls,
        roots: list[str],
        *,
        max_depth: int | None = None,
        marker_paths_by_root: dict[str, str] | None = None,
    ) -> str:
        find_segments = []
        for root in roots:
            command = f"find {shlex.quote(root)}"
            if max_depth is not None:
                command += f" -maxdepth {max_depth}"
            command += " -type f"
            marker_path = (marker_paths_by_root or {}).get(root)
            if marker_path:
                command += f" -newer {shlex.quote(marker_path)}"
            command += f" ! -name '{cls.artifact_marker_prefix}*'"
            find_segments.append(f"if [ -d {shlex.quote(root)} ]; then {command}; fi")
        return " ; ".join(find_segments) + " | sort -u"

    @classmethod
    def resolve_sandbox_template_alias(cls, sandbox_profile: str, explicit_template_alias: str = "") -> str:
        explicit_template_alias = str(explicit_template_alias or "").strip()
        if explicit_template_alias:
            return explicit_template_alias
        profile = str(sandbox_profile or "").strip().lower()
        if profile in {"", cls.default_sandbox_profile}:
            return cls.default_sandbox_template_alias
        if profile == "balanced":
            return "llmops-code-interpreter-balanced"
        return ""

    @classmethod
    def resolve_sandbox_fallback_template_alias(
        cls,
        explicit_fallback_template_alias: str = "",
        *,
        sandbox_template_alias: str = "",
    ) -> str:
        explicit_fallback_template_alias = str(explicit_fallback_template_alias or "").strip()
        if explicit_fallback_template_alias:
            return explicit_fallback_template_alias
        if str(sandbox_template_alias or "").strip():
            return cls.default_sandbox_fallback_template_alias
        return ""

    @classmethod
    def sanitize_sandbox_artifact_text(cls, content: str) -> str:
        """去除用户可见文本中的沙箱本地路径与伪下载链接。"""
        if not content:
            return ""

        sanitized = str(content)

        def _strip_markdown_link(match: re.Match[str]) -> str:
            return match.group(1).strip()

        sanitized = _SANDBOX_DOWNLOAD_LINK_PATTERN.sub(_strip_markdown_link, sanitized)

        def _replace_local_path(match: re.Match[str]) -> str:
            raw_path = match.group(0)
            if raw_path.startswith("sandbox:"):
                raw_path = raw_path[len("sandbox:"):]
            raw_path = raw_path.rstrip(").,，。；;")
            basename = os.path.basename(raw_path.rstrip("/"))
            return basename or "[sandbox-artifact-path]"

        sanitized = _SANDBOX_LOCAL_PATH_PATTERN.sub(_replace_local_path, sanitized)
        return sanitized
