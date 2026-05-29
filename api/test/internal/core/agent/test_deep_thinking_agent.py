"""DeepThinkingAgent 和 BaiduCfcSandboxBackend 的完整测试套件。

测试分层：
    Unit Tests  — 不需要网络，Mock 所有外部依赖
    Integration — 需要真实的百度 CFC 沙箱（标记 @pytest.mark.integration）

运行方式：
    # 只跑单元测试（快，无网络）
    pytest test/internal/core/agent/test_deep_thinking_agent.py -v -k "not integration"

    # 跑集成测试（需要 .env 中配置 E2B_API_KEY / E2B_DOMAIN）
    pytest test/internal/core/agent/test_deep_thinking_agent.py -v -m integration
"""
from __future__ import annotations

import os
import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from internal.core.agent.agents.deep_thinking_agent import DeepRouteDecision, DeepThinkingAgent
from internal.core.agent.backends.baidu_cfc_sandbox_backend import BaiduCfcSandboxBackend
from internal.core.agent.entities.agent_entity import AgentConfig, DEEP_THINKING_SYSTEM_PROMPT
from internal.core.agent.entities.queue_entity import AgentThought, QueueEvent
from internal.core.agent.middleware import DeepTimelineMiddleware
from internal.core.language_model.entities.model_entity import BaseLanguageModel, ModelFeature
from internal.entity.conversation_entity import InvokeFrom


# ============================================================
#  通用 Mock 工具
# ============================================================

def _make_chunk(content="", tool_calls=None):
    """构造 Mock LLM chunk。"""
    chunk = MagicMock()
    chunk.content = content
    chunk.tool_calls = tool_calls or []
    chunk.__add__ = lambda self, other: _make_chunk(
        self.content + (other.content or ""), self.tool_calls or other.tool_calls
    )
    return chunk


def _make_llm(features=None, stream_chunks=None):
    """构造 Mock BaseLanguageModel。"""
    if features is None:
        features = [ModelFeature.TOOL_CALL.value]
    if stream_chunks is None:
        stream_chunks = [_make_chunk("这是深度思考后的答案")]

    llm = MagicMock(spec=BaseLanguageModel)
    llm.features = features
    llm.stream.return_value = iter(stream_chunks)
    llm.get_pricing.return_value = (0.001, 0.002, 1000.0)
    llm.convert_to_human_message.side_effect = lambda q, imgs=None: HumanMessage(content=q)
    return llm


def _make_agent_config(enable_deep_thinking=True, **kwargs):
    """构造 AgentConfig。"""
    return AgentConfig(
        user_id=uuid4(),
        invoke_from=InvokeFrom.DEBUGGER.value,
        preset_prompt="你是测试助手",
        enable_deep_thinking=enable_deep_thinking,
        **kwargs,
    )


# ============================================================
#  Unit Tests: BaiduCfcSandboxBackend
# ============================================================

