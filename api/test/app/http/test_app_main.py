import runpy
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import app.http.module as http_module


class _FakeAppService:
    def __init__(self, prewarm_calls):
        self._prewarm_calls = prewarm_calls

    def prewarm_assistant_mcp_tool_snapshots(self):
        self._prewarm_calls.append(True)
        return [{"binding_identity": "global-mcp", "tool_definitions": [{"name": "weather"}]}]


class _FakeSkillService:
    def __init__(self, sync_calls):
        self._sync_calls = sync_calls

    def ensure_local_catalog_synced(self, force=False):
        self._sync_calls.append(force)
        return 51


class _FakeInjector:
    def __init__(self, *, prewarm_calls=None, sync_calls=None):
        self.requested_classes = []
        self._prewarm_calls = prewarm_calls if prewarm_calls is not None else []
        self._sync_calls = sync_calls if sync_calls is not None else []
        self._app_service = _FakeAppService(self._prewarm_calls)
        self._skill_service = _FakeSkillService(self._sync_calls)

    def get(self, cls):
        self.requested_classes.append(cls)
        if cls.__name__ == "AppService":
            return self._app_service
        if cls.__name__ == "SkillService":
            return self._skill_service
        return SimpleNamespace()


def _make_fake_http(run_calls):
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

    return _FakeHttp


def test_app_module_should_call_run_when_executed_as_main(monkeypatch):
    import internal.server as server_module

    run_calls = []

    monkeypatch.setenv("MODE", "celery")
    monkeypatch.setenv("SKILL_CATALOG_SYNC_ENABLED", "false")
    monkeypatch.setenv("ASSISTANT_MCP_BINDINGS", "[]")
    monkeypatch.setattr(server_module, "Http", _make_fake_http(run_calls))
    monkeypatch.setattr(http_module, "injector", _FakeInjector())
    monkeypatch.delitem(sys.modules, "app.http.app", raising=False)

    module_globals = runpy.run_module("app.http.app", run_name="__main__")

    assert run_calls == [{"debug": True, "port": 5001}]
    assert module_globals["celery"] == "celery-app"


def test_app_module_should_prewarm_assistant_mcp_snapshots_when_bindings_exist(monkeypatch):
    import internal.server as server_module

    run_calls = []
    prewarm_calls = []
    sync_calls = []

    monkeypatch.setenv("MODE", "api")
    monkeypatch.setenv("SKILL_CATALOG_SYNC_ENABLED", "true")
    monkeypatch.setenv(
        "ASSISTANT_MCP_BINDINGS",
        '[{"name":"global-mcp","transport":"streamable_http","url":"https://mcp.example.com","enabled":true}]',
    )
    monkeypatch.setattr(server_module, "Http", _make_fake_http(run_calls))
    monkeypatch.setattr(http_module, "injector", _FakeInjector(prewarm_calls=prewarm_calls, sync_calls=sync_calls))
    monkeypatch.delitem(sys.modules, "app.http.app", raising=False)

    module_globals = runpy.run_module("app.http.app", run_name="__main__")

    assert run_calls == [{"debug": True, "port": 5001}]
    assert prewarm_calls == [True]
    assert sync_calls == [False]
    assert module_globals["celery"] == "celery-app"
