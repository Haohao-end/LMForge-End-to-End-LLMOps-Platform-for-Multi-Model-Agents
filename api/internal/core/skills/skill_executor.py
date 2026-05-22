from __future__ import annotations

import json
import logging
import os
import shlex
import textwrap
import tempfile
import importlib.util
import contextlib
import io
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from internal.core.agent.backends.baidu_cfc_sandbox_backend import BaiduCfcSandboxBackend
from internal.exception import FailException

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_timeout(value: Any, default: int = 60) -> int:
    try:
        timeout = int(value)
    except Exception:
        return default
    return timeout if timeout > 0 else default


def _normalize_payload_text(value: Any) -> str:
    return str(value or "").strip()


def _coerce_json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


@dataclass(slots=True)
class SkillScfClient:
    """技能包的 SCF 同步与执行客户端。"""

    endpoint: str = ""
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not _normalize_text(self.endpoint):
            self.endpoint = _normalize_text(os.getenv("SKILL_SCF_URL") or os.getenv("SANDBOX_URL"))
        self.timeout_seconds = _normalize_timeout(
            self.timeout_seconds or os.getenv("SKILL_SCF_TIMEOUT_SECONDS"),
            default=60,
        )

    @property
    def is_configured(self) -> bool:
        return bool(_normalize_text(self.endpoint))

    def sync_package(self, payload: dict[str, Any]) -> dict[str, Any]:
        """同步/更新技能包到 SCF。"""
        if not self.is_configured:
            logger.warning("SKILL_SCF_URL 未配置，跳过技能包同步: %s", payload.get("source_key", ""))
            return {
                "skipped": True,
                "reason": "SKILL_SCF_URL 未配置",
            }
        return self._post(self._build_sync_request_payload(payload))

    def execute_skill(self, payload: dict[str, Any]) -> Any:
        """调用 SCF 执行技能包工具。"""
        if not self.is_configured:
            raise FailException("SKILL_SCF_URL环境变量未配置")
        return self._post(self._build_execute_request_payload(payload))

    def _build_sync_request_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        skill_payload = payload.get("skill")
        if not isinstance(skill_payload, dict) or not skill_payload:
            skill_payload = payload

        source_key = _normalize_payload_text(skill_payload.get("source_key") or payload.get("source_key"))
        version = skill_payload.get("version") or payload.get("version")
        if isinstance(version, dict):
            version = version.get("version") or version.get("id")
        sync_payload = {
            "source_key": source_key,
            "version": version,
        }
        sync_code = textwrap.dedent(
            f"""
            def sync_package(payload):
                return {{
                    "synced": True,
                    "source_key": {source_key!r},
                    "version": {version!r},
                }}
            """
        ).strip()

        request_payload = dict(payload)
        request_payload["action"] = "sync_package"
        request_payload["code"] = sync_code
        request_payload["func_name"] = "sync_package"
        request_payload["args"] = [sync_payload]
        request_payload["kwargs"] = {}
        return request_payload

    def _build_execute_request_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload = dict(payload)
        request_payload["action"] = "execute_skill"

        code = self._extract_skill_code(request_payload)
        if not code:
            raise FailException("技能云函数执行失败：缺少 skill.py 代码")

        func_name = _normalize_payload_text(
            request_payload.get("func_name") or request_payload.get("entrypoint") or request_payload.get("tool_name")
        )
        if not func_name:
            raise FailException("技能云函数执行失败：缺少入口函数")

        args = request_payload.get("args")
        if not isinstance(args, list):
            args = [request_payload.get("input") or {}]

        kwargs = request_payload.get("kwargs")
        if not isinstance(kwargs, dict):
            kwargs = {}

        request_payload["code"] = code
        request_payload["func_name"] = func_name
        request_payload["args"] = args
        request_payload["kwargs"] = kwargs
        return request_payload

    def _extract_skill_code(self, payload: dict[str, Any]) -> str:
        code = _normalize_payload_text(payload.get("code"))
        if code:
            return code

        bundle = payload.get("bundle")
        if isinstance(bundle, dict):
            code = _normalize_payload_text(bundle.get("skill.py"))
            if code:
                return code

        return ""

    def _post(self, payload: dict[str, Any]) -> Any:
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout_seconds,
            )
            if response.status_code != 200:
                try:
                    response_json = response.json()
                except Exception:
                    response_json = {"raw_text": response.text}
                raise FailException(f"云函数执行失败，状态码: {response.status_code}，响应: {response_json}")

            try:
                response_data = response.json()
            except Exception as exc:
                raise FailException(f"云函数返回非JSON内容: {str(exc)}，原文: {response.text}")

            if isinstance(response_data, dict) and "body" in response_data:
                response_body = response_data.get("body")
                if isinstance(response_body, str):
                    try:
                        parsed_body = json.loads(response_body)
                    except Exception:
                        parsed_body = None
                    if isinstance(parsed_body, dict):
                        response_data = parsed_body
                elif isinstance(response_body, dict):
                    response_data = response_body

            if isinstance(response_data, dict) and "error" in response_data:
                error_message = str(response_data.get("error", ""))
                traceback = str(response_data.get("traceback", "")).strip()
                if traceback:
                    raise FailException(f"云函数执行出错: {error_message}\n{traceback}")
                raise FailException(f"云函数执行出错: {error_message}")

            if isinstance(response_data, dict) and "result" in response_data:
                skill_payload = payload.get("skill") if isinstance(payload.get("skill"), dict) else {}
                logger.info(
                    "技能工具 SCF success: execution_id=%s action=%s func_name=%s source_key=%s",
                    payload.get("execution_id"),
                    payload.get("action"),
                    payload.get("func_name") or payload.get("entrypoint") or payload.get("tool_name"),
                    payload.get("source_key") or payload.get("skill_id") or skill_payload.get("source_key"),
                )
                return response_data["result"]

            return response_data
        except FailException:
            raise
        except requests.exceptions.Timeout:
            raise FailException("云函数执行超时")
        except requests.exceptions.RequestException as exc:
            raise FailException(f"网络请求失败: {str(exc)}")
        except Exception as exc:
            raise FailException(f"技能云函数调用失败: {str(exc)}")


