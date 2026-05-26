from __future__ import annotations

import json

import pytest
import requests

from internal.core.tools.mcp_tools.providers.mcp_tool_factory import McpToolFactory


class _FakeResponse:
    def __init__(self, payload=None, *, status_code: int = 200, headers: dict | None = None, text: str | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self.reason = "OK" if status_code < 400 else "Bad Request"
        if text is not None:
            self.text = text
        elif payload is None:
            self.text = ""
        else:
            self.text = json.dumps(payload, ensure_ascii=False)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} response")


class _FakeSession:
    def __init__(self, handler):
        self.handler = handler
        self.trust_env = False

    def post(self, url, json, headers, timeout):
        return self.handler(url, json, headers, timeout)


@pytest.fixture(autouse=True)
def _clear_mcp_tool_factory_caches():
    McpToolFactory._get_session.cache_clear()
    McpToolFactory._STREAMABLE_HTTP_SESSION_CACHE.clear()
    yield
    McpToolFactory._get_session.cache_clear()
    McpToolFactory._STREAMABLE_HTTP_SESSION_CACHE.clear()


def test_mcp_tool_factory_should_respect_proxy_env(monkeypatch):
    fake_session = _FakeSession(lambda *_args, **_kwargs: _FakeResponse())
    monkeypatch.setattr(
        "internal.core.tools.mcp_tools.providers.mcp_tool_factory.requests.Session",
        lambda: fake_session,
    )

    factory = McpToolFactory()
    session = factory._get_session()

    assert session is fake_session
    assert session.trust_env is True


def test_mcp_tool_factory_should_initialize_streamable_http_session_and_call_selected_tool(monkeypatch):
    calls = []

    def _fake_post(url, json, headers, timeout):
        calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )

        method = json["method"]
        if method == "initialize":
            assert "Mcp-Session-Id" not in headers
            assert headers["Accept"] == "application/json, text/event-stream"
            assert json["params"]["protocolVersion"] == "2024-11-05"
            return _FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": json["id"],
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "experimental": {},
                            "resources": {
                                "subscribe": False,
                                "listChanged": False,
                            },
                            "tools": {
                                "listChanged": False,
                            },
                        },
                        "serverInfo": {
                            "name": "12306-mcp",
                            "version": "1.9.4",
                        },
                    },
                },
                headers={"Mcp-Session-Id": "session-1"},
            )

        if method == "notifications/initialized":
            assert "id" not in json
            assert headers["Mcp-Session-Id"] == "session-1"
            assert json["params"] == {}
            return _FakeResponse(status_code=202)

        if method == "tools/list":
            assert "params" not in json
            assert headers["Mcp-Session-Id"] == "session-1"
            return _FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": json["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "weather",
                                "description": "天气查询",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "city": {
                                            "type": "string",
                                            "description": "城市",
                                        },
                                        "days": {
                                            "type": "integer",
                                            "default": 1,
                                        },
                                    },
                                    "required": ["city"],
                                },
                            },
                            {
                                "name": "hidden_tool",
                                "description": "should be filtered",
                            },
                        ]
                    },
                }
            )

        if method == "tools/call":
            assert headers["Mcp-Session-Id"] == "session-1"
            assert json["params"]["name"] == "weather"
            assert json["params"]["arguments"] == {"city": "杭州", "days": 1}
            return _FakeResponse(
                {
                    "jsonrpc": "2.0",
                    "id": json["id"],
                    "result": {
                        "content": [{"type": "text", "text": "杭州今天晴"}],
                    },
                }
            )

        raise AssertionError(f"unexpected method: {method}")

    fake_session = _FakeSession(_fake_post)
    monkeypatch.setattr(
        "internal.core.tools.mcp_tools.providers.mcp_tool_factory.requests.Session",
        lambda: fake_session,
    )

    factory = McpToolFactory()
    tools = factory.get_tools(
        [
            {
                "name": "weather_gateway",
                "description": "ModelScope weather",
                "transport": "streamable_http",
                "url": "https://mcp.example.com",
                "enabled": True,
                "headers": [
                    {"key": "Authorization", "value": "Bearer token"},
                ],
                "tool_names": ["weather"],
                "timeout_seconds": 15,
                "args": [],
                "env": {},
            }
        ]
    )

    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "mcp__weather_gateway__weather"
    assert factory._get_session().trust_env is True

    result = tool.invoke({"city": "杭州"})
    result_text = result.content if hasattr(result, "content") else result

    assert result_text == "杭州今天晴"
    assert [call["json"]["method"] for call in calls] == ["initialize", "notifications/initialized", "tools/list", "tools/call"]
    assert calls[0]["timeout"] == 15
    assert calls[0]["headers"]["Authorization"] == "Bearer token"
    assert calls[2]["headers"]["Mcp-Session-Id"] == "session-1"
    assert calls[3]["headers"]["Mcp-Session-Id"] == "session-1"


