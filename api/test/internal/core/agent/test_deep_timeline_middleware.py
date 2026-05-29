from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import ToolMessage

from internal.core.agent.entities.queue_entity import QueueEvent
from internal.core.agent.middleware import DeepTimelineMiddleware


def test_wrap_tool_call_should_publish_image_artifact_events_for_qwen_results():
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "call-1",
            "name": "qwen_image_text_to_image",
            "args": {"prompt": "上海初夏旅行穿搭"},
        }
    )

    def handler(_request):
        return ToolMessage(
            content=(
                "✓ 成功生成图像\n"
                "图片 1:\n  URL: https://example.com/generated-1.png\n"
                "图片 2:\n  URL: https://example.com/generated-2.png\n"
            ),
            tool_call_id="call-1",
        )

    result = middleware.wrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)
    assert any(event.event == QueueEvent.DEEP_STEP for event in published)
    artifact_events = [event for event in published if event.event == QueueEvent.DEEP_ARTIFACT_CREATED]
    assert len(artifact_events) == 2

    step_id = str(middleware._get_step_id(request.tool_call))
    first_artifact = artifact_events[0].tool_input["artifact"]
    second_artifact = artifact_events[1].tool_input["artifact"]
    assert first_artifact["name"] == "生成图片"
    assert first_artifact["url"] == "https://example.com/generated-1.png"
    assert first_artifact["extension"] == "png"
    assert first_artifact["mime_type"] == "image/png"
    assert first_artifact["group_id"] == step_id
    assert first_artifact["group_name"] == "生成图片"
    assert second_artifact["url"] == "https://example.com/generated-2.png"
    assert second_artifact["group_id"] == step_id