@dataclass(slots=True)
class SkillSandboxExecutor:
    """技能包的本地沙箱执行器。

    当 SCF 执行失败时，使用沙箱在隔离环境中直接加载 `skill.py` 并执行入口函数。
    """

    timeout_seconds: int = 60
    sandbox_timeout: int = 300

    @property
    def is_configured(self) -> bool:
        return bool(_normalize_payload_text(os.getenv("E2B_API_KEY")) and _normalize_payload_text(os.getenv("E2B_DOMAIN")))

    def execute_skill(self, payload: dict[str, Any]) -> Any:
        if not self.is_configured:
            return self._execute_skill_locally(payload)

        bundle = payload.get("bundle")
        if not isinstance(bundle, dict) or not bundle:
            raise FailException("技能沙箱执行失败：缺少 bundle 内容")

        entrypoint = _normalize_payload_text(payload.get("entrypoint") or payload.get("tool_name"))
        if not entrypoint:
            raise FailException("技能沙箱执行失败：缺少入口函数")

        source_key = _normalize_payload_text(payload.get("source_key") or "skill")
        workspace_dir = f"/tmp/skill_runtime/{source_key}"

        files_to_upload: list[tuple[str, bytes]] = []
        for relative_path, content in bundle.items():
            normalized_path = str(relative_path or "").strip().lstrip("/")
            if not normalized_path:
                continue
            files_to_upload.append((f"{workspace_dir}/{normalized_path}", str(content).encode("utf-8")))

        runner_script = self._build_runner_script()
        input_payload = {
            "tool_name": payload.get("tool_name"),
            "entrypoint": entrypoint,
            "input": payload.get("input") or {},
        }
        files_to_upload.append((f"{workspace_dir}/_skill_runner.py", runner_script.encode("utf-8")))
        files_to_upload.append((f"{workspace_dir}/_skill_input.json", _coerce_json_text(input_payload).encode("utf-8")))

        try:
            with BaiduCfcSandboxBackend(timeout=self.timeout_seconds, sandbox_timeout=self.sandbox_timeout) as backend:
                quoted_workspace_dir = shlex.quote(workspace_dir)
                backend.execute(f"mkdir -p {quoted_workspace_dir}")
                upload_results = backend.upload_files(files_to_upload)
                failed_uploads = [item for item in upload_results if getattr(item, "error", None)]
                if failed_uploads:
                    raise FailException(
                        "技能沙箱执行失败：文件上传失败 "
                        + ", ".join(f"{item.path}: {item.error}" for item in failed_uploads)
                    )

                execution = backend.execute(
                    f"cd {quoted_workspace_dir} && python3 _skill_runner.py || python _skill_runner.py",
                    timeout=self.timeout_seconds,
                )
                result = self._parse_runner_output(execution.output)
                if not result.get("ok", False):
                    error_message = _normalize_payload_text(result.get("error")) or "沙箱执行失败"
                    traceback_text = _normalize_payload_text(result.get("traceback"))
                    if traceback_text:
                        raise FailException(f"{error_message}\n{traceback_text}")
                    raise FailException(error_message)

                if result.get("stderr"):
                    logger.info("技能沙箱 stderr: %s", result.get("stderr"))
                logger.info(
                    "技能工具 sandbox remote success: execution_id=%s entrypoint=%s source_key=%s sandbox_id=%s",
                    payload.get("execution_id"),
                    entrypoint,
                    source_key,
                    backend.id,
                )
                return result.get("result")
        except FailException:
            raise
        except Exception:
            return self._execute_skill_locally(payload)

    def _execute_skill_locally(self, payload: dict[str, Any]) -> Any:
        bundle = payload.get("bundle")
        if not isinstance(bundle, dict) or not bundle:
            raise FailException("技能本地执行失败：缺少 bundle 内容")

        entrypoint = _normalize_payload_text(payload.get("entrypoint") or payload.get("tool_name"))
        if not entrypoint:
            raise FailException("技能本地执行失败：缺少入口函数")
        source_key = _normalize_payload_text(payload.get("source_key") or "skill")

        with tempfile.TemporaryDirectory(prefix="skill_local_") as tmp_dir:
            base_dir = Path(tmp_dir)
            for relative_path, content in bundle.items():
                normalized_path = str(relative_path or "").strip().lstrip("/")
                if not normalized_path:
                    continue
                file_path = base_dir / normalized_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(str(content), encoding="utf-8")

            module_path = base_dir / "skill.py"
            if not module_path.exists():
                raise FailException("技能本地执行失败：bundle 中缺少 skill.py")

            spec = importlib.util.spec_from_file_location("skill_module", module_path)
            if spec is None or spec.loader is None:
                raise FailException("技能本地执行失败：无法加载 skill.py")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            func = getattr(module, entrypoint, None)
            if not callable(func):
                raise FailException(f"技能本地执行失败：函数 {entrypoint!r} 不存在或不可调用")

            call_input = payload.get("input") or {}
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                    result = func(call_input)
            except Exception as exc:
                raise FailException(f"技能本地执行失败: {exc}") from exc

            if stderr_buffer.getvalue():
                logger.info("技能本地执行 stderr: %s", stderr_buffer.getvalue())
            logger.info(
                "技能工具 sandbox local success: execution_id=%s entrypoint=%s source_key=%s",
                payload.get("execution_id"),
                entrypoint,
                source_key,
            )
            return result

    def _build_runner_script(self) -> str:
        return textwrap.dedent(
            """
            from __future__ import annotations

            import contextlib
            import importlib.util
            import io
            import json
            import pathlib
            import traceback

            MARKER = "__SKILL_RESULT__"

            def main() -> None:
                base_dir = pathlib.Path(__file__).resolve().parent
                with (base_dir / "_skill_input.json").open("r", encoding="utf-8") as f:
                    payload = json.load(f)

                module_path = base_dir / "skill.py"
                if not module_path.exists():
                    raise FileNotFoundError(f"skill.py not found: {module_path}")

                spec = importlib.util.spec_from_file_location("skill_module", module_path)
                if spec is None or spec.loader is None:
                    raise RuntimeError("无法加载 skill.py 模块")

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                entrypoint = str(payload.get("entrypoint") or "").strip()
                func = getattr(module, entrypoint, None)
                if not callable(func):
                    raise RuntimeError(f"Function {entrypoint!r} not found or not callable")

                call_input = payload.get("input") or {}
                stdout_buffer = io.StringIO()
                stderr_buffer = io.StringIO()
                with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                    result = func(call_input)

                print(
                    MARKER
                    + json.dumps(
                        {
                            "ok": True,
                            "result": result,
                            "stdout": stdout_buffer.getvalue(),
                            "stderr": stderr_buffer.getvalue(),
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                )

            if __name__ == "__main__":
                try:
                    main()
                except Exception as exc:
                    print(
                        MARKER
                        + json.dumps(
                            {
                                "ok": False,
                                "error": str(exc),
                                "traceback": traceback.format_exc(),
                            },
                            ensure_ascii=False,
                            default=str,
                        )
                    )
            """
        ).strip()

    def _parse_runner_output(self, output: str | None) -> dict[str, Any]:
        text = _normalize_payload_text(output)
        if not text:
            raise FailException("技能沙箱执行失败：没有返回结果")

        marker = "__SKILL_RESULT__"
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if not stripped.startswith(marker):
                continue
            try:
                parsed = json.loads(stripped[len(marker) :])
            except Exception as exc:
                raise FailException(f"技能沙箱执行失败：结果解析失败 {exc}") from exc
            if isinstance(parsed, dict):
                return parsed
            raise FailException("技能沙箱执行失败：结果格式非法")

        raise FailException(f"技能沙箱执行失败：未找到结果标记，原始输出: {text}")
