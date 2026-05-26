import runpy
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import app.http.module as http_module


def test_app_module_should_call_run_when_executed_as_main(monkeypatch):
    import internal.server as server_module

    run_calls = []

    class _FakeHttp:
        def __init__(self, *_args, **_kwargs):
            conf = _kwargs.get("conf")
            self.config = dict(vars(conf)) if conf is not None else {}
            self.extensions = {"celery": "celery-app"}

        @contextmanager
        def app_context(self):
            yield self

        def run(self, **kwargs):
            run_calls.append(kwargs)

    monkeypatch.setattr(server_module, "Http", _FakeHttp)
    monkeypatch.delitem(sys.modules, "app.http.app", raising=False)

    module_globals = runpy.run_module("app.http.app", run_name="__main__")

    assert run_calls == [{"debug": True, "port": 5001}]
    assert module_globals["celery"] == "celery-app"


def test_app_module_should_prewarm_assistant_mcp_snapshots_when_bindings_exist(monkeypatch):
    import internal.server as server_module

    run_calls = []
    prewarm_calls = []

    class _FakeAppService:
        def prewarm_assistant_mcp_tool_snapshots(self):
            prewarm_calls.append(True)
            return [{"binding_identity": "global-mcp", "tool_definitions": [{"name": "weather"}]}]

    class _FakeInjector:
        def __init__(self):
            self.requested_classes = []

        def get(self, cls):
            self.requested_classes.append(cls)
            if cls.__name__ == "AppService":
                return _FakeAppService()
            return SimpleNamespace()

    class _FakeHttp:
        def __init__(self, *_args, **_kwargs):
            conf = _kwargs.get("conf")
            self.config = dict(vars(conf)) if conf is not None else {}
            self.extensions = {"celery": "celery-app"}

        @contextmanager
        def app_context(self):
            yield self

        def run(self, **kwargs):
            run_calls.append(kwargs)

    monkeypatch.setenv(
        "ASSISTANT_MCP_BINDINGS",
        '[{"name":"global-mcp","transport":"streamable_http","url":"https://mcp.example.com","enabled":true}]',
    )
    monkeypatch.setattr(server_module, "Http", _FakeHttp)
    monkeypatch.setattr(http_module, "injector", _FakeInjector())
    monkeypatch.delitem(sys.modules, "app.http.app", raising=False)

    module_globals = runpy.run_module("app.http.app", run_name="__main__")

    assert run_calls == [{"debug": True, "port": 5001}]
    assert prewarm_calls == [True]
    assert module_globals["celery"] == "celery-app"
