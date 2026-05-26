from __future__ import annotations

import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from flask import Flask

from internal.exception import ValidateErrorException
from internal.service.skill_service import SkillService


@contextmanager
def _null_context():
    yield


def _build_service() -> SkillService:
    class _Query:
        def limit(self, *_args, **_kwargs):
            return self

        def first(self):
            return None

        def filter(self, *_args, **_kwargs):
            return self

        def one_or_none(self):
            return None

        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    db = SimpleNamespace(
        session=SimpleNamespace(query=lambda *_args, **_kwargs: _Query()),
        auto_commit=_null_context,
    )
    service = SkillService(db=db, catalog_manager=SimpleNamespace(list_packages=lambda: []), scf_client=SimpleNamespace())
    return service


def _build_skill_package(package_id):
    return SimpleNamespace(
        id=package_id,
        source_key="code_workbench",
        source_path="/tmp/code_workbench",
        name="代码工坊",
        label="代码工坊",
        icon="/skills/code_workbench/icon.svg",
        description="面向代码分析和文件输出的技能包",
        category="开发",
        tags=["代码"],
        capabilities={"code": True},
        executor_type="scf",
        enabled=True,
        current_version=2,
        latest_source_version=2,
        source_checksum="checksum",
        sync_status="synced",
        sync_error="",
        published_at=None,
        created_at=0,
        updated_at=0,
        versions=[],
    )


def _build_version_record(package_id):
    return SimpleNamespace(
        id=uuid4(),
        skill_package_id=package_id,
        version=2,
        manifest={
            "description": "代码分析版本",
            "tools": [
                {
                    "name": "analyze_request",
                    "label": "需求分析",
                    "description": "根据需求生成分析",
                    "entrypoint": "analyze_request",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "用户需求",
                            }
                        },
                        "required": ["request"],
                    },
                }
            ],
        },
        bundle={"manifest.yaml": "source"},
        checksum="checksum",
        sync_status="synced",
        sync_error="",
        created_at=0,
        updated_at=0,
    )


def test_process_and_validate_skill_bindings_should_keep_only_skill_id(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    display_skills, validate_skills = service.process_and_validate_skill_bindings(
        [
            {"skill_id": str(package_id), "version": "not-a-number", "enabled": True},
            {"skill_id": str(uuid4()), "version": 1, "enabled": True},
        ]
    )

    assert validate_skills == [
        {
            "skill_id": str(package_id),
        }
    ]
    assert len(display_skills) == 1
    assert display_skills[0]["skill_id"] == str(package_id)
    assert display_skills[0]["tool_count"] == 1
    assert "version" not in display_skills[0]
    assert "enabled" not in display_skills[0]


def test_get_langchain_tools_by_skill_bindings_should_expand_skill_tools_without_version(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)
    build_calls = []

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    class _ToolFactory:
        def build_tools(self, package_payload, tool_definitions, runtime_context):
            build_calls.append(
                {
                    "package_payload": package_payload,
                    "tool_definitions": tool_definitions,
                    "runtime_context": runtime_context,
                }
            )
            return [f"{package_payload['source_key']}::{tool_definitions[0]['name']}"]

    service.tool_factory = _ToolFactory()

    tools = service.get_langchain_tools_by_skill_bindings(
        [
            {"skill_id": str(package_id)},
        ],
        runtime_context={"app_id": "app-1"},
    )

    assert tools == ["code_workbench::analyze_request"]
    assert len(build_calls) == 1
    assert build_calls[0]["package_payload"]["skill_id"] == str(package_id)
    assert "version" not in build_calls[0]["package_payload"]
    assert build_calls[0]["runtime_context"]["app_id"] == "app-1"


def test_skill_runtime_cache_should_reuse_package_payload_within_request(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)
    lookup_calls = {"package": 0, "version": 0}
    build_calls = []

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)

    def _get_skill_package_record(skill_id):
        lookup_calls["package"] += 1
        return package if skill_id == package_id else None

    def _get_skill_package_version_record(skill_package_id, version):
        lookup_calls["version"] += 1
        return version_record if skill_package_id == package_id and version == 2 else None

    monkeypatch.setattr(service, "_get_skill_package_record", _get_skill_package_record)
    monkeypatch.setattr(service, "_get_skill_package_version_record", _get_skill_package_version_record)

    class _ToolFactory:
        def build_tools(self, package_payload, tool_definitions, runtime_context):
            build_calls.append((package_payload, tool_definitions, runtime_context))
            return [f"{package_payload['source_key']}::{tool_definitions[0]['name']}"]

    service.tool_factory = _ToolFactory()

    with Flask(__name__).app_context():
        display_skills, validate_skills = service.process_and_validate_skill_bindings(
            [{"skill_id": str(package_id)}]
        )
        tools = service.get_langchain_tools_by_skill_bindings(
            [{"skill_id": str(package_id)}],
            runtime_context={"app_id": "app-1"},
        )

    assert validate_skills == [{"skill_id": str(package_id)}]
    assert display_skills[0]["skill_id"] == str(package_id)
    assert tools == ["code_workbench::analyze_request"]
    assert lookup_calls["package"] == 1
    assert lookup_calls["version"] == 1
    assert len(build_calls) == 1


