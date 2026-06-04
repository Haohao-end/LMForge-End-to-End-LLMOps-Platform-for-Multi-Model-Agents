from __future__ import annotations

from internal.core.agent.entities.sandbox_policy_entity import SandboxPolicy


def test_sandbox_policy_should_expose_default_profile():
    assert SandboxPolicy.default_sandbox_profile == "lite"
    assert SandboxPolicy.default_sandbox_template_alias == "llmops-code-interpreter-lite"
    assert SandboxPolicy.default_sandbox_fallback_template_alias == "code-interpreter-v1"
    assert SandboxPolicy.default_sandbox_timeout_seconds == 1800
    assert SandboxPolicy.default_execute_timeout_seconds == 600
    assert SandboxPolicy.default_artifact_base_dirs == ("/workspace", "/home/user", "/tmp", "/mnt/data")
    assert SandboxPolicy.document_build_base_dir == "/tmp/openagent_doc_build"
    assert SandboxPolicy.code_interpreter_data_dir == "/mnt/data"
    assert SandboxPolicy.artifact_marker_prefix == ".openagent_artifact_marker_"


def test_sandbox_policy_should_build_default_artifact_root():
    assert SandboxPolicy.build_default_artifact_root("task-123") == "/workspace/artifacts/task-123"


def test_sandbox_policy_should_sanitize_sandbox_download_links():
    text = (
        "下载地址：[SpaceX_IPO_Prospectus_Draft.txt](sandbox:/mnt/data/SpaceX_IPO_Prospectus_Draft.txt)\n"
        "本地路径：/workspace/output/result.txt"
    )

    sanitized = SandboxPolicy.sanitize_sandbox_artifact_text(text)

    assert "sandbox:/mnt/data/" not in sanitized
    assert "/workspace/" not in sanitized
    assert "SpaceX_IPO_Prospectus_Draft.txt" in sanitized
    assert "result.txt" in sanitized
