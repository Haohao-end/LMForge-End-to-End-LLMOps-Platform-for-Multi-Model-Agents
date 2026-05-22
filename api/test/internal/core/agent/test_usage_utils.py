from __future__ import annotations

import tiktoken
import pytest

from internal.core.agent.entities.queue_entity import AgentThought, QueueEvent
from internal.core.agent.usage_utils import (
    normalize_usage_text,
    summarize_agent_thoughts,
    track_language_model_usage,
)


_ENCODING = tiktoken.get_encoding("cl100k_base")


class _FakeModel:
    def get_pricing(self):
        return 0.001, 0.002, 1000.0

    def invoke(self, payload):
        return f"invoke:{payload}"

    def stream(self, payload):
        yield "hello"
        yield " world"

    def bind_tools(self, _tools):
        return _FakeModel()

    def with_structured_output(self, _schema):
        return _FakeModel()


def test_summarize_agent_thoughts_should_prefer_deep_complete_for_deep_phase_latency():
    thoughts = [
        AgentThought(
            id="00000000-0000-0000-0000-000000000001",
            task_id="00000000-0000-0000-0000-000000000011",
            event=QueueEvent.DEEP_STEP,
            latency=8,
        ),
        AgentThought(
            id="00000000-0000-0000-0000-000000000002",
            task_id="00000000-0000-0000-0000-000000000011",
            event=QueueEvent.DEEP_COMPLETE,
            total_token_count=120,
            total_price=0.12,
            latency=20,
        ),
        AgentThought(
            id="00000000-0000-0000-0000-000000000003",
            task_id="00000000-0000-0000-0000-000000000011",
            event=QueueEvent.AGENT_MESSAGE,
            total_token_count=30,
            total_price=0.03,
            latency=5,
        ),
    ]

    summary = summarize_agent_thoughts(thoughts)

    assert summary.total_token_count == 150
    assert summary.total_price == pytest.approx(0.15)
    assert summary.latency == 25


def test_track_language_model_usage_should_cover_nested_bindings_and_stream():
    model = _FakeModel()

    with track_language_model_usage(model) as tracker:
        structured = model.with_structured_output(dict)
        structured.invoke("route")

        bound = model.bind_tools(["weather"])
        list(bound.stream("plan"))

    expected_token_count = (
        len(_ENCODING.encode("route"))
        + len(_ENCODING.encode("invoke:route"))
        + len(_ENCODING.encode("plan"))
        + len(_ENCODING.encode("hello world"))
    )
    expected_total_price = (
        (len(_ENCODING.encode("route")) + len(_ENCODING.encode("plan"))) * 0.001
        + (len(_ENCODING.encode("invoke:route")) + len(_ENCODING.encode("hello world"))) * 0.002
    ) * 1000.0

    assert tracker.total_token_count == expected_token_count
    assert tracker.total_price == pytest.approx(expected_total_price)


def test_normalize_usage_text_should_redact_inline_base64_image_payload():
    raw_text = "prefix data:image/png;base64," + ("A" * 2048) + " suffix"

    normalized_text = normalize_usage_text(raw_text)

    assert "A" * 2048 not in normalized_text
    assert normalized_text == "prefix data:image/...;base64,[base64] suffix"


def test_track_language_model_usage_should_ignore_inline_base64_image_payload_in_token_count():
    model = _FakeModel()
    data_url = "data:image/jpeg;base64," + ("A" * 4096)
    model_input = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "请看这张图"},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    with track_language_model_usage(model) as tracker:
        tracker.record(model_input, "ok")

    expected_input_token_count = len(_ENCODING.encode(normalize_usage_text(model_input)))
    expected_output_token_count = len(_ENCODING.encode("ok"))

    assert tracker.total_token_count == expected_input_token_count + expected_output_token_count
    assert tracker.total_token_count < len(_ENCODING.encode(str(model_input)))