def test_get_langchain_tools_by_skill_bindings_should_skip_prompt_only_skill_tools(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    package.executor_type = "prompt"
    version_record = _build_version_record(package_id)
    version_record.manifest["tools"] = [
        {
            "name": "stale_tool",
            "label": "过期工具",
            "description": "不应暴露",
            "entrypoint": "stale_tool",
            "input_schema": {"type": "object"},
        }
    ]
    build_calls = []

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    class _ToolFactory:
        def build_tools(self, package_payload, tool_definitions, runtime_context):
            build_calls.append(
                {
                    "package_payload": package_payload,
                    "tool_definitions": tool_definitions,
                    "runtime_context": runtime_context,
                }
            )
            return [f"{package_payload['source_key']}::{tool_definitions[0]['name']}"]

    service.tool_factory = _ToolFactory()

    tools = service.get_langchain_tools_by_skill_bindings(
        [{"skill_id": str(package_id)}],
        runtime_context={"app_id": "app-1"},
    )

    assert tools == []
    assert build_calls == []


def test_get_langchain_prompt_loaders_by_skill_bindings_should_expand_prompt_only_skill(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    package.executor_type = "prompt"
    version_record = _build_version_record(package_id)
    version_record.bundle = {
        "manifest.yaml": "source",
        "skill.md": "# 前端技能\n\n用于视觉层次、留白和布局质量要求高的前端页面设计与实现任务。",
    }

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    tools = service.get_langchain_prompt_loaders_by_skill_bindings(
        [{"skill_id": str(package_id)}],
        runtime_context={"app_id": "app-1"},
    )

    assert len(tools) == 1
    assert tools[0].name == "skill_prompt__code_workbench"
    assert "prompt-only 技能" in tools[0].description

    result = tools[0].invoke({})
    assert result["skill_id"] == str(package_id)
    assert result["source_key"] == "code_workbench"
    assert result["label"] == "代码工坊"
    assert result["prompt"] == "# 前端技能\n\n用于视觉层次、留白和布局质量要求高的前端页面设计与实现任务。"
    assert result["readme"] == result["prompt"]
    assert result["prompt_length"] == len(result["prompt"])
    assert result["ephemeral"] is True
    assert result["lease_id"]


def test_get_langchain_prompt_loaders_by_skill_bindings_should_skip_scf_skills(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: None)
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    tools = service.get_langchain_prompt_loaders_by_skill_bindings(
        [{"skill_id": str(package_id)}],
        runtime_context={"app_id": "app-1"},
    )

    assert tools == []


def test_get_skill_packages_with_page_should_search_tags(monkeypatch):
    service = _build_service()
    package = _build_skill_package(uuid4())
    captured = {}

    class _Query:
        def __init__(self):
            self.filters = []

        def filter(self, *args):
            self.filters.extend(args)
            return self

        def order_by(self, *_args):
            return self

    class _Session:
        def query(self, model):
            captured["model"] = model
            return _Query()

    class _DB:
        def __init__(self):
            self.session = _Session()

    class _Paginator:
        def __init__(self, db, req):
            self.total_record = 1
            self.total_page = 1

        def paginate(self, query):
            captured["query"] = query
            return [package]

    monkeypatch.setattr("internal.service.skill_service.Paginator", _Paginator)
    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(service, "_build_skill_package_summary", lambda pkg: {"id": str(pkg.id), "label": pkg.label})
    service.db = _DB()

    skills, paginator = service.get_skill_packages_with_page(
        SimpleNamespace(
            search_word=SimpleNamespace(data="github"),
            category=SimpleNamespace(data=""),
        )
    )

    assert skills == [{"id": str(package.id), "label": package.label}]
    assert paginator.total_record == 1
    assert paginator.total_page == 1
    assert captured["model"].__name__ == "SkillPackage"
    assert len(captured["query"].filters) == 1
    assert "tags" in str(captured["query"].filters[0]).lower()


def test_get_skill_categories_should_return_empty_when_tables_missing(monkeypatch):
    service = _build_service()

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: False)

    categories = service.get_skill_categories()

    assert categories == {"categories": []}


def test_process_and_validate_skill_bindings_should_raise_when_tables_missing(monkeypatch):
    service = _build_service()

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: False)

    try:
        service.process_and_validate_skill_bindings([{"skill_id": str(uuid4())}])
    except ValidateErrorException as exc:
        assert "技能数据表尚未初始化" in str(exc)
    else:
        raise AssertionError("expected ValidateErrorException")


