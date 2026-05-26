import json
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


def test_wrap_tool_call_should_normalize_write_todos_payload_and_statuses():
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "call-write-todos",
            "name": "write_todos",
            "args": {
                "todos": [
                    {"content": "收集景点", "status": "completed"},
                    {"title": "预订酒店", "status": "done"},
                    {"content": "规划路线", "status": "in_progress"},
                    {"title": "确认行程", "status": "failed"},
                ]
            },
        }
    )

    def handler(_request):
        return ToolMessage(content="已写入待办", tool_call_id="call-write-todos")

    result = middleware.wrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)

    start_event = next(
        event
        for event in published
        if event.event == QueueEvent.DEEP_STEP and event.tool_input["timeline"]["status"] == "start"
    )
    timeline = start_event.tool_input["timeline"]
    todos = timeline["todos"]

    assert timeline["step_type"] == "plan"
    assert timeline["title"] == "拆解任务"
    assert timeline["detail"] == "共 4 项待办"
    assert timeline["todo_count"] == 4
    assert start_event.tool_input["todos"] == todos
    assert todos[0]["content"] == "收集景点"
    assert todos[0]["title"] == "收集景点"
    assert todos[0]["status"] == "completed"
    assert todos[1]["content"] == "预订酒店"
    assert todos[1]["title"] == "预订酒店"
    assert todos[1]["status"] == "completed"
    assert todos[2]["content"] == "规划路线"
    assert todos[2]["status"] == "in_progress"
    assert todos[3]["content"] == "确认行程"
    assert todos[3]["status"] == "error"
    assert "raw_status" in todos[1] and todos[1]["raw_status"] == "done"
    assert json.loads(timeline["technical_detail"])[1]["content"] == "预订酒店"