def test_mcp_tool_factory_should_compile_complex_json_schema_and_keep_metadata(monkeypatch):
    complex_input_schema = {
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["fast", "safe"],
                        "description": "运行模式",
                    },
                    "payload": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "ID",
                                },
                                "count": {
                                    "type": "integer",
                                    "default": 1,
                                },
                            },
                            "required": ["id"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["mode"],
                "additionalProperties": True,
            },
            "variant": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "integer"},
                ]
            },
            "when": {
                "type": "string",
                "format": "date",
                "description": "日期",
            },
        },
        "required": ["request"],
    }

    factory = McpToolFactory()
    captured_calls = []

    def _fake_call_remote_tool(binding, tool_name, arguments):
        captured_calls.append(
            {
                "binding": binding,
                "tool_name": tool_name,
                "arguments": arguments,
            }
        )
        assert tool_name == "complex_tool"
        assert arguments["request"]["mode"] == "fast"
        assert arguments["request"]["extra_flag"] == "keep"
        assert arguments["request"]["payload"][0]["count"] == 2
        assert arguments["variant"] == 3
        assert arguments["when"] == "2026-05-20"
        return "ok"

    monkeypatch.setattr(factory, "_call_remote_tool", _fake_call_remote_tool)

    tool = factory._build_langchain_tool(
        {
            "name": "complex_gateway",
            "description": "Complex MCP",
            "transport": "streamable_http",
            "url": "https://mcp.example.com",
            "enabled": True,
            "headers": [],
            "tool_names": ["complex_tool"],
            "timeout_seconds": 20,
            "args": [],
            "env": {},
        },
        {
            "name": "complex_tool",
            "title": "复杂工具",
            "description": "复杂输入结构的工具",
            "inputSchema": complex_input_schema,
            "outputSchema": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                },
            },
            "annotations": {
                "readOnlyHint": True,
                "idempotentHint": True,
            },
        },
    )

    assert tool.name == "mcp__complex_gateway__complex_tool"
    assert "行为: 只读，幂等" in tool.description
    assert "输入:" in tool.description
    assert "request:对象参数" in tool.description
    assert "variant:string 或 integer" in tool.description
    assert tool.metadata["input_schema"] == complex_input_schema
    assert tool.metadata["output_schema"]["type"] == "object"
    assert tool.metadata["annotations"]["readOnlyHint"] is True
    assert tool.metadata["schema_summary"].startswith("对象参数:")
    assert tool.metadata["input_schema_summary"] == tool.metadata["schema_summary"]
    assert tool.metadata["output_schema_summary"].startswith("对象参数:")
    assert tool.metadata["annotations_summary"] == "只读，幂等"

    result = tool.invoke(
        {
            "request": {
                "mode": "fast",
                "extra_flag": "keep",
                "payload": [
                    {
                        "id": "item-1",
                        "count": 2,
                    }
                ],
            },
            "variant": 3,
            "when": "2026-05-20",
        }
    )
    result_text = result.content if hasattr(result, "content") else result

    assert result_text == "ok"
    assert len(captured_calls) == 1
    assert captured_calls[0]["arguments"]["request"]["extra_flag"] == "keep"


