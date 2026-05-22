from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

from internal.exception import NotFoundException, ValidateErrorException
from internal.core.language_model.entities.model_entity import ModelFeature
from internal.service.language_model_service import LanguageModelService


class _Provider:
    def __init__(self, provider_entity, models):
        self.provider_entity = provider_entity
        self.position = 1
        self._models = models

    def get_model_entities(self):
        return list(self._models.values())

    def get_model_entity(self, model_name: str):
        return self._models.get(model_name)

    @staticmethod
    def get_model_class(_model_type: str):
        return lambda **kwargs: SimpleNamespace(**kwargs)


def _build_service(manager):
    return LanguageModelService(db=SimpleNamespace(), language_model_manager=manager)


class TestLanguageModelService:
    def test_get_language_models_should_map_provider_and_models(self, monkeypatch):
        provider_entity = SimpleNamespace(
            name="openai",
            label="OpenAI",
            icon="openai.png",
            description="desc",
            background="#fff",
            supported_model_types=["chat"],
        )
        model_entity = SimpleNamespace(name="gpt-4o-mini")
        provider = _Provider(provider_entity=provider_entity, models={"gpt-4o-mini": model_entity})
        manager = SimpleNamespace(get_providers=lambda: [provider])
        service = _build_service(manager=manager)

        monkeypatch.setattr(
            "internal.service.language_model_service.convert_model_to_dict",
            lambda model_entities: [{"name": model_entities[0].name}],
        )

        result = service.get_language_models()

        assert result[0]["name"] == "openai"
        assert result[0]["label"] == "OpenAI"
        assert result[0]["models"][0]["name"] == "gpt-4o-mini"

    def test_get_language_model_should_raise_when_provider_not_found(self):
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: None))

        with pytest.raises(NotFoundException):
            service.get_language_model("missing", "gpt-4o-mini")

    def test_get_language_model_should_raise_when_model_not_found(self):
        provider_entity = SimpleNamespace(name="openai")
        provider = _Provider(provider_entity=provider_entity, models={})
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        with pytest.raises(NotFoundException):
            service.get_language_model("openai", "missing-model")

    def test_get_language_model_should_return_serialized_model(self, monkeypatch):
        model_entity = SimpleNamespace(name="gpt-4o-mini")
        provider = _Provider(provider_entity=SimpleNamespace(name="openai"), models={"gpt-4o-mini": model_entity})
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))
        monkeypatch.setattr(
            "internal.service.language_model_service.convert_model_to_dict",
            lambda model: {"name": model.name, "model_type": "chat"},
        )

        result = service.get_language_model("openai", "gpt-4o-mini")

        assert result["name"] == "gpt-4o-mini"
        assert result["model_type"] == "chat"

    def test_get_language_model_icon_should_return_bytes_and_mimetype(self, tmp_path):
        root_path = Path(tmp_path)
        icon_path = root_path / "internal/core/language_model/providers/openai/_asset/openai.png"
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.write_bytes(b"icon-bytes")

        # current_app.root_path 会向上回退两级，因此这里构造 api/app 目录让计算后回到 tmp_root。
        (root_path / "api/app").mkdir(parents=True, exist_ok=True)
        flask_app = Flask(__name__, root_path=str(root_path / "api/app"))

        provider_entity = SimpleNamespace(icon="openai.png")
        provider = SimpleNamespace(provider_entity=provider_entity)
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        with flask_app.app_context():
            content, mimetype = service.get_language_model_icon("openai")

        assert content == b"icon-bytes"
        assert mimetype == "image/png"

    def test_get_language_model_icon_should_raise_when_provider_missing(self):
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: None))

        with pytest.raises(NotFoundException):
            service.get_language_model_icon("missing")

    def test_get_language_model_icon_should_raise_when_icon_missing(self, tmp_path):
        root_path = Path(tmp_path)
        (root_path / "api/app").mkdir(parents=True, exist_ok=True)
        flask_app = Flask(__name__, root_path=str(root_path / "api/app"))
        provider = SimpleNamespace(provider_entity=SimpleNamespace(icon="missing.png"))
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        with flask_app.app_context():
            with pytest.raises(NotFoundException):
                service.get_language_model_icon("openai")

    def test_load_language_model_should_fallback_to_default_model(self, monkeypatch):
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: None))
        marker = SimpleNamespace(name="fallback-model")
        monkeypatch.setattr(service, "load_default_language_model", lambda: marker)

        result = service.load_language_model({"provider": "missing", "model": "x"})

        assert result is marker

    def test_load_language_model_should_build_model_instance_when_config_valid(self):
        model_entity = SimpleNamespace(
            model_type="chat",
            attributes={"model": "gpt-4o-mini", "temperature": 0.5},
            features=["tool_call"],
            metadata={"ctx": 8192},
        )
        provider = SimpleNamespace(
            get_model_entity=lambda _name: model_entity,
            get_model_class=lambda _type: (lambda **kwargs: SimpleNamespace(**kwargs)),
        )
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        llm = service.load_language_model(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "parameters": {"max_tokens": 4096},
            }
        )

        assert llm.model == "gpt-4o-mini"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 4096
        assert llm.features == ["tool_call"]
        assert llm.metadata == {"ctx": 8192}

    def test_load_default_language_model_should_use_expected_defaults(self):
        model_entity = SimpleNamespace(
            model_type="chat",
            attributes={"api_base": "https://api.example.com"},
            features=["tool_call"],
            metadata={"ctx": 8192},
        )
        provider = SimpleNamespace(
            get_model_entity=lambda _name: model_entity,
            get_model_class=lambda _type: (lambda **kwargs: SimpleNamespace(**kwargs)),
        )
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        llm = service.load_default_language_model()

        assert llm.temperature == 1
        assert llm.max_tokens == 8192
        assert llm.features == ["tool_call"]
        assert llm.metadata == {"ctx": 8192}

    def test_describe_runtime_capabilities_should_report_native_image_input(self):
        image_model_entity = SimpleNamespace(
            model_type="chat",
            attributes={"model": "gpt-4o-mini"},
            features=[ModelFeature.TOOL_CALL.value, ModelFeature.IMAGE_INPUT.value],
            metadata={},
        )
        provider = SimpleNamespace(
            get_model_entity=lambda _name: image_model_entity,
            get_model_class=lambda _type: (lambda **kwargs: SimpleNamespace(**kwargs)),
        )
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))

        capabilities = service.describe_runtime_capabilities(
            {"provider": "openai", "model": "gpt-4o-mini"},
            entrypoint=LanguageModelService.ENTRYPOINT_WEB_APP,
        )

        assert capabilities["image_input"]["enabled"] is True
        assert capabilities["image_input"]["via_fallback"] is False
        assert capabilities["effective_model"]["model"] == "gpt-4o-mini"
        assert capabilities["image_output"]["enabled"] is True
        assert capabilities["artifact_output"]["enabled"] is True

    def test_resolve_runtime_language_model_should_auto_upgrade_to_vision_fallback(self, monkeypatch):
        model_entities = {
            ("deepseek", "deepseek-chat"): SimpleNamespace(
                model_type="chat",
                attributes={"model": "deepseek-chat"},
                features=[ModelFeature.TOOL_CALL.value],
                metadata={},
            ),
            ("openai", "gpt-4o-mini"): SimpleNamespace(
                model_type="chat",
                attributes={"model": "gpt-4o-mini"},
                features=[ModelFeature.TOOL_CALL.value, ModelFeature.IMAGE_INPUT.value],
                metadata={},
            ),
        }

        def _get_provider(provider_name: str):
            return SimpleNamespace(
                get_model_entity=lambda model_name: model_entities.get((provider_name, model_name)),
                get_model_class=lambda _type: (lambda **kwargs: SimpleNamespace(**kwargs)),
            )

        service = _build_service(manager=SimpleNamespace(get_provider=_get_provider))
        monkeypatch.setattr(
            service,
            "_get_config_value",
            lambda key, default=None: {
                "IMAGE_REQUEST_POLICY": "auto_upgrade",
                "VISION_FALLBACK_PROVIDER": "openai",
                "VISION_FALLBACK_MODEL": "gpt-4o-mini",
            }.get(key, default),
        )

        resolution = service.resolve_runtime_language_model(
            {"provider": "deepseek", "model": "deepseek-chat"},
            image_urls=["https://example.com/cat.png"],
            entrypoint=LanguageModelService.ENTRYPOINT_WEB_APP,
        )

        assert resolution.llm.model == "gpt-4o-mini"
        assert resolution.resolution_action == "auto_upgrade"
        assert resolution.capabilities["image_input"]["via_fallback"] is True

    def test_resolve_runtime_language_model_should_raise_when_image_input_not_supported(self, monkeypatch):
        text_model_entity = SimpleNamespace(
            model_type="chat",
            attributes={"model": "deepseek-chat"},
            features=[ModelFeature.TOOL_CALL.value],
            metadata={},
        )
        provider = SimpleNamespace(
            get_model_entity=lambda _name: text_model_entity,
            get_model_class=lambda _type: (lambda **kwargs: SimpleNamespace(**kwargs)),
        )
        service = _build_service(manager=SimpleNamespace(get_provider=lambda _name: provider))
        monkeypatch.setattr(service, "_get_config_value", lambda _key, default=None: default)

        with pytest.raises(ValidateErrorException) as exc:
            service.resolve_runtime_language_model(
                {"provider": "deepseek", "model": "deepseek-chat"},
                image_urls=["https://example.com/cat.png"],
                entrypoint=LanguageModelService.ENTRYPOINT_WEB_APP,
            )

        assert exc.value.data["image_input"]["reason_code"] == "IMAGE_INPUT_UNSUPPORTED"
