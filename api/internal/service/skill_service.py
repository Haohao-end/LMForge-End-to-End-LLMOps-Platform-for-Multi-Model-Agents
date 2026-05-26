from __future__ import annotations

from copy import deepcopy
import logging
import mimetypes
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from flask import Flask, current_app, g, has_app_context
from injector import inject
from sqlalchemy import String, desc, func, inspect, or_
from sqlalchemy.exc import ProgrammingError
from langchain_core.tools import StructuredTool
from pydantic import create_model

from internal.core.skills import LocalSkillPackage, SkillCatalogManager, SkillScfClient, SkillToolFactory
from internal.entity.app_entity import AppStatus
from internal.exception import FailException, NotFoundException, ValidateErrorException
from internal.lib.helper import datetime_to_timestamp, generate_text_hash, utc_now_naive
from internal.model import SkillPackage, SkillPackageVersion
from pkg.paginator import Paginator
from pkg.sqlalchemy import SQLAlchemy

from .base_service import BaseService

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return bool(value)


def _normalize_int(value: Any, default: int = 1) -> int:
    try:
        normalized = int(value)
    except Exception:
        return default
    return normalized if normalized > 0 else default


def _normalize_tool_name(value: Any) -> str:
    normalized = _normalize_text(value)
    normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "skill"


