import os
import mimetypes
from dataclasses import dataclass
from typing import Any
from copy import deepcopy
from flask import current_app, has_app_context
from injector import inject, provider
from internal.core.language_model import LanguageModelManager
from internal.core.language_model.entities.model_entity import BaseLanguageModel, ModelFeature
from internal.exception import NotFoundException, ValidateErrorException
from internal.lib.helper import convert_model_to_dict
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService


@dataclass
class RuntimeModelResolution:
    """运行时模型解析结果。"""
    llm: BaseLanguageModel
    requested_model_config: dict[str, Any]
    effective_model_config: dict[str, Any]
    capabilities: dict[str, Any]
    resolution_action: str


@inject
@dataclass
class LanguageModelService(BaseService):
    """语言模型服务"""
    db: SQLAlchemy
    language_model_manager: LanguageModelManager

    IMAGE_REQUEST_POLICY_STRICT = "strict"
    IMAGE_REQUEST_POLICY_AUTO_UPGRADE = "auto_upgrade"
    ENTRYPOINT_DEBUGGER = "debugger"
    ENTRYPOINT_WEB_APP = "web_app"
    ENTRYPOINT_OPENAPI = "openapi"
    ENTRYPOINT_ASSISTANT_AGENT = "assistant_agent"
    ENTRYPOINT_PUBLIC_A2A = "public_a2a"

    def get_language_models(self) -> list[dict[str, Any]]:
        """获取 OpenAgent 项目中的所有模型列表信息"""
        # 1.调用语言模型管理器获取提供商列表
        providers = self.language_model_manager.get_providers()

        # 2.构建语言模型列表，循环读取数据
        language_models = []
        for provider in providers:
            # 3.获取提供商实体和模型实体列表
            provider_entity = provider.provider_entity
            model_entities = provider.get_model_entities()

            # 4.构建响应字典结构
            language_model = {
                "name": provider_entity.name,
                "position": provider.position,
                "label": provider_entity.label,
                "icon": provider_entity.icon,
                "description": provider_entity.description,
                "background": provider_entity.background,
                "support_model_types": provider_entity.supported_model_types,
                "models": convert_model_to_dict(model_entities),
            }
            language_models.append(language_model)

        return language_models

    def get_language_model(self, provider_name: str, model_name: str) -> dict[str, Any]:
        """根据传递的提供者名字+模型名字获取模型详细信息"""
        # 1.获取提供者+模型实体信息
        provider = self.language_model_manager.get_provider(provider_name)
        if not provider:
            raise NotFoundException("该服务提供者不存在")

        # 2.获取模型实体
        model_entity = provider.get_model_entity(model_name)
        if not model_entity:
            raise NotFoundException("该模型不存在")

        return convert_model_to_dict(model_entity)

    @classmethod
    def _get_config_value(cls, key: str, default: Any = None) -> Any:
        """优先从 Flask 配置读取，其次从环境变量读取。"""
        if has_app_context():
            return current_app.config.get(key, default)
        return os.getenv(key, default)

    @classmethod
    def get_default_model_config(cls) -> dict[str, Any]:
        """返回默认文本模型配置。"""
        return {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "parameters": {},
        }

    @classmethod
    def get_assistant_agent_model_config(cls) -> dict[str, Any]:
        """返回辅助 Agent 的基础模型配置。"""
        return {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "parameters": {
                "temperature": 0.8,
            },
        }

    def _load_model_components(self, model_config: dict[str, Any]) -> tuple[Any, Any, Any]:
        """根据模型配置加载 provider、model_entity 与 model_class。"""
        normalized_model_config = deepcopy(model_config or {})
        provider_name = str(normalized_model_config.get("provider", "")).strip()
        model_name = str(normalized_model_config.get("model", "")).strip()

        provider = self.language_model_manager.get_provider(provider_name)
        model_entity = provider.get_model_entity(model_name)
        if not model_entity:
            raise NotFoundException("该模型不存在")
        model_class = provider.get_model_class(model_entity.model_type)
        return provider, model_entity, model_class

    def _instantiate_language_model(self, model_config: dict[str, Any]) -> BaseLanguageModel:
        """严格按模型配置实例化语言模型。"""
        _, model_entity, model_class = self._load_model_components(model_config)
        normalized_model_config = deepcopy(model_config or {})
        parameters = normalized_model_config.get("parameters", {}) or {}
        return model_class(
            **model_entity.attributes,
            **parameters,
            features=model_entity.features,
            metadata=model_entity.metadata,
        )

    def _get_model_entity_or_none(self, model_config: dict[str, Any] | None) -> Any:
        """安全获取模型实体，失败时返回 None。"""
        if not model_config:
            return None
        try:
            _, model_entity, _ = self._load_model_components(model_config)
            return model_entity
        except Exception:
            return None

    @classmethod
    def _normalize_model_ref(cls, model_config: dict[str, Any] | None) -> dict[str, Any]:
        """抽取 provider/model 作为统一模型引用。"""
        normalized_model_config = deepcopy(model_config or {})
        return {
            "provider": str(normalized_model_config.get("provider", "")).strip(),
            "model": str(normalized_model_config.get("model", "")).strip(),
        }

    @classmethod
    def _entrypoint_prefix(cls, entrypoint: str) -> str:
        """将入口名字转换成环境变量前缀。"""
        normalized_entrypoint = str(entrypoint or "").strip().upper()
        if normalized_entrypoint == "":
            return ""
        return f"{normalized_entrypoint}_"

    def _resolve_image_request_policy(self, entrypoint: str) -> str:
        """解析入口对应的图片请求策略。"""
        entrypoint_prefix = self._entrypoint_prefix(entrypoint)
        policy = str(
            self._get_config_value(
                f"{entrypoint_prefix}IMAGE_REQUEST_POLICY",
                self._get_config_value("IMAGE_REQUEST_POLICY", self.IMAGE_REQUEST_POLICY_STRICT),
            )
            or self.IMAGE_REQUEST_POLICY_STRICT
        ).strip().lower()
        if policy not in {self.IMAGE_REQUEST_POLICY_STRICT, self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE}:
            return self.IMAGE_REQUEST_POLICY_STRICT
        return policy

    def _resolve_fallback_model_config(
        self,
        requested_model_config: dict[str, Any],
        entrypoint: str,
    ) -> dict[str, Any] | None:
        """解析入口对应的视觉兜底模型配置。"""
        entrypoint_prefix = self._entrypoint_prefix(entrypoint)
        provider_name = str(
            self._get_config_value(
                f"{entrypoint_prefix}VISION_FALLBACK_PROVIDER",
                self._get_config_value("VISION_FALLBACK_PROVIDER", ""),
            )
            or ""
        ).strip()
        model_name = str(
            self._get_config_value(
                f"{entrypoint_prefix}VISION_FALLBACK_MODEL",
                self._get_config_value("VISION_FALLBACK_MODEL", ""),
            )
            or ""
        ).strip()
        if provider_name == "" or model_name == "":
            return None

        return {
            "provider": provider_name,
            "model": model_name,
            "parameters": deepcopy((requested_model_config or {}).get("parameters", {}) or {}),
        }

    def _build_capabilities(
        self,
        *,
        requested_model_config: dict[str, Any],
        effective_model_config: dict[str, Any],
        entrypoint: str,
        allow_image_input: bool,
        resolution_action: str,
        reason_code: str = "",
        fallback_model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建统一的运行时能力描述。"""
        effective_model_entity = self._get_model_entity_or_none(effective_model_config)
        requested_model_entity = self._get_model_entity_or_none(requested_model_config)
        fallback_model_entity = self._get_model_entity_or_none(fallback_model_config)
        policy = self._resolve_image_request_policy(entrypoint)

        effective_features = list(getattr(effective_model_entity, "features", []) or [])
        requested_features = list(getattr(requested_model_entity, "features", []) or [])
        fallback_features = list(getattr(fallback_model_entity, "features", []) or [])

        effective_supports_image = ModelFeature.IMAGE_INPUT.value in effective_features
        requested_supports_image = ModelFeature.IMAGE_INPUT.value in requested_features
        fallback_supports_image = ModelFeature.IMAGE_INPUT.value in fallback_features
        via_fallback = (
            resolution_action == "auto_upgrade"
            and self._normalize_model_ref(requested_model_config) != self._normalize_model_ref(effective_model_config)
        )

        image_input_enabled = allow_image_input and (
            requested_supports_image or (policy == self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE and fallback_supports_image)
        )

        message = ""
        if not allow_image_input:
            message = "当前入口暂不支持图片输入"
        elif requested_supports_image:
            message = "当前模型支持图片输入"
        elif via_fallback and effective_supports_image:
            message = "当前请求会自动升级到视觉模型处理图片"
        elif policy == self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE and not fallback_supports_image:
            message = "当前模型不支持图片输入，且未配置可用的视觉兜底模型"
        else:
            message = "当前模型不支持图片输入"

        return {
            "requested_model": self._normalize_model_ref(requested_model_config),
            "effective_model": self._normalize_model_ref(effective_model_config),
            "features": effective_features,
            "requested_features": requested_features,
            "image_input": {
                "enabled": image_input_enabled,
                "via_fallback": via_fallback,
                "policy": policy,
                "requested_model_supports": requested_supports_image,
                "effective_model_supports": effective_supports_image,
                "fallback_model": self._normalize_model_ref(fallback_model_config) if fallback_model_config else None,
                "fallback_model_supports": fallback_supports_image,
                "reason_code": reason_code,
                "message": message,
            },
            "image_output": {
                "enabled": True,
                "reason_code": "IMAGE_OUTPUT_SUPPORTED",
            },
            "artifact_output": {
                "enabled": True,
                "reason_code": "ARTIFACT_OUTPUT_SUPPORTED",
            },
        }

    def describe_runtime_capabilities(
        self,
        model_config: dict[str, Any],
        *,
        entrypoint: str,
        allow_image_input: bool = True,
    ) -> dict[str, Any]:
        """描述入口在当前模型配置下的有效能力。"""
        normalized_model_config = deepcopy(model_config or {}) or self.get_default_model_config()
        fallback_model_config = self._resolve_fallback_model_config(normalized_model_config, entrypoint)
        effective_model_config = normalized_model_config
        resolution_action = "passthrough"

        requested_model_entity = self._get_model_entity_or_none(normalized_model_config)
        if requested_model_entity is None:
            effective_model_config = self.get_default_model_config()

        if allow_image_input:
            requested_model_entity = self._get_model_entity_or_none(effective_model_config)
            requested_supports_image = ModelFeature.IMAGE_INPUT.value in list(
                getattr(requested_model_entity, "features", []) or []
            )
            fallback_model_entity = self._get_model_entity_or_none(fallback_model_config)
            fallback_supports_image = ModelFeature.IMAGE_INPUT.value in list(
                getattr(fallback_model_entity, "features", []) or []
            )
            if not requested_supports_image and fallback_supports_image:
                resolution_action = "auto_upgrade"
                effective_model_config = fallback_model_config or effective_model_config

        return self._build_capabilities(
            requested_model_config=normalized_model_config,
            effective_model_config=effective_model_config,
            entrypoint=entrypoint,
            allow_image_input=allow_image_input,
            resolution_action=resolution_action,
            fallback_model_config=fallback_model_config,
        )

    def resolve_runtime_language_model(
        self,
        model_config: dict[str, Any],
        *,
        image_urls: list[str] | None = None,
        entrypoint: str,
        allow_image_input: bool = True,
    ) -> RuntimeModelResolution:
        """解析运行时要使用的语言模型，并在必要时执行图片能力兜底。"""
        normalized_model_config = deepcopy(model_config or {}) or self.get_default_model_config()
        fallback_model_config = self._resolve_fallback_model_config(normalized_model_config, entrypoint)
        image_urls = image_urls or []

        try:
            llm = self._instantiate_language_model(normalized_model_config)
            effective_model_config = normalized_model_config
        except Exception:
            llm = self.load_default_language_model()
            effective_model_config = self.get_default_model_config()

        if not image_urls:
            capabilities = self._build_capabilities(
                requested_model_config=normalized_model_config,
                effective_model_config=effective_model_config,
                entrypoint=entrypoint,
                allow_image_input=allow_image_input,
                resolution_action="passthrough",
                fallback_model_config=fallback_model_config,
            )
            return RuntimeModelResolution(
                llm=llm,
                requested_model_config=normalized_model_config,
                effective_model_config=effective_model_config,
                capabilities=capabilities,
                resolution_action="passthrough",
            )

        if not allow_image_input:
            capabilities = self._build_capabilities(
                requested_model_config=normalized_model_config,
                effective_model_config=effective_model_config,
                entrypoint=entrypoint,
                allow_image_input=False,
                resolution_action="reject",
                reason_code="IMAGE_INPUT_DISABLED_FOR_ENTRYPOINT",
                fallback_model_config=fallback_model_config,
            )
            raise ValidateErrorException(
                "当前入口暂不支持图片输入，请移除图片后重试",
                data=capabilities,
                reason_code="IMAGE_INPUT_DISABLED_FOR_ENTRYPOINT",
            )

        if ModelFeature.IMAGE_INPUT.value in llm.features:
            capabilities = self._build_capabilities(
                requested_model_config=normalized_model_config,
                effective_model_config=effective_model_config,
                entrypoint=entrypoint,
                allow_image_input=True,
                resolution_action="passthrough",
                fallback_model_config=fallback_model_config,
            )
            return RuntimeModelResolution(
                llm=llm,
                requested_model_config=normalized_model_config,
                effective_model_config=effective_model_config,
                capabilities=capabilities,
                resolution_action="passthrough",
            )

        if self._resolve_image_request_policy(entrypoint) == self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE and fallback_model_config:
            fallback_llm = self._instantiate_language_model(fallback_model_config)
            if ModelFeature.IMAGE_INPUT.value in fallback_llm.features:
                capabilities = self._build_capabilities(
                    requested_model_config=normalized_model_config,
                    effective_model_config=fallback_model_config,
                    entrypoint=entrypoint,
                    allow_image_input=True,
                    resolution_action="auto_upgrade",
                    fallback_model_config=fallback_model_config,
                )
                return RuntimeModelResolution(
                    llm=fallback_llm,
                    requested_model_config=normalized_model_config,
                    effective_model_config=fallback_model_config,
                    capabilities=capabilities,
                    resolution_action="auto_upgrade",
                )

        reason_code = "IMAGE_INPUT_UNSUPPORTED"
        if self._resolve_image_request_policy(entrypoint) == self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE and not fallback_model_config:
            reason_code = "VISION_FALLBACK_NOT_CONFIGURED"
        elif self._resolve_image_request_policy(entrypoint) == self.IMAGE_REQUEST_POLICY_AUTO_UPGRADE:
            reason_code = "VISION_FALLBACK_UNSUPPORTED"

        capabilities = self._build_capabilities(
            requested_model_config=normalized_model_config,
            effective_model_config=effective_model_config,
            entrypoint=entrypoint,
            allow_image_input=True,
            resolution_action="reject",
            reason_code=reason_code,
            fallback_model_config=fallback_model_config,
        )
        raise ValidateErrorException(
            "当前模型不支持图片输入，请切换到支持视觉的模型或配置视觉兜底模型后重试",
            data=capabilities,
            reason_code=reason_code,
        )

    def get_language_model_icon(self, provider_name: str) -> tuple[bytes, str]:
        """根据传递的提供者名字获取提供商对应的图标信息"""
        # 1.获取提供者信息
        provider = self.language_model_manager.get_provider(provider_name)
        if not provider:
            raise NotFoundException("该服务提供者不存在")

        # 2.获取项目的根路径信息
        root_path = os.path.dirname(os.path.dirname(current_app.root_path))

        # 3.拼接得到提供者所在的文件夹
        provider_path = os.path.join(
            root_path,
            "internal", "core", "language_model", "providers", provider_name,
        )

        # 4.拼接得到icon对应的路径
        icon_path = os.path.join(provider_path, "_asset", provider.provider_entity.icon)

        # 5.检测icon是否存在
        if not os.path.exists(icon_path):
            raise NotFoundException(f"该模型提供者_asset下未提供图标")

        # 6.读取icon的类型
        mimetype, _ = mimetypes.guess_type(icon_path)
        mimetype = mimetype or "application/octet-stream"

        # 7.读取icon的字节数据
        with open(icon_path, "rb") as f:
            byte_data = f.read()
            return byte_data, mimetype

    def load_language_model(self, model_config: dict[str, Any]) -> BaseLanguageModel:
        """根据传递的模型配置加载大语言模型，并返回其实例"""
        try:
            return self._instantiate_language_model(model_config)
        except Exception as _:
            return self.load_default_language_model()

    def load_default_language_model(self) -> BaseLanguageModel:
        """加载默认的大语言模型，在模型管理器中获取不到模型或者出错时使用默认模型进行兜底"""
        # 1.获取DeepSeek服务提供者与模型类
        provider = self.language_model_manager.get_provider("deepseek")
        model_entity = provider.get_model_entity("deepseek-chat")
        model_class = provider.get_model_class(model_entity.model_type)
        metadata = getattr(model_entity, "metadata", {}) or {}
        max_tokens = (
            getattr(model_entity, "max_output_tokens", 0)
            or getattr(model_entity, "context_window", 0)
            or metadata.get("ctx", 0)
            or metadata.get("context_window", 0)
            or 8000
        )

        # bug:原先写法使用的是LangChain封装的LLM类，需要替换成自定义封装的类，否则会识别到模型不存在features

        # 2.实例化模型并返回
        return model_class(
            **model_entity.attributes,
            temperature=1,
            max_tokens=max_tokens,
            features=model_entity.features,
            metadata=metadata,
        )
