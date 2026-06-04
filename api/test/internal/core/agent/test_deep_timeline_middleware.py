from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import ToolMessage

from internal.core.agent.entities.queue_entity import QueueEvent
from internal.core.agent.entities.tool_policy_entity import ToolPolicy
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


def test_wrap_tool_call_should_use_injected_tool_policy_for_image_results():
    published = []
    middleware = DeepTimelineMiddleware(
        task_id=uuid4(),
        publisher=lambda tid, thought: published.append(thought),
        tool_policy=ToolPolicy(image_result_tool_names=("custom_image_tool",)),
    )
    request = SimpleNamespace(
        tool_call={
            "id": "call-2",
            "name": "custom_image_tool",
            "args": {"prompt": "海边日落"},
        }
    )

    def handler(_request):
        return ToolMessage(
            content=(
                "图片 1:\n"
                "  URL: https://example.com/generated-1.png\n"
            ),
            tool_call_id="call-2",
        )

    result = middleware.wrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)
    artifact_events = [event for event in published if event.event == QueueEvent.DEEP_ARTIFACT_CREATED]
    assert len(artifact_events) == 1
    artifact = artifact_events[0].tool_input["artifact"]
    assert artifact["name"] == "生成图片"
    assert artifact["url"] == "https://example.com/generated-1.png"
    assert artifact["extension"] == "png"


def test_publish_complete_should_finalize_latest_todos():
    """深度执行结束时，应把最终 todo 快照作为独立事件发布。"""
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "todo-call-1",
            "name": "write_todos",
            "args": {
                "todos": [
                    {"content": "规划章节", "status": "completed"},
                    {"content": "生成 Markdown 文件", "status": "in_progress"},
                    {"content": "最终检查", "status": "pending"},
                ],
            },
        }
    )

    def handler(_request):
        return ToolMessage(content="Updated todo list", tool_call_id="todo-call-1")

    middleware.wrap_tool_call(request, handler)
    middleware.publish_complete(
        "执行完成",
        latency=1.0,
        artifact_count=1,
    )

    todo_events = [
        event for event in published
        if event.event == QueueEvent.DEEP_STEP and event.tool == "write_todos"
    ]
    assert len(todo_events) == 3
    process_todo_event = todo_events[1]
    final_todo_event = todo_events[-1]
    assert process_todo_event.id == todo_events[0].id
    assert final_todo_event.id != todo_events[0].id
    assert final_todo_event.tool_input["timeline"]["status"] == "success"
    assert final_todo_event.tool_input["timeline"]["step_type"] == "reflection"
    assert final_todo_event.tool_input["timeline"]["phase"] == "final_snapshot"
    assert final_todo_event.tool_input["timeline"]["source_step_id"] == str(todo_events[0].id)
    assert [
        todo["status"]
        for todo in final_todo_event.tool_input["todos"]
    ] == ["completed", "completed", "completed"]


def test_wrap_tool_call_should_publish_execute_preview_and_result_metadata():
    """execute 工具应同时保留命令预览与结果预览。"""
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "exec-1",
            "name": "execute",
            "args": {
                "command": "python3 -c 'print(\"hello\")'",
            },
        }
    )

    def handler(_request):
        return ToolMessage(content="hello\n", tool_call_id="exec-1")

    result = middleware.wrap_tool_call(request, handler)

    assert isinstance(result, ToolMessage)
    step_events = [event for event in published if event.event == QueueEvent.DEEP_STEP]
    assert len(step_events) == 2
    start_event, final_event = step_events
    assert start_event.tool_input["timeline"]["phase"] == "start"
    assert start_event.tool_input["timeline"]["preview_kind"] == "command"
    assert start_event.tool_input["timeline"]["result_kind"] == "stdout"
    assert start_event.tool_input["timeline"]["recoverable"] is False
    assert final_event.tool_input["timeline"]["status"] == "success"
    assert final_event.tool_input["timeline"]["preview_kind"] == "command"
    assert final_event.tool_input["timeline"]["preview"].startswith("python3 -c")
    assert final_event.tool_input["timeline"]["result_preview"] == "hello\n"
    assert final_event.tool_input["timeline"]["output_empty"] is False
    assert final_event.tool_input["timeline"]["recovered"] is False


def test_wrap_tool_call_should_mark_execute_empty_stdout():
    """execute 的 stdout 为空时，仍应保留命令预览并标记无输出。"""
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "exec-2",
            "name": "execute",
            "args": {
                "command": "python3 -c 'pass'",
            },
        }
    )

    def handler(_request):
        return ToolMessage(content="", tool_call_id="exec-2")

    middleware.wrap_tool_call(request, handler)

    step_events = [event for event in published if event.event == QueueEvent.DEEP_STEP]
    assert len(step_events) == 2
    final_event = step_events[-1]
    assert final_event.tool_input["timeline"]["preview_kind"] == "command"
    assert final_event.tool_input["timeline"]["result_preview"] == ""
    assert final_event.tool_input["timeline"]["output_empty"] is True


def test_wrap_tool_call_should_treat_write_file_errors_as_recoverable_warning():
    """write_file 的协议错误应先以 warning 形式展示，而不是直接红色失败。"""
    published = []
    middleware = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))
    request = SimpleNamespace(
        tool_call={
            "id": "write-1",
            "name": "write_file",
            "args": {
                "path": "SpaceX_IPO_Prospectus_Draft.txt",
                "content": "final prospectus text",
            },
        }
    )

    def handler(_request):
        return ToolMessage(content="protocol mismatch", tool_call_id="write-1", status="error")

    middleware.wrap_tool_call(request, handler)

    step_events = [event for event in published if event.event == QueueEvent.DEEP_STEP]
    assert len(step_events) == 2
    start_event, final_event = step_events
    assert start_event.tool_input["timeline"]["preview_kind"] == "protocol"
    assert final_event.tool_input["timeline"]["status"] == "warning"
    assert final_event.tool_input["timeline"]["phase"] == "warning"
    assert final_event.tool_input["timeline"]["error_kind"] == "protocol_error"
    assert final_event.tool_input["timeline"]["recoverable"] is True
    assert final_event.tool_input["timeline"]["recovered"] is False
    assert final_event.tool_input["timeline"]["result_preview"] == "protocol mismatch"