def test_process_and_validate_skill_bindings_should_not_sync_when_packages_exist(monkeypatch):
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(
        service.db.session,
        "query",
        lambda *_args, **_kwargs: SimpleNamespace(
            limit=lambda *_args, **_kwargs: SimpleNamespace(first=lambda: object()),
        ),
    )
    monkeypatch.setattr(service, "ensure_local_catalog_synced", lambda force=False: (_ for _ in ()).throw(AssertionError("should not sync")))
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: package if skill_id == package_id else None)
    monkeypatch.setattr(
        service,
        "_get_skill_package_version_record",
        lambda skill_package_id, version: version_record if skill_package_id == package_id and version == 2 else None,
    )

    display_skills, validate_skills = service.process_and_validate_skill_bindings([{"skill_id": str(package_id)}])

    assert validate_skills == [{"skill_id": str(package_id)}]
    assert display_skills[0]["skill_id"] == str(package_id)


def test_process_and_validate_skill_bindings_should_not_sync_when_disabled(monkeypatch):
    service = _build_service()
    package_id = uuid4()

    monkeypatch.setattr(service, "_has_skill_package_table", lambda: True)
    monkeypatch.setattr(
        service.db.session,
        "query",
        lambda *_args, **_kwargs: SimpleNamespace(
            limit=lambda *_args, **_kwargs: SimpleNamespace(first=lambda: None),
        ),
    )
    monkeypatch.setattr(
        service,
        "ensure_local_catalog_synced",
        lambda force=False: (_ for _ in ()).throw(AssertionError("should not sync")),
    )
    monkeypatch.setattr(service, "_get_skill_package_record", lambda skill_id: None)

    display_skills, validate_skills = service.process_and_validate_skill_bindings(
        [{"skill_id": str(package_id)}],
        sync_catalog=False,
    )

    assert display_skills == []
    assert validate_skills == []


def test_build_skill_package_payload_should_expose_skill_markdown():
    service = _build_service()
    package_id = uuid4()
    package = _build_skill_package(package_id)
    version_record = _build_version_record(package_id)
    version_record.bundle = {
        "manifest.yaml": "source",
        "skill.md": "# 代码工坊\n\n这是技能正文。",
    }

    payload = service._build_package_payload(
        package=package,
        version_record=version_record,
        include_bundle=True,
    )

    assert payload["readme"] == "# 代码工坊\n\n这是技能正文。"
    assert payload["bundle"]["skill.md"] == "# 代码工坊\n\n这是技能正文。"
    assert "source_path" not in payload
    assert "enabled" not in payload
    assert "current_version" not in payload
    assert "versions" not in payload