class TestBaiduCfcSandboxBackend:
    """百度 CFC 沙箱后端单元测试（全部 Mock，无需网络）。"""

    def test_init_requires_api_key(self):
        """缺少 API Key 时应抛出 ValueError。"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("E2B_API_KEY", None)
            os.environ.pop("E2B_DOMAIN", None)
            with pytest.raises(ValueError, match="E2B_API_KEY"):
                BaiduCfcSandboxBackend(domain="test.example.com")

    def test_init_requires_domain(self):
        """缺少 Domain 时应抛出 ValueError。"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("E2B_DOMAIN", None)
            with pytest.raises(ValueError, match="E2B_DOMAIN"):
                BaiduCfcSandboxBackend(api_key="test-key")

    def test_init_reads_env_vars(self):
        """应从环境变量读取配置。"""
        with patch.dict(os.environ, {
            "E2B_API_KEY": "env-key-123",
            "E2B_DOMAIN":  "env-domain.example.com",
        }):
            backend = BaiduCfcSandboxBackend()
            assert backend._api_key == "env-key-123"
            assert backend._domain  == "env-domain.example.com"

    def test_init_reads_template_env_vars(self):
        """应从环境变量读取模板名和 fallback 模板名。"""
        with patch.dict(os.environ, {
            "E2B_API_KEY": "env-key-123",
            "E2B_DOMAIN":  "env-domain.example.com",
            "SANDBOX_TEMPLATE_ALIAS": "lite-template",
            "SANDBOX_FALLBACK_TEMPLATE_ALIAS": "fallback-template",
        }):
            backend = BaiduCfcSandboxBackend()
            assert backend._template_alias == "lite-template"
            assert backend._fallback_template_alias == "fallback-template"

    def test_id_property(self):
        """id 属性应返回非空字符串。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")
        assert isinstance(backend.id, str)
        assert len(backend.id) > 0

    def test_execute_success(self):
        """execute() 成功时应返回正确的 ExecuteResponse。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        # Mock e2b Sandbox
        mock_result = MagicMock()
        mock_result.stdout   = "hello world\n"
        mock_result.stderr   = ""
        mock_result.exit_code = 0

        mock_sbx = MagicMock()
        mock_sbx.commands.run.return_value = mock_result
        mock_sbx.sandbox_id = "test-sandbox-id"
        backend._sbx = mock_sbx

        result = backend.execute("echo hello world")

        assert result.exit_code == 0
        assert "hello world" in result.output
        assert result.truncated is False
        mock_sbx.commands.run.assert_called_once_with("echo hello world", timeout=60)

    def test_execute_with_stderr(self):
        """execute() 有 stderr 输出时应加 [stderr] 前缀。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_result = MagicMock()
        mock_result.stdout    = "ok\n"
        mock_result.stderr    = "warning: something\n"
        mock_result.exit_code = 0

        mock_sbx = MagicMock()
        mock_sbx.commands.run.return_value = mock_result
        backend._sbx = mock_sbx

        result = backend.execute("python3 script.py")

        assert "[stderr]" in result.output
        assert "warning: something" in result.output

    def test_execute_truncates_large_output(self):
        """超过 100000 字节的输出应被截断。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_result = MagicMock()
        mock_result.stdout    = "x" * 200_000   # 200KB 输出
        mock_result.stderr    = ""
        mock_result.exit_code = 0

        mock_sbx = MagicMock()
        mock_sbx.commands.run.return_value = mock_result
        backend._sbx = mock_sbx

        result = backend.execute("cat huge_file")

        assert result.truncated is True
        assert len(result.output) < 110_000  # 截断后不超过阈值 + 提示文字

    def test_execute_handles_exception(self):
        """execute() 遇到异常时应返回 exit_code=1 而非抛出。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_sbx = MagicMock()
        mock_sbx.commands.run.side_effect = RuntimeError("连接超时")
        backend._sbx = mock_sbx

        result = backend.execute("ls /")

        assert result.exit_code == 1
        assert "RuntimeError" in result.output or "连接超时" in result.output

    def test_execute_custom_timeout(self):
        """execute() 应使用自定义 timeout 参数。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d", timeout=30)

        mock_result = MagicMock()
        mock_result.stdout    = "ok"
        mock_result.stderr    = ""
        mock_result.exit_code = 0

        mock_sbx = MagicMock()
        mock_sbx.commands.run.return_value = mock_result
        backend._sbx = mock_sbx

        backend.execute("long_cmd", timeout=120)

        mock_sbx.commands.run.assert_called_once_with("long_cmd", timeout=120)

    def test_create_sandbox_uses_template_fallback(self):
        """当主模板创建失败时，应自动尝试 fallback 模板。"""
        backend = BaiduCfcSandboxBackend(
            api_key="k",
            domain="d",
            timeout=30,
            sandbox_timeout=90,
            template_alias="lite-template",
            fallback_template_alias="fallback-template",
        )

        mock_result = MagicMock()
        mock_result.stdout = "ok\n"
        mock_result.stderr = ""
        mock_result.exit_code = 0

        mock_sbx = MagicMock()
        mock_sbx.commands.run.return_value = mock_result
        with patch("e2b_code_interpreter.Sandbox.create", side_effect=[RuntimeError("template missing"), mock_sbx]) as create_mock:
            result = backend.execute("echo ok")

        assert result.exit_code == 0
        assert "ok" in result.output
        assert create_mock.call_count == 2
        assert create_mock.call_args_list[0].kwargs["template"] == "lite-template"
        assert create_mock.call_args_list[1].kwargs["template"] == "fallback-template"
        assert create_mock.call_args_list[0].kwargs["timeout"] == 90
        assert create_mock.call_args_list[1].kwargs["timeout"] == 90
        assert backend._active_template_alias == "fallback-template"

    def test_create_sandbox_without_template_keeps_legacy_behavior(self):
        """未配置模板时，应保持旧的 Sandbox.create(timeout=...) 行为。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d", sandbox_timeout=42)

        mock_sbx = MagicMock()
        with patch("e2b_code_interpreter.Sandbox.create", return_value=mock_sbx) as create_mock:
            sandbox = backend._get_sandbox()

        assert sandbox is mock_sbx
        assert create_mock.call_count == 1
        assert create_mock.call_args.kwargs == {"timeout": 42}
        assert backend._active_template_alias is None

    def test_upload_files_success(self):
        """upload_files() 成功时应返回无错误的响应列表。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_sbx = MagicMock()
        mock_sbx.files.write.return_value = None
        backend._sbx = mock_sbx

        responses = backend.upload_files([
            ("/workspace/hello.py", b"print('hello')"),
            ("/workspace/data.txt", b"some data"),
        ])

        assert len(responses) == 2
        assert all(r.error is None for r in responses)
        assert mock_sbx.files.write.call_count == 2

    def test_upload_files_partial_failure(self):
        """upload_files() 部分失败时应单独标记错误，不影响其他文件。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_sbx = MagicMock()
        mock_sbx.files.write.side_effect = [
            None,                            # 第一个文件成功
            IOError("磁盘空间不足"),          # 第二个文件失败
        ]
        backend._sbx = mock_sbx

        responses = backend.upload_files([
            ("/ok.py", b"content"),
            ("/fail.py", b"content"),
        ])

        assert responses[0].error is None
        assert responses[1].error is not None
        assert "磁盘空间不足" in responses[1].error

    def test_download_files_success(self):
        """download_files() 成功时应返回正确的字节内容。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_sbx = MagicMock()
        mock_sbx.files.read.return_value = b"file content here"
        backend._sbx = mock_sbx

        responses = backend.download_files(["/workspace/result.txt"])

        assert len(responses) == 1
        assert responses[0].content == b"file content here"
        assert responses[0].error is None

    def test_close_kills_sandbox(self):
        """close() 应调用 sandbox.kill() 并清空 _sbx。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")

        mock_sbx = MagicMock()
        backend._sbx = mock_sbx

        backend.close()

        mock_sbx.kill.assert_called_once()
        assert backend._sbx is None

    def test_context_manager(self):
        """作为上下文管理器时，__exit__ 应自动关闭沙箱。"""
        backend = BaiduCfcSandboxBackend(api_key="k", domain="d")
        mock_sbx = MagicMock()
        backend._sbx = mock_sbx

        with backend:
            pass  # 进入上下文

        mock_sbx.kill.assert_called_once()


# ============================================================
#  Unit Tests: AgentConfig
# ============================================================

class TestAgentConfig:
    """AgentConfig 扩展字段测试。"""

    def test_enable_deep_thinking_default_false(self):
        """enable_deep_thinking 默认应为 False。"""
        config = AgentConfig(user_id=uuid4(), invoke_from=InvokeFrom.DEBUGGER.value)
        assert config.enable_deep_thinking is False

    def test_enable_deep_thinking_can_be_set(self):
        """enable_deep_thinking 应可设置为 True。"""
        config = AgentConfig(
            user_id=uuid4(),
            invoke_from=InvokeFrom.DEBUGGER.value,
            enable_deep_thinking=True,
        )
        assert config.enable_deep_thinking is True

    def test_deep_thinking_prompt_has_required_placeholders(self):
        """DEEP_THINKING_SYSTEM_PROMPT 应包含 {preset_prompt} 和 {long_term_memory} 占位符。"""
        assert "{preset_prompt}" in DEEP_THINKING_SYSTEM_PROMPT
        assert "{long_term_memory}" in DEEP_THINKING_SYSTEM_PROMPT

    def test_deep_thinking_prompt_format(self):
        """DEEP_THINKING_SYSTEM_PROMPT.format() 应正常工作。"""
        filled = DEEP_THINKING_SYSTEM_PROMPT.format(
            preset_prompt="你是助手",
            long_term_memory="用户喜欢简洁",
        )
        assert "你是助手" in filled
        assert "用户喜欢简洁" in filled


# ============================================================
#  Unit Tests: QueueEvent
# ============================================================

class TestQueueEvent:
    """QueueEvent 枚举测试。"""

    def test_deep_thinking_event_exists(self):
        """DEEP_THINKING 枚举值应存在且值为 'deep_thinking'。"""
        assert QueueEvent.DEEP_THINKING == "deep_thinking"
        assert QueueEvent.DEEP_THINKING.value == "deep_thinking"
        assert QueueEvent.DEEP_STEP == "deep_step"
        assert QueueEvent.DEEP_COMPLETE == "deep_complete"
        assert QueueEvent.DEEP_ARTIFACT_CREATED == "deep_artifact_created"

    def test_existing_events_unchanged(self):
        """添加 DEEP_THINKING 后，原有事件不应改变。"""
        assert QueueEvent.AGENT_MESSAGE  == "agent_message"
        assert QueueEvent.AGENT_THOUGHT  == "agent_thought"
        assert QueueEvent.AGENT_ACTION   == "agent_action"
        assert QueueEvent.AGENT_END      == "agent_end"
        assert QueueEvent.DATASET_RETRIEVAL == "dataset_retrieval"


# ============================================================
#  Unit Tests: DeepThinkingAgent 图结构
# ============================================================

class TestDeepThinkingAgentGraph:
    """DeepThinkingAgent LangGraph 图结构测试。"""

    def _build_agent(self):
        llm = _make_llm()
        config = _make_agent_config(enable_deep_thinking=True)
        return DeepThinkingAgent(llm=llm, agent_config=config)

    @staticmethod
    def _build_state(query: str = "帮我写一个排序算法"):
        return {
            "messages": [HumanMessage(content=query)],
            "task_id": uuid4(),
            "iteration_count": 0,
            "history": [],
            "long_term_memory": "",
        }

    @staticmethod
    def _route(**overrides):
        payload = {
            "need_sandbox": False,
            "need_file_io": False,
            "need_execute": False,
            "need_subagent": False,
            "need_artifact_output": False,
            "reason": "测试路由",
            "summary": "无需沙箱，使用普通深度思考",
        }
        payload.update(overrides)
        return DeepRouteDecision(
            **payload,
        )

    def test_graph_compiles_without_error(self):
        """_build_agent() 应能成功编译 LangGraph 图，不抛异常。"""
        agent = self._build_agent()
        assert agent._agent is not None

    @patch.object(DeepThinkingAgent, "_build_deep_agent")
    @patch.object(DeepThinkingAgent, "_decide_deep_route")
    def test_deep_agent_node_publishes_timeline_events(self, mock_route, mock_build_deep):
        """_deep_agent_node 应发布 Timeline 事件和完成事件。"""
        mock_route.return_value = self._route()
        mock_deep_agent = MagicMock()
        mock_deep_agent.invoke.return_value = {
            "messages": [AIMessage(content="深度思考后的规划结果")],
        }
        mock_build_deep.return_value = (mock_deep_agent, MagicMock(), "/workspace/artifacts/test", False)

        agent = self._build_agent()
        published = []
        agent.agent_queue_manager.publish = lambda tid, thought: published.append(thought)

        agent._deep_agent_node(self._build_state())

        assert any(event.event == QueueEvent.DEEP_STEP for event in published)
        assert any(event.event == QueueEvent.DEEP_COMPLETE for event in published)

    @patch.object(DeepThinkingAgent, "_build_deep_agent")
    @patch.object(DeepThinkingAgent, "_decide_deep_route")
    def test_deep_agent_node_graceful_degradation(self, mock_route, mock_build_deep):
        """deepagents 初始化失败时，应优雅降级。"""
        mock_route.return_value = self._route()
        mock_build_deep.side_effect = ImportError("deepagents 未安装")

        agent = self._build_agent()
        published = []
        agent.agent_queue_manager.publish = lambda tid, thought: published.append(thought)

        result = agent._deep_agent_node(self._build_state("test"))

        assert isinstance(result, dict)
        assert result["messages"] == []
        assert any(
            event.event == QueueEvent.DEEP_STEP and "deepagents 未安装" in event.observation
            for event in published
        )

    @patch.object(DeepThinkingAgent, "_build_deep_agent")
    @patch.object(DeepThinkingAgent, "_decide_deep_route")
    def test_deep_agent_node_injects_context_to_messages(self, mock_route, mock_build_deep):
        """_deep_agent_node 应将深度思考摘要注入 messages。"""
        mock_route.return_value = self._route(
            need_sandbox=True,
            need_execute=True,
            summary="需要沙箱执行",
        )
        mock_deep_agent = MagicMock()
        mock_deep_agent.invoke.return_value = {
            "messages": [AIMessage(content="规划：先做A，再做B")],
        }
        mock_build_deep.return_value = (mock_deep_agent, MagicMock(), "/workspace/artifacts/test", True)

        agent = self._build_agent()
        agent.agent_queue_manager.publish = MagicMock()

        result = agent._deep_agent_node(self._build_state("帮我写代码"))

        assert "messages" in result
        msgs = result["messages"]
        assert any(isinstance(message, AIMessage) for message in msgs)
        assert "<deep_execution_summary>" in msgs[0].content
        assert "<deep_thinking_result>" in msgs[0].content

    @patch.object(DeepThinkingAgent, "_build_deep_agent")
    def test_deep_agent_node_should_publish_deep_usage_totals(self, mock_build_deep):
        llm = _make_llm()

        structured_llm = MagicMock()
        structured_llm.invoke.return_value = self._route()
        llm.with_structured_output.return_value = structured_llm

        tool_llm = MagicMock()
        tool_llm.invoke.return_value = "工具调用完成"
        object.__setattr__(llm, "bind_tools", MagicMock(return_value=tool_llm))

        agent = DeepThinkingAgent(llm=llm, agent_config=_make_agent_config(enable_deep_thinking=True))
        published = []
        agent.agent_queue_manager.publish = lambda tid, thought: published.append(thought)

        class _DeepAgent:
            def invoke(self, _payload):
                llm.bind_tools(["weather"]).invoke("查询上海天气")
                return {
                    "messages": [AIMessage(content="深度思考后的规划结果")],
                }

        mock_build_deep.return_value = (_DeepAgent(), MagicMock(), "/workspace/artifacts/test", False)

        agent._deep_agent_node(self._build_state("请生成上海旅行规划"))

        complete_event = next(
            event for event in published if event.event == QueueEvent.DEEP_COMPLETE
        )
        assert complete_event.total_token_count > 0
        assert complete_event.total_price > 0

    def test_build_deep_agent_uses_sandbox_when_env_set(self):
        """配置完整且路由要求沙箱时，应构建 BaiduCfcSandboxBackend。"""
        captured = {}
        agent = self._build_agent()
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda *_: None)
        task_id = uuid4()
        route = self._route(
            need_sandbox=True,
            need_execute=True,
            summary="需要沙箱执行",
        )

        def capture_create_deep_agent(*args, **kwargs):
            captured["backend"] = kwargs.get("backend")
            captured["middleware"] = kwargs.get("middleware")
            return MagicMock()

        with patch("deepagents.create_deep_agent", side_effect=capture_create_deep_agent), \
             patch.object(BaiduCfcSandboxBackend, "ensure_ready", return_value=None), \
             patch.object(
                 BaiduCfcSandboxBackend,
                 "execute",
                 return_value=SimpleNamespace(exit_code=0, output=f"/home/user/artifacts/{task_id}"),
             ), \
             patch.dict(os.environ, {
                "E2B_API_KEY": "test-key",
                "E2B_DOMAIN": "sandbox.example.com",
             }, clear=False):
            _, backend, artifact_root, used_sandbox = agent._build_deep_agent(
                task_id=task_id,
                route_decision=route,
                timeline=timeline,
            )

        assert isinstance(backend, BaiduCfcSandboxBackend)
        assert used_sandbox is True
        assert artifact_root == f"/home/user/artifacts/{task_id}"
        assert isinstance(captured["middleware"][0], DeepTimelineMiddleware)

    def test_build_deep_agent_fallback_to_state_backend(self):
        """未请求沙箱时，应使用 StateBackend。"""
        captured = {}
        agent = self._build_agent()
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda *_: None)
        route = self._route()

        def capture_create_deep_agent(*args, **kwargs):
            captured["backend"] = kwargs.get("backend")
            return MagicMock()

        with patch("deepagents.create_deep_agent", side_effect=capture_create_deep_agent), \
             patch.dict(os.environ, {}, clear=True):
            _, backend, _, used_sandbox = agent._build_deep_agent(
                task_id=uuid4(),
                route_decision=route,
                timeline=timeline,
            )

        assert type(backend).__name__ == "StateBackend"
        assert type(captured["backend"]).__name__ == "StateBackend"
        assert used_sandbox is False

    def test_build_deep_agent_uses_template_config_from_env(self):
        """SANDBOX_* 环境变量应正确映射到沙箱模板配置。"""
        captured_backend = {}
        agent = self._build_agent()
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda *_: None)
        task_id = uuid4()
        route = self._route(
            need_sandbox=True,
            need_execute=True,
            summary="需要沙箱执行",
        )

        def capture_create_deep_agent(*args, **kwargs):
            captured_backend["backend"] = kwargs.get("backend")
            return MagicMock()

        with patch("deepagents.create_deep_agent", side_effect=capture_create_deep_agent), \
             patch.object(BaiduCfcSandboxBackend, "ensure_ready", return_value=None) as ensure_ready_mock, \
             patch.object(
                 BaiduCfcSandboxBackend,
                 "execute",
                 return_value=SimpleNamespace(exit_code=0, output=f"/home/user/artifacts/{task_id}"),
             ), \
             patch.dict(os.environ, {
                "E2B_API_KEY": "test-key",
                "E2B_DOMAIN": "sandbox.example.com",
                "SANDBOX_TEMPLATE_ALIAS": "lite-template",
                "SANDBOX_FALLBACK_TEMPLATE_ALIAS": "fallback-template",
                "SANDBOX_TIMEOUT_SECONDS": "123",
                "SANDBOX_EXECUTE_TIMEOUT_SECONDS": "45",
             }, clear=False):
            _, backend, artifact_root, used_sandbox = agent._build_deep_agent(
                task_id=task_id,
                route_decision=route,
                timeline=timeline,
            )

        assert isinstance(backend, BaiduCfcSandboxBackend)
        assert backend._template_alias == "lite-template"
        assert backend._fallback_template_alias == "fallback-template"
        assert backend._sandbox_timeout == 123
        assert backend._timeout == 45
        assert used_sandbox is True
        assert artifact_root == f"/home/user/artifacts/{task_id}"
        ensure_ready_mock.assert_called_once()
        assert captured_backend["backend"] is backend

    def test_build_deep_agent_falls_back_to_state_backend_when_sandbox_validation_fails(self):
        """模板验证失败时，应自动回退到 StateBackend。"""
        agent = self._build_agent()
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda *_: None)
        route = self._route(
            need_sandbox=True,
            need_execute=True,
            summary="需要沙箱执行",
        )

        with patch("deepagents.create_deep_agent", return_value=MagicMock()), \
             patch.object(BaiduCfcSandboxBackend, "ensure_ready", side_effect=RuntimeError("template invalid")), \
             patch.dict(os.environ, {
                "E2B_API_KEY": "test-key",
                "E2B_DOMAIN": "sandbox.example.com",
                "SANDBOX_TEMPLATE_ALIAS": "lite-template",
             }, clear=False):
            _, backend, _, used_sandbox = agent._build_deep_agent(
                task_id=uuid4(),
                route_decision=route,
                timeline=timeline,
            )

        assert type(backend).__name__ == "StateBackend"
        assert used_sandbox is False

    def test_collect_artifacts_uploads_to_cos_and_publishes_events(self):
        """沙箱生成的附件应被下载、上传 COS，并发布 artifact 事件。"""
        agent = self._build_agent()
        published = []
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))

        backend = MagicMock()
        backend.execute.return_value = SimpleNamespace(
            exit_code=0,
            output="/workspace/artifacts/task-1/plan.txt\n",
        )
        backend.download_files.return_value = [
            SimpleNamespace(path="/workspace/artifacts/task-1/plan.txt", content=b"hello", error=None)
        ]

        mock_upload_file = SimpleNamespace(
            id=uuid4(),
            name="plan.txt",
            size=5,
            extension="txt",
            mime_type="text/plain",
            key="artifacts/plan.txt",
        )
        mock_cos_service = MagicMock()
        mock_cos_service.upload_bytes.return_value = mock_upload_file
        mock_cos_service.get_file_url.return_value = "https://cos.example.com/artifacts/plan.txt"
        mock_injector = MagicMock()
        mock_injector.get.return_value = mock_cos_service

        with patch("app.http.module.injector", mock_injector):
            artifacts = agent._collect_artifacts(
                backend=backend,
                artifact_root="/workspace/artifacts/task-1",
                timeline=timeline,
            )

        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "plan.txt"
        assert any(event.event == QueueEvent.DEEP_ARTIFACT_CREATED for event in published)

    def test_collect_artifacts_scans_home_user_fallback_root(self):
        """当 /workspace 不可写时，应能从 /home/user/artifacts 中发现产物。"""
        agent = self._build_agent()
        published = []
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))

        backend = MagicMock()
        backend.execute.return_value = SimpleNamespace(
            exit_code=0,
            output="/home/user/artifacts/task-1/plan.txt\n",
        )
        backend.download_files.return_value = [
            SimpleNamespace(path="/home/user/artifacts/task-1/plan.txt", content=b"hello", error=None)
        ]

        mock_upload_file = SimpleNamespace(
            id=uuid4(),
            name="plan.txt",
            size=5,
            extension="txt",
            mime_type="text/plain",
            key="artifacts/plan.txt",
        )
        mock_cos_service = MagicMock()
        mock_cos_service.upload_bytes.return_value = mock_upload_file
        mock_cos_service.get_file_url.return_value = "https://cos.example.com/artifacts/plan.txt"
        mock_injector = MagicMock()
        mock_injector.get.return_value = mock_cos_service

        with patch("app.http.module.injector", mock_injector):
            artifacts = agent._collect_artifacts(
                backend=backend,
                artifact_root="/workspace/artifacts/task-1",
                timeline=timeline,
            )

        assert len(artifacts) == 1
        assert artifacts[0]["path"] == "/home/user/artifacts/task-1/plan.txt"
        scan_command = backend.execute.call_args.args[0]
        assert "/workspace/artifacts/task-1" in scan_command
        assert "/home/user/artifacts/task-1" in scan_command
        assert any(event.event == QueueEvent.DEEP_ARTIFACT_CREATED for event in published)

    def test_collect_artifacts_enters_flask_app_context_when_needed(self):
        """产物持久化在线程内无 app context 时，应显式进入 runtime_flask_app.app_context()。"""
        runtime_flask_app = MagicMock()
        runtime_flask_app.app_context.return_value = nullcontext()
        agent = self._build_agent()
        agent.agent_config.runtime_flask_app = runtime_flask_app
        published = []
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))

        backend = MagicMock()
        backend.execute.return_value = SimpleNamespace(
            exit_code=0,
            output="/home/user/artifacts/task-1/plan.txt\n",
        )
        backend.download_files.return_value = [
            SimpleNamespace(path="/home/user/artifacts/task-1/plan.txt", content=b"hello", error=None)
        ]

        mock_upload_file = SimpleNamespace(
            id=uuid4(),
            name="plan.txt",
            size=5,
            extension="txt",
            mime_type="text/plain",
            key="artifacts/plan.txt",
        )
        mock_cos_service = MagicMock()
        mock_cos_service.upload_bytes.return_value = mock_upload_file
        mock_cos_service.get_file_url.return_value = "https://cos.example.com/artifacts/plan.txt"
        mock_injector = MagicMock()
        mock_injector.get.return_value = mock_cos_service

        with patch("app.http.module.injector", mock_injector), \
             patch("internal.core.agent.agents.deep_thinking_agent.has_app_context", return_value=False):
            artifacts = agent._collect_artifacts(
                backend=backend,
                artifact_root="/workspace/artifacts/task-1",
                timeline=timeline,
            )

        assert len(artifacts) == 1
        runtime_flask_app.app_context.assert_called_once()
        assert any(event.event == QueueEvent.DEEP_ARTIFACT_CREATED for event in published)

    def test_collect_artifacts_scans_top_level_artifact_root_when_task_folder_is_empty(self):
        """当产物误写到 /home/user/artifacts 顶层时，应通过 marker 兜底扫描发现文件。"""
        agent = self._build_agent()
        published = []
        timeline = DeepTimelineMiddleware(task_id=uuid4(), publisher=lambda tid, thought: published.append(thought))

        backend = MagicMock()
        backend._openagent_artifact_markers = [
            "/home/user/artifacts/.openagent_artifact_marker_task-1",
        ]
        backend.execute.side_effect = [
            SimpleNamespace(exit_code=0, output=""),
            SimpleNamespace(exit_code=0, output="/home/user/artifacts/shanghai_travel_outfits.svg\n"),
        ]
        backend.download_files.return_value = [
            SimpleNamespace(
                path="/home/user/artifacts/shanghai_travel_outfits.svg",
                content=b"<svg></svg>",
                error=None,
            )
        ]

        mock_upload_file = SimpleNamespace(
            id=uuid4(),
            name="shanghai_travel_outfits.svg",
            size=11,
            extension="svg",
            mime_type="image/svg+xml",
            key="artifacts/shanghai_travel_outfits.svg",
        )
        mock_cos_service = MagicMock()
        mock_cos_service.upload_bytes.return_value = mock_upload_file
        mock_cos_service.get_file_url.return_value = "https://cos.example.com/artifacts/shanghai_travel_outfits.svg"
        mock_injector = MagicMock()
        mock_injector.get.return_value = mock_cos_service

        with patch("app.http.module.injector", mock_injector):
            artifacts = agent._collect_artifacts(
                backend=backend,
                artifact_root="/workspace/artifacts/task-1",
                timeline=timeline,
            )

        assert len(artifacts) == 1
        assert artifacts[0]["path"] == "/home/user/artifacts/shanghai_travel_outfits.svg"
        assert backend.execute.call_count == 2
        fallback_scan_command = backend.execute.call_args_list[1].args[0]
        assert "/home/user/artifacts" in fallback_scan_command
        assert "-maxdepth 1" in fallback_scan_command
        assert ".openagent_artifact_marker_task-1" in fallback_scan_command
        assert any(event.event == QueueEvent.DEEP_ARTIFACT_CREATED for event in published)

    def test_sanitize_deep_answer_removes_fake_download_link_and_local_path(self):
        """应清理 deepagents 回答中的伪下载链接和沙箱本地路径。"""
        answer = """📄 可下载文件
