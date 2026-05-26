"""DeepThinkingAgent — 深度思考智能体。"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
import json
import logging
import mimetypes
import os
import re
import shlex
import sys
import time
import uuid
from types import ModuleType
from urllib.parse import urlparse
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from flask import has_app_context

from internal.core.agent.agents.function_call_agent import FunctionCallAgent
from internal.core.agent.entities.agent_entity import (
    DEEP_THINKING_SYSTEM_PROMPT,
    AgentState,
)
from internal.core.agent.entities.queue_entity import AgentThought, QueueEvent
from internal.core.agent.middleware import DeepTimelineMiddleware
from internal.core.agent.usage_utils import track_language_model_usage

logger = logging.getLogger(__name__)

_DEFAULT_SANDBOX_PROFILE = "lite"
_DEFAULT_SANDBOX_TEMPLATE_ALIAS = "llmops-code-interpreter-lite"
_DEFAULT_SANDBOX_FALLBACK_TEMPLATE_ALIAS = "code-interpreter-v1"
_DEFAULT_SANDBOX_TIMEOUT_SECONDS = 300
_DEFAULT_EXECUTE_TIMEOUT_SECONDS = 60
_DEFAULT_ARTIFACT_BASE_DIRS = ("/workspace", "/home/user", "/tmp")
_ARTIFACT_MARKER_PREFIX = ".openagent_artifact_marker_"
_SANDBOX_LOCAL_PATH_PATTERNS = (
    r"/workspace/artifacts/[^\s)>]+",
    r"/home/user/artifacts/[^\s)>]+",
    r"/tmp/artifacts/[^\s)>]+",
    r"sandbox:/mnt/data/[^\s)>]+",
)
_DEEPAGENTS_EXCLUDED_TOOLS = frozenset({
    "ls",
    "read_file",
    "write_file",
    "edit_file",
    "glob",
    "grep",
})
_REGISTERED_DEEPAGENTS_PROFILE_KEYS: set[str] = set()
_PROVIDER_PROFILE_ALIASES: dict[str, tuple[str, ...]] = {
    "google": ("google_genai",),
    "google_genai": ("google",),
    "wenxin": ("qianfan",),
    "qianfan": ("wenxin",),
    "zhipu": ("zhipuai",),
    "zhipuai": ("zhipu",),
    "grok": ("xai",),
    "xai": ("grok",),
}


try:  # pragma: no cover - 仅在本地未安装 deepagents 时启用兜底桩
    import deepagents as _deepagents_module  # noqa: F401
except ImportError:  # pragma: no cover - 仅用于单测与本地导入兜底
    deepagents_stub = ModuleType("deepagents")
    deepagents_backends_stub = ModuleType("deepagents.backends")

    @dataclass(slots=True)
    class GeneralPurposeSubagentProfile:
        enabled: bool = True
        name: str = "general-purpose"
        description: str = ""
        system_prompt: str = ""

    @dataclass(slots=True)
    class HarnessProfile:
        excluded_tools: frozenset[str] = frozenset()
        excluded_middleware: frozenset[Any] = frozenset()
        extra_middleware: tuple[Any, ...] = ()
        general_purpose_subagent: Any = field(default_factory=GeneralPurposeSubagentProfile)
        base_system_prompt: str = ""
        system_prompt_suffix: str = ""
        tool_description_overrides: dict[str, str] = field(default_factory=dict)

    @dataclass(slots=True)
    class StateBackend:
        """deepagents 未安装时的占位后端。"""

    def create_deep_agent(*_args: Any, **_kwargs: Any) -> Any:
        raise ImportError("deepagents 未安装")

    def register_harness_profile(*_args: Any, **_kwargs: Any) -> None:
        return None

    deepagents_stub.create_deep_agent = create_deep_agent
    deepagents_stub.HarnessProfile = HarnessProfile
    deepagents_stub.GeneralPurposeSubagentProfile = GeneralPurposeSubagentProfile
    deepagents_stub.register_harness_profile = register_harness_profile
    deepagents_backends_stub.StateBackend = StateBackend
    deepagents_stub.backends = deepagents_backends_stub
    sys.modules.setdefault("deepagents", deepagents_stub)
    sys.modules.setdefault("deepagents.backends", deepagents_backends_stub)


def _read_positive_int_env(env_name: str, default: int) -> int:
    raw_value = (os.getenv(env_name) or "").strip()
    if not raw_value:
        return default

    try:
        parsed_value = int(raw_value)
    except ValueError:
        logger.warning("%s=%r 无法解析为整数，使用默认值 %s", env_name, raw_value, default)
        return default

    if parsed_value <= 0:
        logger.warning("%s=%r 必须大于 0，使用默认值 %s", env_name, raw_value, default)
        return default

    return parsed_value


def _normalize_profile_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _deduplicate_profile_keys(keys: list[str]) -> list[str]:
    deduplicated: list[str] = []
    for key in keys:
        normalized_key = _normalize_profile_key(key)
        if not normalized_key or normalized_key in deduplicated:
            continue
        deduplicated.append(normalized_key)
    return deduplicated


def _infer_deepagents_profile_keys(model: Any) -> list[str]:
    """根据当前模型实例尽量推断 deepagents profile key。"""
    provider_candidates: list[str] = []
    module_name = str(getattr(model.__class__, "__module__", "") or "").strip()
    if ".providers." in module_name:
        provider_candidates.append(module_name.split(".providers.", 1)[1].split(".", 1)[0])

    llm_type = _normalize_profile_key(getattr(model, "_llm_type", ""))
    if llm_type:
        provider_candidates.append(llm_type)

    provider_attr = _normalize_profile_key(getattr(model, "provider", ""))
    if provider_attr:
        provider_candidates.append(provider_attr)

    expanded_candidates: list[str] = []
    for provider in list(provider_candidates):
        expanded_candidates.append(provider)
        expanded_candidates.extend(_PROVIDER_PROFILE_ALIASES.get(provider, ()))

    model_name = _normalize_profile_key(
        getattr(model, "model_name", "")
        or getattr(model, "model", "")
        or getattr(model, "model_id", "")
    )

    profile_keys: list[str] = []
    for provider in expanded_candidates:
        if provider:
            profile_keys.append(provider)
            if model_name:
                profile_keys.append(f"{provider}:{model_name}")

    return _deduplicate_profile_keys(profile_keys)


def _register_deepagents_harness_profile(model: Any) -> None:
    """注册 deepagents harness profile，隐藏文件工具并关闭默认 general-purpose subagent。"""
    profile_keys = _infer_deepagents_profile_keys(model)
    if not profile_keys:
        return

    from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile  # noqa: PLC0415

    profile = HarnessProfile(
        excluded_tools=_DEEPAGENTS_EXCLUDED_TOOLS,
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    )

    for profile_key in profile_keys:
        if profile_key in _REGISTERED_DEEPAGENTS_PROFILE_KEYS:
            continue
        try:
            register_harness_profile(profile_key, profile)
            _REGISTERED_DEEPAGENTS_PROFILE_KEYS.add(profile_key)
            logger.debug("已注册 deepagents harness profile: %s", profile_key)
        except Exception as exc:  # pragma: no cover - 仅在 deepagents profile API 异常时触发
            logger.warning("注册 deepagents harness profile 失败: key=%s, error=%s", profile_key, exc)


class DeepRouteDecision(BaseModel):
    """深度思考阶段的运行时能力判断结果。"""

    need_sandbox: bool = False
    need_file_io: bool = False
    need_execute: bool = False
    need_subagent: bool = False
    need_artifact_output: bool = False
    reason: str = ""
    summary: str = ""


class DeepThinkingAgent(FunctionCallAgent):
    """深度思考智能体：先判断能力，再按需使用沙箱和 deepagents。"""

    name: str = "deep_thinking_agent"

    def _build_agent(self) -> CompiledStateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("preset_operation", self._preset_operation_node)
        graph.add_node("long_term_memory_recall", self._long_term_memory_recall_node)
        graph.add_node("deep_agent", self._deep_agent_node)
        graph.add_node("llm", self._llm_node)
        graph.add_node("tools", self._tools_node)

        graph.set_entry_point("preset_operation")
        graph.add_conditional_edges("preset_operation", self._preset_operation_condition)
        graph.add_edge("long_term_memory_recall", "deep_agent")
        graph.add_edge("deep_agent", "llm")
        graph.add_conditional_edges("llm", self._tools_condition)
        graph.add_edge("tools", "llm")
        return graph.compile()

    def _deep_agent_node(self, state: AgentState) -> AgentState:
        task_id = state["task_id"]
        start_at = time.perf_counter()
        timeline = DeepTimelineMiddleware(task_id=task_id, publisher=self.agent_queue_manager.publish)
        query = self._extract_query(state["messages"][-1])
        long_term_memory = str(state.get("long_term_memory", "") or "")

        route_step_id = uuid.uuid4()
        timeline.publish_step(
            step_id=route_step_id,
            step_type="plan",
            status="start",
            title="分析执行策略",
            detail="正在判断是否需要沙箱、文件输出和子任务拆解",
        )

        with track_language_model_usage(self.llm) as usage_tracker:
            route_decision = self._decide_deep_route(query)
            timeline.publish_step(
                step_id=route_step_id,
                step_type="plan",
                status="success",
                title="分析执行策略",
                detail=route_decision.summary or route_decision.reason or "已完成执行策略分析",
                technical_detail=route_decision.model_dump_json(),
                tool_input={"route": route_decision.model_dump()},
            )

            backend = None
            try:
                deep_agent, backend, artifact_root, used_sandbox = self._build_deep_agent(
                    task_id=task_id,
                    route_decision=route_decision,
                    timeline=timeline,
                    long_term_memory=long_term_memory,
                )
            except Exception as e:
                logger.warning("deepagents 子 Agent 构建失败，降级为普通模式: %s", e)
                timeline.publish_step(
                    step_id=uuid.uuid4(),
                    step_type="reflection",
                    status="error",
                    title="初始化深度执行失败",
                    detail="深度执行初始化失败，已回退到普通流程",
                    technical_detail=f"{type(e).__name__}: {e}",
                )
                return {"messages": []}

            deep_answer = ""
            artifacts: list[dict[str, Any]] = []
            execution_error = ""
            try:
                result = deep_agent.invoke({
                    "messages": [HumanMessage(content=query)],
                })
                messages = result.get("messages", [])
                if messages:
                    last = messages[-1]
                    deep_answer = getattr(last, "content", "") or ""
                    if isinstance(deep_answer, list):
                        deep_answer = " ".join(
                            block.get("text", "")
                            for block in deep_answer
                            if isinstance(block, dict) and block.get("type") == "text"
                        )

                if used_sandbox:
                    artifacts = self._collect_artifacts(
                        backend=backend,
                        artifact_root=artifact_root,
                        timeline=timeline,
                    )
            except Exception as e:
                logger.error("deepagents 执行失败: %s", e)
                timeline.publish_step(
                    step_id=uuid.uuid4(),
                    step_type="reflection",
                    status="error",
                    title="深度执行失败",
                    detail="深度执行过程中出现错误",
                    technical_detail=f"{type(e).__name__}: {e}",
                )
                deep_answer = f"深度思考执行时遇到错误: {e}"
                execution_error = f"{type(e).__name__}: {e}"
            finally:
                close_method = getattr(backend, "close", None)
                if callable(close_method):
                    try:
                        close_method()
                    except Exception:
                        logger.debug("关闭深度执行 backend 时发生异常", exc_info=True)

        latency = time.perf_counter() - start_at
        deep_answer = self._sanitize_deep_answer(deep_answer, artifacts=artifacts)
        self_check = self._build_final_self_check(
            route_decision=route_decision,
            used_sandbox=used_sandbox,
            deep_answer=deep_answer,
            artifacts=artifacts,
            execution_error=execution_error,
        )
        timeline.publish_step(
            step_id=uuid.uuid4(),
            step_type="reflection",
            status=self_check["status"],
            title="最终一致性检查",
            detail=self_check["detail"],
            technical_detail=self_check["technical_detail"],
            tool="self_check",
        )
        completion_summary = self._build_completion_summary(
            route_decision=route_decision,
            used_sandbox=used_sandbox,
            deep_answer=deep_answer,
            artifacts=artifacts,
            self_check_summary=self_check["summary"],
        )
        timeline.publish_complete(
            completion_summary,
            latency=latency,
            artifact_count=len(artifacts),
            total_token_count=usage_tracker.total_token_count,
            total_price=usage_tracker.total_price,
        )

        thinking_context = self._build_thinking_context(
            route_decision=route_decision,
            used_sandbox=used_sandbox,
            deep_answer=deep_answer,
            artifacts=artifacts,
            self_check=self_check,
        )
        return {"messages": [AIMessage(content=thinking_context)]}

    @staticmethod
    def _extract_query(message: Any) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return str(block.get("text", ""))
        return str(content)

    def _decide_deep_route(self, query: str) -> DeepRouteDecision:
        routing_prompt = (
            "你是一个深度执行路由器。请判断这次任务是否需要沙箱执行、文件读写、"
            "代码执行、子任务拆解、产物输出。"
            "请基于语义判断，不要只看关键词是否完全命中。"
            "如果用户只是要方案、计划、攻略、总结等文本结果，而没有明确表达保存、导出、下载、附件、另存为、生成文档、导出成 markdown 等意图，就不要把 need_artifact_output 设为 true。"
            "如果用户确实希望把结果保存为文件、导出、下载、附带附件，或需要可下载的 Markdown/文档，请把 need_artifact_output 设为 true；"
            "对于方案类任务，若需要附件，优先生成 Markdown，而不是 PDF。"
            "如果需要生成 txt/csv/json/md/html/docx/xlsx/代码文件，need_artifact_output 必须为 true。"
            "如果需要执行 Python/Shell、读写真实文件或生成可下载附件，need_sandbox 必须为 true。"
        )
        try:
            structured_llm = self.llm.with_structured_output(DeepRouteDecision)
            decision = structured_llm.invoke([
                HumanMessage(
                    content=(
                        f"{routing_prompt}\n\n"
                        f"预设提示：{self.agent_config.preset_prompt}\n\n"
                        f"用户任务：{query}"
                    )
                )
            ])
            if isinstance(decision, DeepRouteDecision):
                normalized = decision
            elif isinstance(decision, dict):
                normalized = DeepRouteDecision(**decision)
            else:
                normalized = DeepRouteDecision()
        except Exception:
            logger.debug("结构化路由判断失败，回退到启发式策略", exc_info=True)
            normalized = self._heuristic_deep_route(query)

        if normalized.need_execute or normalized.need_file_io or normalized.need_artifact_output:
            normalized.need_sandbox = True
        if not normalized.summary:
            normalized.summary = (
                "需要沙箱执行"
                if normalized.need_sandbox
                else "无需沙箱，使用普通深度思考"
            )
        return normalized

    @staticmethod
    def _heuristic_deep_route(query: str) -> DeepRouteDecision:
        normalized_query = query.lower()
        artifact_keywords = [
            "txt", "csv", "json", "markdown", "md", "html", "word", "docx",
            "excel", "xlsx", "pdf", "文件", "附件", "导出", "导出成 markdown", "导出成md",
            "导出为 markdown", "导出为md", "输出成 markdown", "输出成md", "生成文档",
            "生成 markdown", "生成md", "保存", "保存为", "另存为", "下载", "表格",
        ]
        execute_keywords = [
            "python", "shell", "bash", "脚本", "代码", "运行", "执行", "测试",
            "benchmark", "命令", "程序",
        ]
        file_keywords = [
            "read file", "write file", "edit file", "grep", "glob", "保存", "读取文件",
            "写入文件", "编辑文件", "搜索文件", "目录",
        ]
        subagent_keywords = ["拆分任务", "分步骤", "多任务", "多个子任务", "并行"]

        need_artifact_output = any(keyword in normalized_query for keyword in artifact_keywords)
        need_execute = any(keyword in normalized_query for keyword in execute_keywords)
        need_file_io = need_artifact_output or any(keyword in normalized_query for keyword in file_keywords)
        need_subagent = any(keyword in normalized_query for keyword in subagent_keywords)
        need_sandbox = need_execute or need_file_io or need_artifact_output
        summary = "需要沙箱执行" if need_sandbox else "无需沙箱，使用普通深度思考"
        reason = "启发式判断：涉及代码执行、文件输出或真实文件操作" if need_sandbox else "启发式判断：任务偏文本规划与分析"
        return DeepRouteDecision(
            need_sandbox=need_sandbox,
            need_file_io=need_file_io,
            need_execute=need_execute,
            need_subagent=need_subagent,
            need_artifact_output=need_artifact_output,
            reason=reason,
            summary=summary,
        )

    @classmethod
    def _build_default_artifact_root(cls, task_id: Any) -> str:
        return f"/workspace/artifacts/{task_id}"

    @classmethod
    def _build_candidate_artifact_roots(cls, primary_root: str) -> list[str]:
        normalized_primary = (primary_root or "").rstrip("/")
        task_id_segment = os.path.basename(normalized_primary)
        roots = [normalized_primary] if normalized_primary else []
        if task_id_segment:
            roots.extend(f"{base}/artifacts/{task_id_segment}" for base in _DEFAULT_ARTIFACT_BASE_DIRS)

        unique_roots: list[str] = []
        for root in roots:
            if root and root not in unique_roots:
                unique_roots.append(root)
        return unique_roots

    @classmethod
    def _build_fallback_artifact_roots(cls, primary_root: str) -> list[str]:
        normalized_primary = (primary_root or "").rstrip("/")
        roots = []
        if normalized_primary:
            parent_root = os.path.dirname(normalized_primary.rstrip("/"))
            if parent_root and parent_root != "/":
                roots.append(parent_root)
        roots.extend(f"{base}/artifacts" for base in _DEFAULT_ARTIFACT_BASE_DIRS)

        unique_roots: list[str] = []
        for root in roots:
            if root and root not in unique_roots:
                unique_roots.append(root)
        return unique_roots

    @classmethod
    def _build_artifact_marker_name(cls, primary_root: str) -> str:
        task_id_segment = os.path.basename((primary_root or "").rstrip("/"))
        if not task_id_segment:
            return f"{_ARTIFACT_MARKER_PREFIX}artifacts"
        return f"{_ARTIFACT_MARKER_PREFIX}{task_id_segment}"

    def _prepare_artifact_markers(self, *, backend: Any, artifact_root: str) -> list[str]:
        execute_method = getattr(backend, "execute", None)
        if not callable(execute_method):
            return []

        marker_name = self._build_artifact_marker_name(artifact_root)
        fallback_roots = self._build_fallback_artifact_roots(artifact_root)
        if not fallback_roots:
            return []

        command_segments = []
        for root in fallback_roots:
            marker_path = f"{root}/{marker_name}"
            command_segments.append(
                f"if mkdir -p {shlex.quote(root)} 2>/dev/null; then "
                f": > {shlex.quote(marker_path)} && printf '%s\\n' {shlex.quote(marker_path)}; "
                "fi"
            )

        result = execute_method(" ; ".join(command_segments), timeout=15)
        if getattr(result, "exit_code", 1) != 0:
            logger.warning("准备沙箱产物标记失败，继续使用常规扫描: %s", getattr(result, "output", ""))
            return []

        return self._extract_artifact_paths(getattr(result, "output", ""))

    @staticmethod
    def _extract_artifact_paths(output: Any) -> list[str]:
        return [
            line.strip()
            for line in str(output or "").splitlines()
            if line.strip() and not line.startswith("[stderr]") and line.startswith("/")
        ]

    @staticmethod
    def _build_find_command(
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
            command += f" ! -name '{_ARTIFACT_MARKER_PREFIX}*'"
            find_segments.append(f"if [ -d {shlex.quote(root)} ]; then {command}; fi")
        return " ; ".join(find_segments) + " | sort -u"

    def _resolve_sandbox_artifact_root(
        self,
        *,
        backend: Any,
        task_id: Any,
    ) -> str:
        default_root = self._build_default_artifact_root(task_id)
        execute_method = getattr(backend, "execute", None)
        if not callable(execute_method):
            return default_root

        task_id_text = str(task_id)
        probe_command = (
            "for base in /workspace \"$HOME\" /home/user /tmp; do "
            f"if [ -n \"$base\" ] && mkdir -p \"$base/artifacts/{task_id_text}\" 2>/dev/null; then "
            f"printf '%s/artifacts/{task_id_text}' \"$base\"; "
            "exit 0; "
            "fi; "
            "done; "
            "exit 1"
        )
        result = execute_method(probe_command, timeout=15)
        if getattr(result, "exit_code", 1) != 0:
            logger.warning("探测沙箱产物目录失败，回退默认目录: %s", getattr(result, "output", ""))
            return default_root

        detected_root = str(getattr(result, "output", "")).strip()
        return detected_root if detected_root.startswith("/") else default_root

    def _build_deep_agent(
        self,
        *,
        task_id,
        route_decision: DeepRouteDecision,
        timeline: DeepTimelineMiddleware,
        long_term_memory: str = "",
    ):
        from deepagents import create_deep_agent  # noqa: PLC0415
        from deepagents.backends import StateBackend  # noqa: PLC0415

        e2b_key = os.environ.get("E2B_API_KEY", "")
        e2b_domain = os.environ.get("E2B_DOMAIN", "")
        sandbox_enabled = bool(route_decision.need_sandbox and e2b_key and e2b_domain)
        sandbox_profile = (os.getenv("SANDBOX_PROFILE") or "").strip().lower()
        sandbox_template_alias = (os.getenv("SANDBOX_TEMPLATE_ALIAS") or "").strip()
        sandbox_fallback_template_alias = (os.getenv("SANDBOX_FALLBACK_TEMPLATE_ALIAS") or "").strip()
        sandbox_timeout = _read_positive_int_env("SANDBOX_TIMEOUT_SECONDS", _DEFAULT_SANDBOX_TIMEOUT_SECONDS)
        execute_timeout = _read_positive_int_env("SANDBOX_EXECUTE_TIMEOUT_SECONDS", _DEFAULT_EXECUTE_TIMEOUT_SECONDS)

        if not sandbox_template_alias:
            if sandbox_profile in {"", _DEFAULT_SANDBOX_PROFILE}:
                sandbox_template_alias = _DEFAULT_SANDBOX_TEMPLATE_ALIAS
            elif sandbox_profile == "balanced":
                sandbox_template_alias = "llmops-code-interpreter-balanced"

        if sandbox_template_alias and not sandbox_fallback_template_alias:
            sandbox_fallback_template_alias = _DEFAULT_SANDBOX_FALLBACK_TEMPLATE_ALIAS

        artifact_root = self._build_default_artifact_root(task_id)
        used_sandbox = False
        if sandbox_enabled:
            try:
                from internal.core.agent.backends import BaiduCfcSandboxBackend  # noqa: PLC0415

                backend = BaiduCfcSandboxBackend(
                    api_key=e2b_key,
                    domain=e2b_domain,
                    timeout=execute_timeout,
                    sandbox_timeout=sandbox_timeout,
                    template_alias=sandbox_template_alias or None,
                    fallback_template_alias=sandbox_fallback_template_alias or None,
                )
                if sandbox_template_alias:
                    backend.ensure_ready()
                artifact_root = self._resolve_sandbox_artifact_root(
                    backend=backend,
                    task_id=task_id,
                )
                setattr(
                    backend,
                    "_openagent_artifact_markers",
                    self._prepare_artifact_markers(backend=backend, artifact_root=artifact_root),
                )
                used_sandbox = True
                timeline.publish_step(
                    step_id=uuid.uuid4(),
                    step_type="tool",
                    status="success",
                    title="进入沙箱执行",
                    detail=f"已启用沙箱模板：{sandbox_template_alias or '<default>'}",
                    technical_detail=f"artifact_root={artifact_root}",
                    tool="sandbox",
                )
            except Exception as e:
                logger.warning("沙箱初始化失败，降级为普通深度思考: %s", e)
                timeline.publish_step(
                    step_id=uuid.uuid4(),
                    step_type="tool",
                    status="error",
                    title="沙箱初始化失败",
                    detail="无法创建沙箱，已回退到普通深度思考",
                    technical_detail=f"{type(e).__name__}: {e}",
                    tool="sandbox",
                )
                backend = StateBackend()
                sandbox_enabled = False

        if not sandbox_enabled:
            backend = StateBackend()
            timeline.publish_step(
                step_id=uuid.uuid4(),
                step_type="tool",
                status="success",
                title="使用普通深度思考",
                detail="本次任务未启用沙箱，将使用无执行环境的深度思考模式",
                technical_detail=route_decision.reason,
                tool="state_backend",
            )

        _register_deepagents_harness_profile(self.llm)
        system_prompt = DEEP_THINKING_SYSTEM_PROMPT.format(
            preset_prompt=self.agent_config.preset_prompt,
            long_term_memory=long_term_memory,
        )
        system_prompt += (
            f"\n\n## 本次运行约束\n"
            f"- 是否允许沙箱执行: {'是' if sandbox_enabled else '否'}\n"
            f"- 产物输出目录: {artifact_root}\n"
            f"- 优先复用当前应用已经绑定好的工具与 agent_bindings；只有在确实需要上下文隔离时才考虑任务委派。\n"
            f"- 如需生成最终可下载文件，请只写入该目录，最终交由系统收口为附件链接。\n"
            f"- 生成完文件后，请在最终回答中简要说明文件名称和用途。\n"
            f"- 只有在用户明确要求配图或视觉材料时才调用图像工具，默认不要生成图片。\n"
            f"- 方案类任务默认先输出完整文本结论；如果用户明确要保存、导出、下载、附件、另存为、生成文档或导出成 markdown，再额外生成附件。\n"
            f"- 如果需要附件，优先生成 Markdown，不要默认转成 PDF。\n"
            f"- 附件是可选补充材料，不得阻塞文本结果的输出。\n"
            f"- 禁止把沙箱本地路径（如 /workspace、/home/user、/tmp、sandbox:/mnt/data 下的路径）当成下载链接返回给用户。\n"
            f"- 如果生成了附件，只能说明文件名和用途，真实下载链接由系统注入。\n"
            f"- 在最终回答前，请做一次轻量自检：确认计划是否完成、附件是否真实可下载、最终答案是否没有泄漏沙箱本地路径。"
        )
        if not sandbox_enabled:
            system_prompt += "\n- 当前未提供沙箱执行能力，不要调用 execute 解决任务。"

        deep_agent = create_deep_agent(
            model=self.llm,
            tools=list(self.agent_config.tools),
            system_prompt=system_prompt,
            backend=backend,
            middleware=[timeline],
        )
        return deep_agent, backend, artifact_root, used_sandbox

    def _collect_artifacts(
        self,
        *,
        backend: Any,
        artifact_root: str,
        timeline: DeepTimelineMiddleware,
    ) -> list[dict[str, Any]]:
        execute_method = getattr(backend, "execute", None)
        download_method = getattr(backend, "download_files", None)
        if not callable(execute_method) or not callable(download_method):
            return []

        artifact_paths_step_id = uuid.uuid4()
        timeline.publish_step(
            step_id=artifact_paths_step_id,
            step_type="artifact",
            status="start",
            title="检查生成产物",
            detail=f"扫描目录 {artifact_root}",
            technical_detail="\n".join(self._build_candidate_artifact_roots(artifact_root)),
            tool="artifact_scan",
        )

        scan_roots = self._build_candidate_artifact_roots(artifact_root)
        find_command = self._build_find_command(scan_roots)
        result = execute_method(find_command, timeout=15)
        if getattr(result, "exit_code", 1) != 0:
            timeline.publish_step(
                step_id=artifact_paths_step_id,
                step_type="artifact",
                status="error",
                title="检查生成产物",
                detail="扫描产物目录失败",
                technical_detail=str(getattr(result, "output", "")),
                tool="artifact_scan",
                latency=0,
            )
            return []

        artifact_paths = self._extract_artifact_paths(getattr(result, "output", ""))
        if not artifact_paths:
            fallback_roots = self._build_fallback_artifact_roots(artifact_root)
            marker_paths_by_root = {
                os.path.dirname(path): path
                for path in (getattr(backend, "_openagent_artifact_markers", None) or [])
                if path
            }
            if fallback_roots and marker_paths_by_root:
                fallback_find_command = self._build_find_command(
                    [root for root in fallback_roots if root in marker_paths_by_root],
                    max_depth=1,
                    marker_paths_by_root=marker_paths_by_root,
                )
                fallback_result = execute_method(fallback_find_command, timeout=15)
                if getattr(fallback_result, "exit_code", 1) == 0:
                    artifact_paths = self._extract_artifact_paths(getattr(fallback_result, "output", ""))
        if not artifact_paths:
            timeline.publish_step(
                step_id=artifact_paths_step_id,
                step_type="artifact",
                status="success",
                title="检查生成产物",
                detail="本次未生成可下载产物",
                tool="artifact_scan",
                latency=0,
            )
            return []

        timeline.publish_step(
            step_id=artifact_paths_step_id,
            step_type="artifact",
            status="success",
            title="检查生成产物",
            detail=f"发现 {len(artifact_paths)} 个产物文件",
            technical_detail="\n".join(artifact_paths[:20]),
            tool="artifact_scan",
            latency=0,
        )

        responses = download_method(artifact_paths)
        artifacts: list[dict[str, Any]] = []

        flask_app = self.agent_config.runtime_flask_app
        app_context = nullcontext()
        if flask_app is not None and not has_app_context():
            app_context = flask_app.app_context()

        with app_context:
            from app.http.module import injector  # noqa: PLC0415
            from internal.service import CosService  # noqa: PLC0415

            cos_service = injector.get(CosService)
            for response in responses:
                if getattr(response, "error", None) or getattr(response, "content", None) is None:
                    timeline.publish_step(
                        step_id=uuid.uuid4(),
                        step_type="artifact",
                        status="error",
                        title="持久化产物失败",
                        detail=f"无法下载沙箱产物：{getattr(response, 'path', '')}",
                        technical_detail=str(getattr(response, "error", "")),
                        tool="artifact_download",
                    )
                    continue

                artifact_path = str(response.path)
                artifact_name = os.path.basename(artifact_path)
                mime_type = mimetypes.guess_type(artifact_name)[0] or "application/octet-stream"
                try:
                    upload_file = cos_service.upload_bytes(
                        filename=artifact_name,
                        content=response.content,
                        account_id=self.agent_config.user_id,
                        mime_type=mime_type,
                        folder="artifacts",
                    )
                    artifact = {
                        "id": str(upload_file.id),
                        "name": upload_file.name,
                        "path": artifact_path,
                        "size": upload_file.size,
                        "extension": upload_file.extension,
                        "mime_type": upload_file.mime_type,
                        "url": cos_service.get_file_url(upload_file.key, download_name=upload_file.name),
                    }
                    artifacts.append(artifact)
                    timeline.publish_artifact(artifact_id=uuid.uuid4(), artifact=artifact)
                except Exception as e:
                    timeline.publish_step(
                        step_id=uuid.uuid4(),
                        step_type="artifact",
                        status="error",
                        title="持久化产物失败",
                        detail=f"上传产物失败：{artifact_name}",
                        technical_detail=f"{type(e).__name__}: {e}",
                        tool="artifact_upload",
                    )
        return artifacts

    @staticmethod
    def _build_completion_summary(
        *,
        route_decision: DeepRouteDecision,
        used_sandbox: bool,
        deep_answer: str,
        artifacts: list[dict[str, Any]],
        self_check_summary: str = "",
    ) -> str:
        summary_parts = [route_decision.summary or "深度思考已完成"]
        if used_sandbox:
            summary_parts.append("执行环境：沙箱")
        elif route_decision.need_sandbox:
            summary_parts.append("执行环境：已回退为无沙箱模式")
        if artifacts:
            summary_parts.append("生成附件：" + "、".join(artifact["name"] for artifact in artifacts[:5]))
        if deep_answer:
            summary_parts.append("已生成最终答复")
        if self_check_summary:
            summary_parts.append(self_check_summary)
        return "；".join(summary_parts)

    @staticmethod
    def _build_thinking_context(
        *,
        route_decision: DeepRouteDecision,
        used_sandbox: bool,
        deep_answer: str,
        artifacts: list[dict[str, Any]],
        self_check: dict[str, Any] | None = None,
    ) -> str:
        artifact_summary = ""
        if artifacts:
            artifact_lines = "\n".join(
                f"- {artifact['name']} ({artifact['url']})"
                for artifact in artifacts
            )
            artifact_summary = f"\n\n<generated_artifacts>\n{artifact_lines}\n</generated_artifacts>"

        self_check_summary = ""
        if self_check:
            self_check_summary = (
                "\n\n<deep_self_check>\n"
                f"{json.dumps(self_check, ensure_ascii=False)}\n"
                "</deep_self_check>"
            )

        final_answer_instruction = (
            "以上是深度思考阶段的分析结果。请基于此给用户一个简洁、准确的最终回答。"
            "如果 <generated_artifacts> 存在，只能使用其中的真实下载 URL；"
            "绝不要向用户暴露沙箱本地路径（包括 sandbox:/mnt/data），也不要伪造“点击下载”链接。"
            "如果 <generated_artifacts> 不存在，请直接给出完整文本结果；如果 self_check 提示本次未生成附件，请用一句简短提醒说明附件是可选补充材料，但不要把它描述成失败。"
        )

        return (
            f"<deep_execution_summary>\n"
            f"- route: {route_decision.summary or route_decision.reason}\n"
            f"- need_sandbox: {route_decision.need_sandbox}\n"
            f"- used_sandbox: {used_sandbox}\n"
            f"- need_execute: {route_decision.need_execute}\n"
            f"- need_file_io: {route_decision.need_file_io}\n"
            f"- need_subagent: {route_decision.need_subagent}\n"
            f"</deep_execution_summary>\n\n"
            f"<deep_thinking_result>\n{deep_answer}\n</deep_thinking_result>"
            f"{artifact_summary}\n\n"
            f"{self_check_summary}"
            f"{final_answer_instruction}"
        )

    @classmethod
    def _build_final_self_check(
        cls,
        *,
        route_decision: DeepRouteDecision,
        used_sandbox: bool,
        deep_answer: str,
        artifacts: list[dict[str, Any]],
        execution_error: str = "",
    ) -> dict[str, Any]:
        artifact_urls = [str(artifact.get("url", "")).strip() for artifact in artifacts]
        invalid_artifact_urls = [
            url for url in artifact_urls
            if url and urlparse(url).scheme not in {"http", "https"}
        ]
        local_path_leaked = any(
            pattern in deep_answer
            for pattern in (
                "/workspace/artifacts/",
                "/home/user/artifacts/",
                "/tmp/artifacts/",
                "sandbox:/mnt/data/",
            )
        )

        issues: list[str] = []
        if execution_error:
            issues.append("执行阶段出现异常")
        if local_path_leaked:
            issues.append("最终答案仍包含沙箱本地路径")
        if invalid_artifact_urls:
            issues.append("存在非 HTTP(S) 的附件链接")
        artifact_missing = not artifacts and route_decision.need_artifact_output
        if artifact_missing and issues:
            issues.append("任务需要产物输出但未生成附件")

        if issues:
            status = "error"
            summary = "最终自检未通过"
            detail = "；".join(issues)
        elif artifact_missing:
            status = "warning"
            summary = "最终自检通过（提醒：未生成附件）"
            detail = "已完成轻量自检：答案未泄漏沙箱本地路径。提醒：本次未生成附件，但附件是可选补充材料，文本结果已可直接使用。"
        else:
            status = "success"
            summary = "最终自检通过"
            detail = "已完成轻量自检：答案未泄漏沙箱本地路径，附件均为真实下载链接。"
        technical_detail = json.dumps(
            {
                "status": status,
                "used_sandbox": used_sandbox,
                "execution_error": execution_error,
                "artifact_count": len(artifacts),
                "artifact_missing": artifact_missing,
                "artifact_urls": artifact_urls,
                "invalid_artifact_urls": invalid_artifact_urls,
                "local_path_leaked": local_path_leaked,
                "route_need_sandbox": route_decision.need_sandbox,
                "route_need_file_io": route_decision.need_file_io,
                "route_need_execute": route_decision.need_execute,
                "route_need_subagent": route_decision.need_subagent,
            },
            ensure_ascii=False,
        )
        return {
            "status": status,
            "summary": summary,
            "detail": detail,
            "technical_detail": technical_detail,
        }

    @classmethod
    def _sanitize_deep_answer(cls, deep_answer: str, *, artifacts: list[dict[str, Any]]) -> str:
        if not deep_answer:
            return ""

        sanitized_lines: list[str] = []
        for raw_line in str(deep_answer).splitlines():
            line = raw_line.strip()
            if not line:
                sanitized_lines.append(raw_line)
                continue

            if (
                "点击下载" in line
                or "需在沙箱中查看" in line
                or line.startswith("文件路径：")
                or line.startswith("文件路径:")
            ):
                continue

            if any(
                marker in line
                for marker in (
                    "/workspace/artifacts/",
                    "/home/user/artifacts/",
                    "/tmp/artifacts/",
                    "sandbox:/mnt/data/",
                )
            ):
                continue

            sanitized_lines.append(raw_line)

        sanitized = "\n".join(sanitized_lines).strip()
        for pattern in _SANDBOX_LOCAL_PATH_PATTERNS:
            sanitized = re.sub(pattern, "[sandbox-artifact-path]", sanitized)

        if artifacts and sanitized:
            sanitized += "\n\n已生成可下载附件，具体下载链接以后端返回的附件列表为准。"

        return sanitized

    @classmethod
    def _preset_operation_condition(
        cls, state: AgentState
    ) -> Literal["long_term_memory_recall", "__end__"]:
        message = state["messages"][-1]
        if message.type == "ai":
            return END
        return "long_term_memory_recall"