def test_sync_local_package_should_skip_remote_sync_for_prompt_only_packages():
    updates = []

    class _QueryResult:
        def __init__(self, value):
            self._value = value

        def filter(self, *_args, **_kwargs):
            return self

        def one_or_none(self):
            return self._value

    class _Session:
        def __init__(self, package, version_record):
            self.package = package
            self.version_record = version_record

        def query(self, model):
            if model.__name__ == "SkillPackage":
                return _QueryResult(self.package)
            if model.__name__ == "SkillPackageVersion":
                return _QueryResult(self.version_record)
            raise AssertionError(f"unexpected model: {model}")

    class _DB:
        def __init__(self, package, version_record):
            self.session = _Session(package, version_record)

        @contextmanager
        def auto_commit(self):
            yield

    package_id = uuid4()
    package = _build_skill_package(package_id)
    package.executor_type = "prompt"
    package.sync_status = "failed"
    version_record = _build_version_record(package_id)
    version_record.sync_status = "failed"
    local_package = SimpleNamespace(
        source_key="gh-address-comments",
        source_path="/tmp/gh-address-comments",
        name="gh-address-comments",
        label="gh-address-comments",
        icon="",
        description="prompt skill",
        category="GitHub",
        tags=["github"],
        capabilities={},
        executor_type="prompt",
        tools=[],
        version=1,
        checksum="checksum",
        enabled=True,
        manifest={"description": "prompt skill", "tools": []},
        bundle={"manifest.yaml": "source", "skill.md": "# skill"},
    )

    service = SkillService(db=_DB(package, version_record), catalog_manager=SimpleNamespace(list_packages=lambda: []), scf_client=SimpleNamespace())

    def _record_update(model_instance, **kwargs):
        updates.append((model_instance, kwargs))
        for key, value in kwargs.items():
            setattr(model_instance, key, value)
        return model_instance

    service._has_skill_package_table = lambda: True
    service.update = _record_update
    service._sync_package_to_scf = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("SCF should not be called"))

    changed = service._sync_local_package(local_package)

    assert changed is True
    assert package.sync_status == "skipped"
    assert version_record.sync_status == "skipped"
    assert updates


def test_sync_local_package_should_short_circuit_when_already_skipped():
    updates = []

    class _QueryResult:
        def __init__(self, value):
            self._value = value

        def filter(self, *_args, **_kwargs):
            return self

        def one_or_none(self):
            return self._value

    class _Session:
        def __init__(self, package, version_record):
            self.package = package
            self.version_record = version_record

        def query(self, model):
            if model.__name__ == "SkillPackage":
                return _QueryResult(self.package)
            if model.__name__ == "SkillPackageVersion":
                return _QueryResult(self.version_record)
            raise AssertionError(f"unexpected model: {model}")

    class _DB:
        def __init__(self, package, version_record):
            self.session = _Session(package, version_record)

        @contextmanager
        def auto_commit(self):
            yield

    package_id = uuid4()
    package = _build_skill_package(package_id)
    package.executor_type = "prompt"
    package.sync_status = "skipped"
    package.source_checksum = "checksum"
    package.latest_source_version = 1
    version_record = _build_version_record(package_id)
    version_record.sync_status = "skipped"
    local_package = SimpleNamespace(
        source_key="gh-address-comments",
        source_path="/tmp/gh-address-comments",
        name="gh-address-comments",
        label="gh-address-comments",
        icon="",
        description="prompt skill",
        category="GitHub",
        tags=["github"],
        capabilities={},
        executor_type="prompt",
        tools=[],
        version=1,
        checksum="checksum",
        enabled=True,
        manifest={"description": "prompt skill", "tools": []},
        bundle={"manifest.yaml": "source", "skill.md": "# skill"},
    )

    service = SkillService(db=_DB(package, version_record), catalog_manager=SimpleNamespace(list_packages=lambda: []), scf_client=SimpleNamespace())
    service._has_skill_package_table = lambda: True
    service.update = lambda *args, **kwargs: updates.append((args, kwargs))
    service._sync_package_to_scf = lambda **_kwargs: (_ for _ in ()).throw(AssertionError("SCF should not be called"))

    changed = service._sync_local_package(local_package)

    assert changed is False
    assert updates == []