def test_mcp_tool_factory_should_prepare_and_refresh_binding_snapshots(monkeypatch):
    factory = McpToolFactory()
    binding = {
        "name": "weather_gateway",
        "description": "weather",
        "transport": "streamable_http",
        "url": "https://mcp.example.com",
        "enabled": True,
        "headers": [],
        "tool_names": ["weather"],
        "timeout_seconds": 15,
        "args": [],
        "env": {},
    }

    prepared = factory.prepare_binding_snapshots([binding])
    assert len(prepared) == 1
    assert prepared[0]["binding_identity"] == factory.build_binding_identity(binding)
    assert prepared[0]["status"] == "warming"
    assert prepared[0]["retryable"] is True

    tool_definitions = [
        {
            "name": "weather",
            "title": "天气查询",
            "description": "查询天气",
            "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        }
    ]
    monkeypatch.setattr(factory, "_list_remote_tools", lambda _binding: tool_definitions)

    refreshed = factory.refresh_binding_snapshots([binding], prepared)

    assert len(refreshed) == 1
    assert refreshed[0]["status"] == "ready"
    assert refreshed[0]["retryable"] is False
    assert refreshed[0]["tool_names"] == ["weather"]
    assert refreshed[0]["tool_count"] == 1
    assert refreshed[0]["retry_count"] == 0
    assert refreshed[0]["binding_identity"] == factory.build_binding_identity(binding)


def test_mcp_tool_factory_should_mark_permanent_refresh_failures_as_non_retryable(monkeypatch):
    factory = McpToolFactory()
    binding = {
        "name": "weather_gateway",
        "description": "weather",
        "transport": "streamable_http",
        "url": "https://mcp.example.com",
        "enabled": True,
        "headers": [],
        "tool_names": ["weather"],
        "timeout_seconds": 15,
        "args": [],
        "env": {},
    }

    prepared = factory.prepare_binding_snapshots([binding])
    monkeypatch.setattr(factory, "_list_remote_tools", lambda _binding: (_ for _ in ()).throw(RuntimeError("record not found")))

    refreshed = factory.refresh_binding_snapshots([binding], prepared)

    assert len(refreshed) == 1
    assert refreshed[0]["status"] == "failed"
    assert refreshed[0]["retryable"] is False
    assert refreshed[0]["last_error"] == "record not found"
    assert refreshed[0]["retry_count"] == 1


def test_mcp_tool_factory_should_keep_cached_tools_when_refresh_fails_permanently(monkeypatch):
    factory = McpToolFactory()
    binding = {
        "name": "weather_gateway",
        "description": "weather",
        "transport": "streamable_http",
        "url": "https://mcp.example.com",
        "enabled": True,
        "headers": [],
        "tool_names": ["weather"],
        "timeout_seconds": 15,
        "args": [],
        "env": {},
    }

    existing_snapshot = factory.prepare_binding_snapshots([binding])[0]
    existing_snapshot.update(
        {
            "status": "stale",
            "tool_definitions": [
                {
                    "name": "weather",
                    "title": "天气查询",
                    "description": "查询天气",
                    "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
                }
            ],
            "tool_names": ["weather"],
            "tool_count": 1,
            "schema_hash": "schema-hash",
            "last_success_at": 1710000000,
        }
    )
    monkeypatch.setattr(factory, "_list_remote_tools", lambda _binding: (_ for _ in ()).throw(RuntimeError("record not found")))

    refreshed = factory.refresh_binding_snapshots([binding], [existing_snapshot])

    assert len(refreshed) == 1
    assert refreshed[0]["status"] == "stale"
    assert refreshed[0]["retryable"] is False
    assert refreshed[0]["tool_count"] == 1
    assert refreshed[0]["tool_names"] == ["weather"]


def test_mcp_tool_factory_should_build_tools_from_snapshots_without_live_discovery(monkeypatch):
    factory = McpToolFactory()
    binding = {
        "name": "weather_gateway",
        "description": "weather",
        "transport": "streamable_http",
        "url": "https://mcp.example.com",
        "enabled": True,
        "headers": [],
        "tool_names": ["weather"],
        "timeout_seconds": 15,
        "args": [],
        "env": {},
    }
    binding_identity = factory.build_binding_identity(binding)
    snapshots = [
        {
            "binding_identity": binding_identity,
            "binding_hash": "hash-1",
            "binding": binding,
            "status": "ready",
            "tool_definitions": [
                {
                    "name": "weather",
                    "title": "天气查询",
                    "description": "查询天气",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                }
            ],
            "tool_names": ["weather"],
            "tool_count": 1,
            "schema_hash": "schema-hash-1",
            "last_attempt_at": 1,
            "last_success_at": 1,
            "last_error": "",
            "retry_count": 0,
            "retryable": False,
        }
    ]

    def _raise_if_called(_binding):
        raise AssertionError("live discovery should not be called when snapshots are provided")

    monkeypatch.setattr(factory, "_list_remote_tools", _raise_if_called)

    tools = factory.get_tools([binding], snapshots)

    assert len(tools) == 1
    assert tools[0].name == "mcp__weather_gateway__weather"
    assert tools[0].metadata["binding_name"] == "weather_gateway"
