from __future__ import annotations

import mimetypes
import json
import re
import time
import uuid
from collections.abc import Callable
from typing import Any
from uuid import UUID
from urllib.parse import urlparse

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from internal.core.agent.entities.queue_entity import AgentThought, QueueEvent


def _stringify(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


_TODO_STATUS_ALIASES: dict[str, str] = {
    "completed": "completed",
    "complete": "completed",
    "done": "completed",
    "success": "completed",
    "succeeded": "completed",
    "finished": "completed",
    "error": "error",
    "failed": "error",
    "fail": "error",
    "failure": "error",
    "in_progress": "in_progress",
    "progress": "in_progress",
    "running": "in_progress",
    "working": "in_progress",
    "doing": "in_progress",
    "start": "in_progress",
    "pending": "pending",
    "todo": "pending",
    "to_do": "pending",
    "wait": "pending",
    "waiting": "pending",
    "not_started": "pending",
}


def _normalize_todo_status(status: Any) -> str:
    normalized = re.sub(r"[\s-]+", "_", _stringify(status, "").strip().lower())
    if not normalized:
        return "pending"
    return _TODO_STATUS_ALIASES.get(normalized, "pending")


def _normalize_todo_item(item: Any, *, position: int) -> dict[str, Any]:
    if isinstance(item, dict):
        normalized_item = dict(item)
        raw_content = (
            item.get("content")
            or item.get("text")
            or item.get("description")
            or item.get("title")
            or item.get("name")
        )
        raw_title = item.get("title") or item.get("name") or raw_content
        content = _stringify(raw_content, "").strip()
        title = _stringify(raw_title, "").strip()
        if not content:
            content = title
        if not title:
            title = content
        normalized_item["content"] = content
        normalized_item["title"] = title
        raw_status = item.get("status")
        normalized_item["status"] = _normalize_todo_status(raw_status)
        if raw_status is not None and _stringify(raw_status, "").strip():
            normalized_item["raw_status"] = _stringify(raw_status, "").strip()
        normalized_item["position"] = position
        return normalized_item

    text = _stringify(item, "").strip()
    return {
        "content": text,
        "title": text,
        "status": "pending",
        "position": position,
    }


def _normalize_todo_list(todos: Any) -> list[dict[str, Any]]:
    if not isinstance(todos, list):
        return []
    normalized = [_normalize_todo_item(item, position=index) for index, item in enumerate(todos)]
    return [
        item
        for item in normalized
        if str(item.get("content", "")).strip() or str(item.get("title", "")).strip()
    ]


class DeepTimelineMiddleware(AgentMiddleware):
    """将 deepagents 的内置工具调用转成可直接渲染的时间线事件。"""

    _IMAGE_RESULT_TOOL_NAMES = {
        "qwen_image_text_to_image",
        "qwen_image_edit",
        "qwen_image_edit_2509",
    }

    def __init__(
        self,
        *,
        task_id: UUID,
        publisher: Callable[[UUID, AgentThought], None],
    ) -> None:
        super().__init__()
        self.task_id = task_id
        self.publisher = publisher
        self._tool_steps: dict[str, UUID] = {}

    def publish_step(
        self,
        *,
        step_id: UUID,
        step_type: str,
        status: str,
        title: str,
        detail: str = "",
        technical_detail: str = "",
        tool: str = "",
        tool_input: dict[str, Any] | None = None,
        latency: float = 0,
    ) -> None:
        payload = dict(tool_input or {})
        if tool == "write_todos":
            normalized_todos = _normalize_todo_list(payload.get("todos", []))
            payload["todos"] = normalized_todos
        else:
            normalized_todos = []

        payload["timeline"] = {
            "step_type": step_type,
            "status": status,
            "title": title,
            "detail": detail,
            "technical_detail": technical_detail,
        }
        if tool == "write_todos":
            payload["timeline"]["todos"] = normalized_todos
            payload["timeline"]["todo_count"] = len(normalized_todos)
            if status == "start" and normalized_todos and not technical_detail:
                technical_detail = json.dumps(
                    normalized_todos,
                    ensure_ascii=False,
                    indent=2,
                )
                payload["timeline"]["technical_detail"] = technical_detail
        self.publisher(
            self.task_id,
            AgentThought(
                id=step_id,
                task_id=self.task_id,
                event=QueueEvent.DEEP_STEP,
                thought=detail,
                observation=technical_detail,
                tool=tool,
                tool_input=payload,
                latency=latency,
            ),
        )

    def publish_artifact(
        self,
        *,
        artifact_id: UUID,
        artifact: dict[str, Any],
        group_id: str = "",
        group_name: str = "生成图片",
    ) -> None:
        payload = dict(artifact)
        if group_id and not str(payload.get("group_id", "") or "").strip():
            payload["group_id"] = str(group_id).strip()
        if group_name and not str(payload.get("group_name", "") or "").strip():
            payload["group_name"] = str(group_name).strip()
        self.publisher(
            self.task_id,
            AgentThought(
                id=artifact_id,
                task_id=self.task_id,
                event=QueueEvent.DEEP_ARTIFACT_CREATED,
                thought=str(payload.get("name", "")),
                observation=str(payload.get("url", "")),
                tool="artifact",
                tool_input={"artifact": payload},
                latency=0,
            ),
        )

    @staticmethod
    def _extract_inline_image_urls(text: str) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()
        for pattern in (
            r"!\[[^\]]*]\((https?://[^\s)]+)\)",
            r"图片\s*\d+\s*:\s*(?:\n\s*)?URL\s*:\s*(https?://[^\s)]+)",
            r"https?://[^\s<>()]+?\.(?:png|jpg|jpeg|gif|webp|bmp|svg|tiff|tif|avif)(?:\?[^\s<>()]*)?",
        ):
            for match in re.findall(pattern, text or "", flags=re.IGNORECASE | re.DOTALL):
                normalized = str(match or "").strip().rstrip(".,;)]}")
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                urls.append(normalized)
        return urls

    @staticmethod
    def _build_image_artifact(image_url: str, *, index: int) -> dict[str, Any]:
        normalized_url = str(image_url or "").strip()
        extension = ""
        normalized_path = urlparse(normalized_url).path.lower()
        for candidate in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".tif", ".tiff", ".avif"):
            if normalized_path.endswith(candidate):
                extension = candidate.lstrip(".")
                break
        mime_type = mimetypes.guess_type(normalized_url)[0] or ""
        artifact: dict[str, Any] = {
            "name": "生成图片" if index == 1 else f"生成图片 {index}",
            "url": normalized_url,
        }
        if extension:
            artifact["extension"] = extension
        if mime_type:
            artifact["mime_type"] = mime_type
        return artifact

    def publish_complete(
        self,
        self_summary: str,
        *,
        latency: float,
        artifact_count: int,
        total_token_count: int = 0,
        total_price: float = 0.0,
    ) -> None:
        self.publisher(
            self.task_id,
            AgentThought(
                id=uuid.uuid4(),
                task_id=self.task_id,
                event=QueueEvent.DEEP_COMPLETE,
                thought=self_summary,
                observation=self_summary,
                tool="deep_complete",
                tool_input={
                    "timeline": {
                        "step_type": "reflection",
                        "status": "success",
                        "title": "整理执行结果",
                        "detail": self_summary,
                        "artifact_count": artifact_count,
                    }
                },
                total_token_count=total_token_count,
                total_price=total_price,
                latency=latency,
            ),
        )

    def _get_step_id(self, tool_call: dict[str, Any]) -> UUID:
        call_id = str(tool_call.get("id", "")).strip()
        if call_id:
            if call_id not in self._tool_steps:
                self._tool_steps[call_id] = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.task_id}:{call_id}")
            return self._tool_steps[call_id]
        return uuid.uuid4()

    @staticmethod
    def _classify_tool(tool_name: str) -> tuple[str, str]:
        if tool_name == "write_todos":
            return "plan", "拆解任务"
        if tool_name == "task":
            return "subagent", "调用子任务"
        if tool_name == "execute":
            return "tool", "执行代码"
        return "tool", f"调用工具：{tool_name}"

    @staticmethod
    def _build_start_detail(tool_name: str, args: dict[str, Any]) -> str:
        if tool_name == "write_todos":
            todos = _normalize_todo_list(args.get("todos", []))
            if todos:
                return f"共 {len(todos)} 项待办"
            return "正在拆解任务并制定执行计划"

        if tool_name == "execute":
            command = _stringify(args.get("command", ""), "")
            return command[:300] if command else "正在执行代码或命令"

        if tool_name == "task":
            description = _stringify(args.get("description", ""), "")
            subagent_type = _stringify(args.get("subagent_type", ""), "")
            prefix = f"子任务类型：{subagent_type}" if subagent_type else "启动子任务"
            if description:
                return f"{prefix}，{description[:240]}"
            return prefix

        path = args.get("file_path") or args.get("path")
        if path:
            return f"{tool_name} -> {path}"
        pattern = args.get("pattern")
        if pattern:
            return f"{tool_name} -> {pattern}"
        return _stringify(args, default="正在执行工具")[:300]

    @staticmethod
    def _extract_result_content(result: ToolMessage | Command[Any]) -> str:
        if isinstance(result, ToolMessage):
            return _stringify(result.content)
        if isinstance(result, Command):
            update = getattr(result, "update", None) or {}
            messages = update.get("messages", [])
            if messages:
                last_message = messages[-1]
                return _stringify(getattr(last_message, "content", ""))
        return _stringify(result)

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tool_name = str(request.tool_call.get("name", ""))
        tool_args = dict(request.tool_call.get("args", {}) or {})
        step_type, title = self._classify_tool(tool_name)
        step_id = self._get_step_id(request.tool_call)
        start_at = time.perf_counter()

        self.publish_step(
            step_id=step_id,
            step_type=step_type,
            status="start",
            title=title,
            detail=self._build_start_detail(tool_name, tool_args),
            tool=tool_name,
            tool_input=tool_args,
            latency=0,
        )

        try:
            result = handler(request)
        except Exception as e:
            self.publish_step(
                step_id=step_id,
                step_type=step_type,
                status="error",
                title=title,
                detail=f"{title}失败",
                technical_detail=f"{type(e).__name__}: {e}",
                tool=tool_name,
                tool_input=tool_args,
                latency=time.perf_counter() - start_at,
            )
            raise

        result_preview = self._extract_result_content(result)[:1200]
        status = "error" if isinstance(result, ToolMessage) and getattr(result, "status", "") == "error" else "success"
        self.publish_step(
            step_id=step_id,
            step_type=step_type,
            status=status,
            title=title,
            detail=result_preview or f"{title}完成",
            technical_detail=result_preview,
            tool=tool_name,
            tool_input=tool_args,
            latency=time.perf_counter() - start_at,
        )

        if status == "success" and tool_name in self._IMAGE_RESULT_TOOL_NAMES:
            image_urls = self._extract_inline_image_urls(result_preview)
            for image_index, image_url in enumerate(image_urls, start=1):
                self.publish_artifact(
                    artifact_id=uuid.uuid4(),
                    artifact=self._build_image_artifact(image_url, index=image_index),
                    group_id=str(step_id),
                    group_name="生成图片",
                )
        return result