@inject
@dataclass
class SkillService(BaseService):
    """技能包服务。"""

    db: SQLAlchemy
    catalog_manager: SkillCatalogManager = field(default_factory=SkillCatalogManager)
    scf_client: SkillScfClient = field(default_factory=SkillScfClient)

    def __post_init__(self) -> None:
        self.tool_factory = SkillToolFactory(self.scf_client)

    @staticmethod
    def _get_runtime_skill_payload_cache() -> dict[str, dict[str, Any]]:
        """获取请求级技能运行时缓存，避免同一请求重复查库。"""
        if not has_app_context():
            return {}

        cache = getattr(g, "_skill_runtime_payload_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            g._skill_runtime_payload_cache = cache
        return cache

    def _remember_runtime_skill_payload(
        self,
        package: SkillPackage,
        version_record: SkillPackageVersion,
    ) -> dict[str, Any]:
        """缓存技能运行时工具构建所需的包内容，供同请求内复用。"""
        runtime_payload = {
            "package_payload": self._build_package_payload(
                package=package,
                version_record=version_record,
                include_bundle=True,
            ),
            "tool_definitions": self._get_executable_tool_definitions(package, version_record),
        }
        cache = self._get_runtime_skill_payload_cache()
        cache[str(package.id)] = deepcopy(runtime_payload)
        return runtime_payload

    def _get_cached_runtime_skill_payload(self, skill_id: UUID | str) -> dict[str, Any] | None:
        """读取请求级技能运行时缓存。"""
        try:
            skill_uuid = skill_id if isinstance(skill_id, UUID) else UUID(str(skill_id))
        except Exception:
            return None

        cache = self._get_runtime_skill_payload_cache()
        cached_payload = cache.get(str(skill_uuid))
        if not isinstance(cached_payload, dict):
            return None
        return deepcopy(cached_payload)

    def _has_skill_package_table(self) -> bool:
        try:
            return inspect(self.db.engine).has_table(SkillPackage.__tablename__)
        except Exception:
            return False

    @staticmethod
    def _is_missing_skill_package_table_error(error: Exception) -> bool:
        orig = getattr(error, "orig", None)
        if orig is not None:
            if getattr(orig, "pgcode", None) == "42P01":
                return True
            if orig.__class__.__name__ == "UndefinedTable":
                return True

        message = str(error).lower()
        return "skill_package" in message and "does not exist" in message

    def _ensure_skill_package_table(self) -> None:
        if not self._has_skill_package_table():
            raise ValidateErrorException("技能数据表尚未初始化，请先执行数据库迁移")

    # ------------------------------------------------------------------ #
    #  本地 catalog 同步                                                    #
    # ------------------------------------------------------------------ #

    def ensure_local_catalog_synced(self, force: bool = False) -> int:
        """确保本地技能包目录已同步到数据库。"""
        if not self._has_skill_package_table():
            return 0

        self.catalog_manager.clear_cache()
        synced_count = 0
        for local_package in self.catalog_manager.list_packages():
            try:
                if self._sync_local_package(local_package, force=force):
                    synced_count += 1
            except ProgrammingError as exc:
                if not self._is_missing_skill_package_table_error(exc):
                    raise
                return synced_count
        return synced_count

    def _sync_local_package(self, local_package: LocalSkillPackage, force: bool = False) -> bool:
        self._ensure_skill_package_table()
        package = self.db.session.query(SkillPackage).filter(
            SkillPackage.source_key == local_package.source_key,
        ).one_or_none()

        current_version_record = None
        if package:
            current_version_record = self.db.session.query(SkillPackageVersion).filter(
                SkillPackageVersion.skill_package_id == package.id,
                SkillPackageVersion.version == local_package.version,
            ).one_or_none()
            if (
                not force
                and package.source_checksum == local_package.checksum
                and package.latest_source_version == local_package.version
                and package.sync_status in {"synced", "skipped", "failed"}
                and current_version_record
                and current_version_record.sync_status in {"synced", "skipped", "failed"}
            ):
                return False

        with self.db.auto_commit():
            if not package:
                package = SkillPackage(
                    source_key=local_package.source_key,
                    source_path=local_package.source_path,
                    name=local_package.name,
                    label=local_package.label,
                    icon=local_package.icon,
                    description=local_package.description,
                    category=local_package.category,
                    tags=local_package.tags,
                    capabilities=local_package.capabilities,
                    executor_type=local_package.executor_type,
                    enabled=local_package.enabled,
                    current_version=local_package.version,
                    latest_source_version=local_package.version,
                    source_checksum=local_package.checksum,
                    sync_status="pending",
                    sync_error="",
                    published_at=None,
                    updated_at=utc_now_naive(),
                )
                self.db.session.add(package)
                self.db.session.flush()
            else:
                self.update(
                    package,
                    source_path=local_package.source_path,
                    name=local_package.name,
                    label=local_package.label,
                    icon=local_package.icon,
                    description=local_package.description,
                    category=local_package.category,
                    tags=local_package.tags,
                    capabilities=local_package.capabilities,
                    executor_type=local_package.executor_type,
                    enabled=local_package.enabled,
                    current_version=local_package.version,
                    latest_source_version=local_package.version,
                    source_checksum=local_package.checksum,
                    updated_at=utc_now_naive(),
                )

            version_record = self.db.session.query(SkillPackageVersion).filter(
                SkillPackageVersion.skill_package_id == package.id,
                SkillPackageVersion.version == local_package.version,
            ).one_or_none()
            if not version_record:
                version_record = SkillPackageVersion(
                    skill_package_id=package.id,
                    version=local_package.version,
                    manifest=local_package.manifest,
                    bundle=local_package.bundle,
                    checksum=local_package.checksum,
                    sync_status="pending",
                    sync_error="",
                    updated_at=utc_now_naive(),
                )
                self.db.session.add(version_record)
            else:
                self.update(
                    version_record,
                    manifest=local_package.manifest,
                    bundle=local_package.bundle,
                    checksum=local_package.checksum,
                    updated_at=utc_now_naive(),
                )

        should_sync_remote = _normalize_text(local_package.executor_type).lower() == "scf" and bool(local_package.tools)
        if not should_sync_remote:
            with self.db.auto_commit():
                self.update(
                    package,
                    sync_status="skipped",
                    sync_error="",
                    published_at=package.published_at or utc_now_naive(),
                    updated_at=utc_now_naive(),
                )
                self.update(
                    version_record,
                    sync_status="skipped",
                    sync_error="",
                    updated_at=utc_now_naive(),
                )
            return True

        self._sync_package_to_scf(
            package=package,
            version_record=version_record,
            local_package=local_package,
            action="sync",
            force=force,
        )
        return True

    # ------------------------------------------------------------------ #
    #  查询与展示                                                           #
    # ------------------------------------------------------------------ #

    def get_skill_categories(self) -> dict[str, list[dict[str, Any]]]:
        """获取技能分类统计。"""
        if not self._has_skill_package_table():
            return {"categories": []}
        try:
            rows = (
                self.db.session.query(
                    SkillPackage.category,
                    func.count(SkillPackage.id),
                )
                .group_by(SkillPackage.category)
                .order_by(SkillPackage.category.asc())
                .all()
            )
        except ProgrammingError as exc:
            if self._is_missing_skill_package_table_error(exc):
                return {"categories": []}
            raise
        categories = [
            {
                "id": str(category or "").strip() or "通用",
                "name": str(category or "").strip() or "通用",
                "count": int(count or 0),
            }
            for category, count in rows
        ]
        return {"categories": categories}

    def get_skill_packages_with_page(self, req: Any) -> tuple[list[dict[str, Any]], Paginator]:
        """获取技能包分页列表。"""
        paginator = Paginator(db=self.db, req=req)
        if not self._has_skill_package_table():
            paginator.total_record = 0
            paginator.total_page = 0
            return [], paginator

        filters = []
        search_word = _normalize_text(getattr(req.search_word, "data", ""))
        category = _normalize_text(getattr(req.category, "data", ""))
        if search_word:
            like_word = f"%{search_word}%"
            filters.append(
                or_(
                    SkillPackage.name.ilike(like_word),
                    SkillPackage.label.ilike(like_word),
                    SkillPackage.description.ilike(like_word),
                    SkillPackage.tags.cast(String).ilike(like_word),
                    SkillPackage.source_key.ilike(like_word),
                    SkillPackage.category.ilike(like_word),
                )
            )
        if category and category != "all":
            filters.append(SkillPackage.category == category)

        try:
            packages = paginator.paginate(
                self.db.session.query(SkillPackage).filter(*filters).order_by(desc(SkillPackage.updated_at))
            )
        except ProgrammingError as exc:
            if self._is_missing_skill_package_table_error(exc):
                paginator.total_record = 0
                paginator.total_page = 0
                return [], paginator
            raise
        return [self._build_skill_package_summary(package) for package in packages], paginator

    def get_skill_package(self, skill_id: UUID | str) -> dict[str, Any]:
        """获取单个技能包详情。"""
        package = self._get_skill_package_record(skill_id)
        if not package:
            raise NotFoundException("该技能包不存在，请核实后重试")
        return self._build_skill_package_detail(package)

    def get_skill_package_icon(self, skill_id: UUID | str) -> tuple[bytes | None, str | None, str | None]:
        """获取技能包图标。"""
        package = self._get_skill_package_record(skill_id)
        if not package:
            raise NotFoundException("该技能包不存在，请核实后重试")

        icon = _normalize_text(package.icon)
        if icon.startswith(("http://", "https://")):
            return None, None, icon

        if not icon:
            return None, None, None

        icon_path = self._resolve_icon_path(package, icon)
        if not icon_path.exists():
            raise NotFoundException("该技能包图标不存在，请核实后重试")

        mimetype, _ = mimetypes.guess_type(str(icon_path))
        mimetype = mimetype or "application/octet-stream"
        with open(icon_path, "rb") as f:
            return f.read(), mimetype, None

    # ------------------------------------------------------------------ #
    #  技能绑定与运行时工具                                                #
    # ------------------------------------------------------------------ #

    def process_and_validate_skill_bindings(
        self,
        origin_skills: list[dict[str, Any]],
        *,
        sync_catalog: bool = True,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """校验技能绑定并返回展示信息与可落库信息。"""
        if not isinstance(origin_skills, list):
            return [], []
        if not origin_skills:
            return [], []

        self._ensure_skill_package_table()
        try:
            has_existing_packages = bool(self.db.session.query(SkillPackage.id).limit(1).first())
        except ProgrammingError as exc:
            if not self._is_missing_skill_package_table_error(exc):
                raise
            has_existing_packages = False

        if sync_catalog and not has_existing_packages:
            self.ensure_local_catalog_synced()

        validate_skills: list[dict[str, Any]] = []
        display_skills: list[dict[str, Any]] = []
        seen_skill_ids: set[str] = set()

        for binding in origin_skills:
            if not isinstance(binding, dict):
                continue

            skill_id = _normalize_text(binding.get("skill_id") or binding.get("id"))
            if not skill_id:
                continue

            try:
                skill_uuid = UUID(skill_id)
            except Exception:
                continue

            if skill_id in seen_skill_ids:
                raise ValidateErrorException("绑定技能存在重复")

            package = self._get_skill_package_record(skill_uuid)
            if not package:
                continue

            version_record = self._get_skill_package_version_record(package.id, package.current_version)
            if not version_record:
                continue

            self._remember_runtime_skill_payload(package, version_record)
            normalized_binding = {
                "skill_id": str(package.id),
            }
            validate_skills.append(normalized_binding)
            display_skills.append(self._build_skill_binding_display(package, version_record))
            seen_skill_ids.add(skill_id)

        return display_skills, validate_skills

    def get_langchain_tools_by_skill_bindings(
        self,
        skill_bindings: list[dict[str, Any]] | None,
        *,
        runtime_context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """根据技能绑定列表生成 LangChain 工具。"""
        if not isinstance(skill_bindings, list):
            return []

        if not self._has_skill_package_table():
            return []

        tools: list[Any] = []
        runtime_context = runtime_context or {}

        for binding in skill_bindings:
            if not isinstance(binding, dict):
                continue

            skill_id = _normalize_text(binding.get("skill_id"))
            if not skill_id:
                continue

            try:
                skill_uuid = UUID(skill_id)
            except Exception:
                continue

            cached_runtime_payload = self._get_cached_runtime_skill_payload(skill_uuid)
            if cached_runtime_payload:
                package_payload = cached_runtime_payload.get("package_payload")
                tool_definitions = cached_runtime_payload.get("tool_definitions")
                if not isinstance(package_payload, dict) or not isinstance(tool_definitions, list):
                    cached_runtime_payload = None
                else:
                    package_payload = deepcopy(package_payload)
                    tool_definitions = deepcopy(tool_definitions)
            if not cached_runtime_payload:
                package = self._get_skill_package_record(skill_uuid)
                if not package:
                    continue

                version_record = self._get_skill_package_version_record(package.id, package.current_version)
                if not version_record:
                    continue

                cached_runtime_payload = self._remember_runtime_skill_payload(package, version_record)
                package_payload = cached_runtime_payload.get("package_payload")
                tool_definitions = cached_runtime_payload.get("tool_definitions")

            if not isinstance(package_payload, dict) or not isinstance(tool_definitions, list):
                continue
            if not tool_definitions:
                continue
            tools.extend(
                self.tool_factory.build_tools(
                    package_payload=package_payload,
                    tool_definitions=tool_definitions,
                    runtime_context=runtime_context,
                )
            )

        return tools

    def get_langchain_prompt_loaders_by_skill_bindings(
        self,
        skill_bindings: list[dict[str, Any]] | None,
        *,
        runtime_context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """为已绑定的 prompt-only 技能生成按需加载全文的运行时工具。"""
        if not isinstance(skill_bindings, list):
            return []

        if not self._has_skill_package_table():
            return []

        runtime_context = runtime_context or {}
        tools: list[Any] = []
        seen_tool_names: set[str] = set()

        for binding in skill_bindings:
            if not isinstance(binding, dict):
                continue

            skill_id = _normalize_text(binding.get("skill_id"))
            if not skill_id:
                continue

            try:
                skill_uuid = UUID(skill_id)
            except Exception:
                continue

            cached_runtime_payload = self._get_cached_runtime_skill_payload(skill_uuid)
            if cached_runtime_payload:
                package_payload = cached_runtime_payload.get("package_payload")
                if not isinstance(package_payload, dict):
                    cached_runtime_payload = None
                else:
                    package_payload = deepcopy(package_payload)
            if not cached_runtime_payload:
                package = self._get_skill_package_record(skill_uuid)
                if not package:
                    continue

                if _normalize_text(package.executor_type).lower() == "scf":
                    continue

                version_record = self._get_skill_package_version_record(package.id, package.current_version)
                if not version_record:
                    continue
                cached_runtime_payload = self._remember_runtime_skill_payload(package, version_record)
                package_payload = cached_runtime_payload.get("package_payload")

            if not isinstance(package_payload, dict):
                continue
            if _normalize_text(package_payload.get("executor_type")).lower() == "scf":
                continue

            tool = self._build_prompt_only_skill_loader_tool(
                package=SimpleNamespace(
                    id=UUID(str(package_payload["skill_id"])),
                    source_key=package_payload.get("source_key", ""),
                    name=package_payload.get("name", ""),
                    label=package_payload.get("label", ""),
                    icon=package_payload.get("icon", ""),
                    description=package_payload.get("description", ""),
                    category=package_payload.get("category", ""),
                    tags=package_payload.get("tags", []),
                    capabilities=package_payload.get("capabilities", {}),
                    executor_type=package_payload.get("executor_type", ""),
                    source_path="",
                    created_at=0,
                    updated_at=0,
                    readme=package_payload.get("readme", ""),
                ),
                version_record=SimpleNamespace(
                    bundle=package_payload.get("bundle", {}),
                    manifest={"readme": package_payload.get("readme", ""), "tools": package_payload.get("tools", [])},
                ),
                runtime_context=runtime_context,
            )
            if tool.name in seen_tool_names:
                continue
            tools.append(tool)
            seen_tool_names.add(tool.name)

        return tools

    # ------------------------------------------------------------------ #
    #  内部辅助                                                             #
    # ------------------------------------------------------------------ #

    def _get_skill_package_record(self, skill_id: UUID | str) -> SkillPackage | None:
        try:
            skill_uuid = skill_id if isinstance(skill_id, UUID) else UUID(str(skill_id))
        except Exception:
            return None
        try:
            return self.db.session.query(SkillPackage).filter(SkillPackage.id == skill_uuid).one_or_none()
        except ProgrammingError as exc:
            if self._is_missing_skill_package_table_error(exc):
                return None
            raise

    def _get_skill_package_version_record(self, skill_package_id: UUID, version: int) -> SkillPackageVersion | None:
        try:
            return self.db.session.query(SkillPackageVersion).filter(
                SkillPackageVersion.skill_package_id == skill_package_id,
                SkillPackageVersion.version == version,
            ).one_or_none()
        except ProgrammingError as exc:
            if self._is_missing_skill_package_table_error(exc):
                return None
            raise

    def _normalize_tool_definitions(self, raw_tools: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_tools, list):
            return []

        tools: list[dict[str, Any]] = []
        for tool in raw_tools:
            if not isinstance(tool, dict):
                continue
            name = _normalize_text(tool.get("name"))
            if not name:
                continue
            input_schema = tool.get("input_schema") or tool.get("inputSchema") or {}
            if not isinstance(input_schema, dict):
                input_schema = {}
            tools.append(
                {
                    "name": name,
                    "label": _normalize_text(tool.get("label") or tool.get("title") or name) or name,
                    "description": _normalize_text(tool.get("description")),
                    "entrypoint": _normalize_text(tool.get("entrypoint") or tool.get("function") or name) or name,
                    "input_schema": input_schema,
                }
            )
        return tools

    def _get_executable_tool_definitions(
        self,
        package: SkillPackage,
        version_record: SkillPackageVersion | None,
    ) -> list[dict[str, Any]]:
        if not version_record:
            return []
        if _normalize_text(package.executor_type).lower() != "scf":
            return []
        return self._normalize_tool_definitions(version_record.manifest.get("tools"))

    def _build_skill_tool_inputs(self, input_schema: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(input_schema, dict):
            return []

        properties = input_schema.get("properties") or {}
        required_fields = set(input_schema.get("required") or [])
        inputs: list[dict[str, Any]] = []
        if isinstance(properties, dict):
            for prop_name, prop_schema in properties.items():
                if not isinstance(prop_schema, dict):
                    prop_schema = {}
                schema_type = str(prop_schema.get("type") or "string")
                inputs.append(
                    {
                        "name": prop_name,
                        "type": schema_type,
                        "required": prop_name in required_fields,
                        "description": _normalize_text(prop_schema.get("description")),
                    }
                )
        return inputs

    def _build_skill_package_summary(self, package: SkillPackage) -> dict[str, Any]:
        current_version_record = self._get_skill_package_version_record(package.id, package.current_version)
        return self._build_package_payload(
            package=package,
            version_record=current_version_record,
            include_tools=False,
        )

    def _build_skill_package_detail(self, package: SkillPackage) -> dict[str, Any]:
        current_version_record = self._get_skill_package_version_record(package.id, package.current_version)
        return self._build_package_payload(
            package=package,
            version_record=current_version_record,
            include_tools=True,
        )

    def _build_skill_binding_display(
        self,
        package: SkillPackage,
        version_record: SkillPackageVersion,
    ) -> dict[str, Any]:
        tool_definitions = self._get_executable_tool_definitions(package, version_record)
        return {
            "skill_id": str(package.id),
            "source_key": package.source_key,
            "name": package.name,
            "label": package.label,
            "icon": self._resolve_icon_url(package),
            "description": package.description,
            "readme": self._extract_skill_readme(package, version_record),
            "category": package.category,
            "tags": package.tags or [],
            "capabilities": package.capabilities or {},
            "executor_type": package.executor_type,
            "tool_count": len(tool_definitions),
            "tools": [
                {
                    "name": tool["name"],
                    "label": tool["label"],
                    "description": tool["description"],
                    "entrypoint": tool["entrypoint"],
                    "inputs": self._build_skill_tool_inputs(tool.get("input_schema")),
                }
                for tool in tool_definitions
            ],
            "created_at": datetime_to_timestamp(package.created_at),
            "updated_at": datetime_to_timestamp(package.updated_at),
        }

    def _build_prompt_only_skill_loader_tool(
        self,
        *,
        package: SkillPackage,
        version_record: SkillPackageVersion,
        runtime_context: dict[str, Any],
    ) -> StructuredTool:
        tool_name = f"skill_prompt__{_normalize_tool_name(package.source_key)}"
        tool_description = (
            f"按需加载已绑定 prompt-only 技能「{package.label}」的完整 Markdown 正文。"
            "适合在初始摘要不足以完成任务时临时调用，返回结果仅用于当前会话。"
        )
        args_schema = create_model(f"SkillPromptLoaderArgs_{package.id.hex}")
        package_payload = self._build_package_payload(
            package=package,
            version_record=version_record,
            include_tools=False,
        )

        def tool_func() -> dict[str, Any]:
            prompt_text = _normalize_text(package_payload.get("readme") or package_payload.get("description"))
            result = {
                "skill_id": package_payload["skill_id"],
                "source_key": package_payload["source_key"],
                "name": package_payload["name"],
                "label": package_payload["label"],
                "description": package_payload["description"],
                "category": package_payload["category"],
                "executor_type": package_payload["executor_type"],
                "prompt": prompt_text,
                "readme": prompt_text,
                "prompt_length": len(prompt_text),
                "lease_id": str(uuid4()),
                "ephemeral": True,
            }
            logger.info(
                "技能 prompt 按需加载成功: skill_id=%s source_key=%s prompt_length=%s",
                package_payload["skill_id"],
                package_payload["source_key"],
                len(prompt_text),
            )
            return result

        return StructuredTool.from_function(
            func=tool_func,
            name=tool_name,
            description=tool_description,
            args_schema=args_schema,
        )

    def _build_package_payload(
        self,
        *,
        package: SkillPackage,
        version_record: SkillPackageVersion | None,
        include_tools: bool = False,
        include_bundle: bool = False,
    ) -> dict[str, Any]:
        tool_definitions = self._get_executable_tool_definitions(package, version_record) if version_record else []

        tools = []
        if include_tools and version_record:
            tools = [
                {
                    "name": tool["name"],
                    "label": tool["label"],
                    "description": tool["description"],
                    "entrypoint": tool["entrypoint"],
                    "inputs": self._build_skill_tool_inputs(tool.get("input_schema")),
                }
                for tool in tool_definitions
            ]

        current_tool_count = len(tool_definitions)
        readme = self._extract_skill_readme(package, version_record)
        return {
            "id": str(package.id),
            "skill_id": str(package.id),
            "source_key": package.source_key,
            "name": package.name,
            "label": package.label,
            "icon": self._resolve_icon_url(package),
            "description": package.description,
            "readme": readme,
            "category": package.category,
            "tags": package.tags or [],
            "capabilities": package.capabilities or {},
            "executor_type": package.executor_type,
            "tool_count": current_tool_count,
            "tools": tools,
            "created_at": datetime_to_timestamp(package.created_at),
            "updated_at": datetime_to_timestamp(package.updated_at),
            **({"bundle": version_record.bundle or {}} if include_bundle and version_record else {}),
        }

    def _extract_skill_readme(
        self,
        package: SkillPackage,
        version_record: SkillPackageVersion | None,
    ) -> str:
        if version_record and isinstance(version_record.bundle, dict):
            for key in ("skill.md", "README.md", "readme.md"):
                readme = _normalize_text(version_record.bundle.get(key))
                if readme:
                    return readme

        if hasattr(package, "readme"):
            readme = _normalize_text(getattr(package, "readme"))
            if readme:
                return readme

        if version_record:
            readme = _normalize_text(version_record.manifest.get("readme"))
            if readme:
                return readme

        return _normalize_text(package.description)

    def _resolve_icon_url(self, package: SkillPackage) -> str:
        icon = _normalize_text(package.icon)
        if not icon:
            return ""
        if icon.startswith(("http://", "https://")):
            return icon
        return f"/skills/{package.id}/icon"

    def _resolve_icon_path(self, package: SkillPackage, icon: str):
        from pathlib import Path

        package_path = Path(package.source_path)
        return package_path / icon

    def _sync_current_package(self, package: SkillPackage, action: str, force: bool = False) -> None:
        version_record = self._get_skill_package_version_record(package.id, package.current_version)
        if not version_record:
            raise FailException("技能包当前版本不存在，请核实后重试")
        self._sync_package_to_scf(
            package=package,
            version_record=version_record,
            local_package=None,
            action=action,
            force=force,
        )

    def _build_sync_payload(
        self,
        *,
        package: SkillPackage,
        version_record: SkillPackageVersion,
        local_package: LocalSkillPackage | None,
        action: str,
        force: bool = False,
    ) -> dict[str, Any]:
        manifest = version_record.manifest or {}
        bundle = version_record.bundle or {}
        return {
            "action": action,
            "force": force,
            "skill": {
                "skill_id": str(package.id),
                "source_key": package.source_key,
                "source_path": package.source_path,
                "name": package.name,
                "label": package.label,
                "description": package.description,
                "category": package.category,
                "tags": package.tags or [],
                "capabilities": package.capabilities or {},
                "executor_type": package.executor_type,
                "enabled": package.enabled,
                "current_version": package.current_version,
                "latest_source_version": package.latest_source_version,
                "source_checksum": package.source_checksum,
                "manifest": manifest,
                "bundle": bundle,
                "local_source": {
                    "version": local_package.version if local_package else version_record.version,
                    "checksum": local_package.checksum if local_package else version_record.checksum,
                },
                "tool_count": len(self._normalize_tool_definitions(manifest.get("tools"))),
            },
            "version": {
                "id": str(version_record.id),
                "version": version_record.version,
                "checksum": version_record.checksum,
            },
        }

    def _sync_package_to_scf(
        self,
        *,
        package: SkillPackage,
        version_record: SkillPackageVersion,
        local_package: LocalSkillPackage | None,
        action: str,
        force: bool = False,
    ) -> dict[str, Any]:
        payload = self._build_sync_payload(
            package=package,
            version_record=version_record,
            local_package=local_package,
            action=action,
            force=force,
        )
        try:
            result = self.scf_client.sync_package(payload)
            if isinstance(result, dict) and result.get("skipped"):
                sync_status = "pending"
                sync_error = ""
            else:
                sync_status = "synced"
                sync_error = ""
        except Exception as exc:
            sync_status = "failed"
            sync_error = str(exc)
            result = {"error": sync_error}
            logger.exception("技能包同步失败: %s", exc)

        with self.db.auto_commit():
            self.update(
                package,
                sync_status=sync_status,
                sync_error=sync_error,
                published_at=package.published_at if sync_status != "synced" else package.published_at or utc_now_naive(),
                updated_at=utc_now_naive(),
            )
            self.update(
                version_record,
                sync_status=sync_status,
                sync_error=sync_error,
                updated_at=utc_now_naive(),
            )

        return result
