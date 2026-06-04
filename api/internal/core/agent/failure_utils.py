from __future__ import annotations

from typing import Any

from internal.core.agent.entities.queue_entity import QueueEvent


_TIMEOUT_HINTS = (
    "timeout",
    "timed out",
    "deadline exceeded",
    "504",
)


def classify_failure_event(error: Any) -> QueueEvent:
    """将异常归类为 timeout / error 终态事件。

    这里不依赖具体 provider 异常类型，只依赖类名和消息文本，避免耦合。
    """
    if isinstance(error, TimeoutError):
        return QueueEvent.TIMEOUT

    error_type_name = type(error).__name__.lower()
    error_module = type(error).__module__.lower()
    error_text = str(error or "").strip().lower()
    normalized = " ".join([error_type_name, error_module, error_text]).strip()

    if any(hint in normalized for hint in _TIMEOUT_HINTS):
        return QueueEvent.TIMEOUT

    return QueueEvent.ERROR


def build_failure_observation(error: Any, context: str = "") -> str:
    """构造可展示的失败说明文本。"""
    normalized_context = str(context or "").strip()
    normalized_error = str(error or "").strip()

    if normalized_context and normalized_error:
        if normalized_error in normalized_context:
            return normalized_context
        return f"{normalized_context}: {normalized_error}"

    if normalized_context:
        return normalized_context

    return normalized_error
