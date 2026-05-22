from __future__ import annotations

import re
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import tiktoken

from internal.core.agent.entities.queue_entity import QueueEvent


_ENCODING = tiktoken.get_encoding("cl100k_base")
_DATA_URL_PATTERN = re.compile(
    r"data:[^;]+;base64,[A-Za-z0-9+/=]+",
    re.IGNORECASE,
)


def _to_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _to_non_negative_float(value: Any) -> float:
    try:
        return max(0.0, float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _get_event_value(event: Any) -> str:
    return str(getattr(event, "value", event) or "")


def normalize_usage_text(value: Any) -> str:
    """归一化用于 token 估算的文本，避免把 base64 图片内容计入 token。"""
    text = str(value or "")
    if not text:
        return ""
    return _DATA_URL_PATTERN.sub("data:image/...;base64,[base64]", text)


@dataclass(slots=True)
class AgentUsageSummary:
    total_token_count: int = 0
    total_price: float = 0.0
    latency: float = 0.0


def summarize_agent_thoughts(agent_thoughts: Iterable[Any]) -> AgentUsageSummary:
    """聚合消息级 token / price / latency。

    说明：
    - token 与 price 直接按已去重 thought 列表求和。
    - latency 对 deep_complete 做去重处理；该事件是深度阶段总耗时摘要，
      若与各 deep_step 一起累加会明显高估总耗时。
    """
    total_token_count = 0
    total_price = 0.0
    regular_latency = 0.0
    deep_phase_step_latency = 0.0
    deep_phase_complete_latency = 0.0
    max_latency = 0.0

    for agent_thought in agent_thoughts:
        total_token_count += _to_non_negative_int(getattr(agent_thought, "total_token_count", 0))
        total_price += _to_non_negative_float(getattr(agent_thought, "total_price", 0.0))

        latency = _to_non_negative_float(getattr(agent_thought, "latency", 0.0))
        max_latency = max(max_latency, latency)
        event = _get_event_value(getattr(agent_thought, "event", ""))
        if event == QueueEvent.DEEP_COMPLETE.value:
            deep_phase_complete_latency = max(deep_phase_complete_latency, latency)
        elif event in {
            QueueEvent.DEEP_THINKING.value,
            QueueEvent.DEEP_STEP.value,
            QueueEvent.DEEP_ARTIFACT_CREATED.value,
        }:
            deep_phase_step_latency += latency
        else:
            regular_latency += latency

    total_latency = regular_latency + (
        deep_phase_complete_latency or deep_phase_step_latency
    )

    return AgentUsageSummary(
        total_token_count=total_token_count,
        total_price=total_price,
        latency=total_latency or max_latency,
    )


@dataclass(slots=True)
class LanguageModelUsageTracker:
    """在不依赖 provider usage metadata 的情况下，估算 LLM 调用成本。"""

    input_price: float = 0.0
    output_price: float = 0.0
    price_unit: float = 0.0
    total_token_count: int = 0
    total_price: float = 0.0
    _patched_models: dict[int, dict[str, Any]] = field(default_factory=dict)

    def patch_model(self, model: Any) -> Any:
        if model is None:
            return model

        model_id = id(model)
        if model_id in self._patched_models:
            return model

        originals: dict[str, Any] = {}
        for method_name in ("invoke", "stream", "bind_tools", "with_structured_output", "bind"):
            original = getattr(model, method_name, None)
            if callable(original):
                originals[method_name] = original

        if not originals:
            return model

        self._patched_models[model_id] = {
            "model": model,
            "originals": originals,
        }

        if "invoke" in originals:
            original_invoke = originals["invoke"]

            def invoke_wrapper(*args, **kwargs):
                result = original_invoke(*args, **kwargs)
                self.record(args[0] if args else kwargs.get("input", ""), result)
                return result

            object.__setattr__(model, "invoke", invoke_wrapper)

        if "stream" in originals:
            original_stream = originals["stream"]

            def stream_wrapper(*args, **kwargs):
                gathered = None
                for chunk in original_stream(*args, **kwargs):
                    if gathered is None:
                        gathered = chunk
                    else:
                        try:
                            gathered += chunk
                        except Exception:
                            gathered = chunk
                    yield chunk

                if gathered is not None:
                    self.record(args[0] if args else kwargs.get("input", ""), gathered)

            object.__setattr__(model, "stream", stream_wrapper)

        for method_name in ("bind_tools", "with_structured_output", "bind"):
            if method_name not in originals:
                continue
            original_method = originals[method_name]

            def binder_wrapper(*args, __original=original_method, **kwargs):
                bound_model = __original(*args, **kwargs)
                return self.patch_model(bound_model)

            object.__setattr__(model, method_name, binder_wrapper)

        return model

    def restore(self) -> None:
        for payload in reversed(list(self._patched_models.values())):
            model = payload["model"]
            for method_name, original in payload["originals"].items():
                object.__setattr__(model, method_name, original)
        self._patched_models.clear()

    def record(self, model_input: Any, model_output: Any) -> None:
        input_token_count = len(_ENCODING.encode(normalize_usage_text(model_input)))
        output_token_count = len(_ENCODING.encode(normalize_usage_text(model_output)))
        self.total_token_count += input_token_count + output_token_count
        self.total_price += (
            input_token_count * self.input_price + output_token_count * self.output_price
        ) * self.price_unit


@contextmanager
def track_language_model_usage(model: Any):
    get_pricing = getattr(model, "get_pricing", None)
    pricing = get_pricing() if callable(get_pricing) else (0.0, 0.0, 0.0)
    tracker = LanguageModelUsageTracker(
        input_price=_to_non_negative_float(pricing[0] if len(pricing) > 0 else 0.0),
        output_price=_to_non_negative_float(pricing[1] if len(pricing) > 1 else 0.0),
        price_unit=_to_non_negative_float(pricing[2] if len(pricing) > 2 else 0.0),
    )
    tracker.patch_model(model)
    try:
        yield tracker
    finally:
        tracker.restore()