📥 [点击下载：计划.txt]（需在沙箱中查看）
文件路径：/home/user/artifacts/task-1/计划.txt
这里是正文摘要。"""

        sanitized = DeepThinkingAgent._sanitize_deep_answer(
            answer,
            artifacts=[{"name": "计划.txt", "url": "https://cos.example.com/plan.txt"}],
        )

        assert "点击下载" not in sanitized
        assert "/home/user/artifacts/" not in sanitized
        assert "这里是正文摘要" in sanitized
        assert "generated_artifacts" not in sanitized

    def test_sanitize_deep_answer_removes_sandbox_uri_links(self):
        """应清理 sandbox:/mnt/data 伪下载链接，避免前端出现不可用链接。"""
        answer = """下载地址：sandbox:/mnt/data/shanghai_travel_outfits.svg
请点击下载。"""

        sanitized = DeepThinkingAgent._sanitize_deep_answer(answer, artifacts=[])

        assert "sandbox:/mnt/data/" not in sanitized


# ============================================================
#  Integration Tests（需要真实百度 CFC 沙箱）
# ============================================================

@pytest.mark.integration
class TestBaiduCfcSandboxIntegration:
    """集成测试：需要真实的百度 CFC 沙箱环境。

    运行前确保 .env 中配置了：
        E2B_API_KEY=bce-v3/ALTAK-...
        E2B_DOMAIN=sandbox-execute.bj.baidubce.com
    """

    @pytest.fixture(scope="class")
    def sandbox(self):
        """创建真实沙箱实例，测试完成后关闭。"""
        api_key = os.environ.get("E2B_API_KEY", "")
        domain  = os.environ.get("E2B_DOMAIN",  "")
        if not api_key or not domain:
            pytest.skip("E2B_API_KEY 或 E2B_DOMAIN 未配置，跳过集成测试")

        backend = BaiduCfcSandboxBackend(api_key=api_key, domain=domain)
        yield backend
        backend.close()

    def test_execute_python_code(self, sandbox):
        """真实沙箱：执行 Python 代码并验证输出。"""
        result = sandbox.execute("python3 -c 'print(1 + 2 + 3)'")
        assert result.exit_code == 0
        assert "6" in result.output

    def test_execute_shell_command(self, sandbox):
        """真实沙箱：执行 Shell 命令。"""
        result = sandbox.execute("echo 'hello from baidu cfc sandbox'")
        assert result.exit_code == 0
        assert "hello from baidu cfc sandbox" in result.output

    def test_execute_multiline_python(self, sandbox):
        """真实沙箱：执行多行 Python 脚本。"""
        script = "python3 -c \"\nimport math\nresult = math.sqrt(144)\nprint(f'sqrt(144)={result}')\n\""
        result = sandbox.execute(script)
        assert result.exit_code == 0
        assert "12.0" in result.output

    def test_file_upload_and_download(self, sandbox):
        """真实沙箱：上传文件后能下载回来内容一致。"""
        content = b"# hello from unit test\nprint('hi')\n"
        path    = "/tmp/test_upload.py"

        upload_resp = sandbox.upload_files([(path, content)])
        assert upload_resp[0].error is None

        download_resp = sandbox.download_files([path])
        assert download_resp[0].content == content

    def test_execute_uploaded_file(self, sandbox):
        """真实沙箱：上传 Python 文件后能执行。"""
        code = b"result = 2 ** 10\nprint(f'2^10={result}')\n"
        path = "/tmp/test_exec.py"

        sandbox.upload_files([(path, code)])
        result = sandbox.execute(f"python3 {path}")

        assert result.exit_code == 0
        assert "1024" in result.output

    def test_sandbox_id_is_string(self, sandbox):
        """真实沙箱：sandbox_id 应为非空字符串。"""
        assert isinstance(sandbox.id, str)
        assert len(sandbox.id) > 0
