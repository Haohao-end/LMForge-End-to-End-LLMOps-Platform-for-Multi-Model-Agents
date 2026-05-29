from __future__ import annotations

import logging
import json as json_module

from internal.core.skills.skill_executor import SkillSandboxExecutor, SkillScfClient


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.status_code = 200
        self.text = "ok"

    def json(self):
        return self._payload


def test_skill_scf_client_should_post_sync_and_execute_payloads(monkeypatch, caplog):
    calls = []

    def _fake_post(url, json=None, timeout=None, **_kwargs):
        calls.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return _FakeResponse({"statusCode": 200, "body": json_module.dumps({"result": {"status": "ok"}})})

    monkeypatch.setattr("internal.core.skills.skill_executor.requests.post", _fake_post)

    client = SkillScfClient(endpoint="https://scf.example.com/skills", timeout_seconds=12)

    with caplog.at_level(logging.INFO):
        sync_result = client.sync_package({"skill": {"source_key": "code_workbench"}, "version": {"version": 1}})
        exec_result = client.execute_skill(
            {
                "skill_id": "skill-1",
                "source_key": "code_workbench",
                "tool_name": "analyze_request",
                "entrypoint": "analyze_request",
                "input": {"request": "hello"},
                "bundle": {
                    "skill.py": "def analyze_request(params):\n    return {'echo': params.get('request')}\n",
                },
            }
        )

    assert sync_result == {"status": "ok"}
    assert exec_result == {"status": "ok"}
    assert calls[0]["url"] == "https://scf.example.com/skills"
    assert calls[0]["timeout"] == 12
    assert calls[0]["json"]["action"] == "sync_package"
    assert calls[0]["json"]["func_name"] == "sync_package"
    assert calls[0]["json"]["args"][0]["source_key"] == "code_workbench"
    assert "def sync_package" in calls[0]["json"]["code"]
    assert calls[1]["json"]["action"] == "execute_skill"
    assert calls[1]["json"]["skill_id"] == "skill-1"
    assert calls[1]["json"]["func_name"] == "analyze_request"
    assert calls[1]["json"]["args"] == [{"request": "hello"}]
    assert calls[1]["json"]["kwargs"] == {}
    assert "def analyze_request" in calls[1]["json"]["code"]
    assert caplog.text.count("技能工具 SCF success") == 2


def test_skill_sandbox_executor_should_execute_locally_when_unconfigured(monkeypatch):
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    monkeypatch.delenv("E2B_DOMAIN", raising=False)

    executor = SkillSandboxExecutor()
    result = executor.execute_skill(
        {
            "bundle": {
                "skill.py": (
                    "from __future__ import annotations\n\n"
                    "def run(params):\n"
                    "    return {'echo': params.get('value')}\n"
                )
            },
            "entrypoint": "run",
            "input": {"value": "hello"},
        }
    )

    assert result == {"echo": "hello"}


def test_skill_sandbox_executor_should_log_local_success(monkeypatch, caplog):
    monkeypatch.delenv("E2B_API_KEY", raising=False)
    monkeypatch.delenv("E2B_DOMAIN", raising=False)

    executor = SkillSandboxExecutor()
    with caplog.at_level(logging.INFO):
        result = executor.execute_skill(
            {
                "bundle": {
                    "skill.py": (
                        "from __future__ import annotations\n\n"
                        "def run(params):\n"
                        "    return {'echo': params.get('value')}\n"
                    )
                },
                "entrypoint": "run",
                "input": {"value": "hello"},
            }
        )

    assert result == {"echo": "hello"}
    assert "技能工具 sandbox local success" in caplog.text


def test_skill_sandbox_executor_should_log_remote_success(monkeypatch, caplog):
    monkeypatch.setenv("E2B_API_KEY", "test-key")
    monkeypatch.setenv("E2B_DOMAIN", "test-domain")

    class _FakeUploadResponse:
        def __init__(self, path: str, error: str | None = None):
            self.path = path
            self.error = error

    class _FakeExecuteResponse:
        def __init__(self, output: str):
            self.output = output

    class _FakeBackend:
        def __init__(self, *_, **__):
            self.id = "sandbox-test-1"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, command: str, *, timeout=None):
            if "_skill_runner.py" in command:
                return _FakeExecuteResponse(
                    "__SKILL_RESULT__"
                    + json_module.dumps(
                        {
                            "ok": True,
                            "result": {"echo": "hello"},
                            "stdout": "",
                            "stderr": "",
                        }
                    )
                )
            return _FakeExecuteResponse("")

        def upload_files(self, files):
            return [_FakeUploadResponse(path) for path, _content in files]

    monkeypatch.setattr("internal.core.skills.skill_executor.BaiduCfcSandboxBackend", _FakeBackend)

    executor = SkillSandboxExecutor()
    with caplog.at_level(logging.INFO):
        result = executor.execute_skill(
            {
                "bundle": {
                    "skill.py": (
                        "from __future__ import annotations\n\n"
                        "def run(params):\n"
                        "    return {'echo': params.get('value')}\n"
                    )
                },
                "entrypoint": "run",
                "input": {"value": "hello"},
            }
        )

    assert result == {"echo": "hello"}
    assert "技能工具 sandbox remote success" in caplog.text
