from types import SimpleNamespace
from pathlib import Path

import pytest
import yaml

from internal.core.language_model.entities.model_entity import (
    BaseLanguageModel,
    ModelFeature,
    ModelType,
)
from internal.core.language_model.entities.provider_entity import (
    Provider,
    ProviderEntity,
)
from internal.core.language_model.language_model_manager import LanguageModelManager
from internal.core.language_model.providers.atlascloud.chat import Chat as AtlasCloudChat
from internal.core.language_model.providers.grok.chat import Chat as GrokChat
from internal.core.language_model.providers.moonshot.chat import Chat as MoonshotChat
from internal.core.language_model.providers.tongyi.chat import Chat as TongyiChat
from internal.core.language_model.providers.wenxin.chat import Chat as WenxinChat
from internal.exception import FailException, NotFoundException


def test_base_language_model_helpers_should_handle_pricing_and_multimodal_payload():
    dummy = SimpleNamespace(
        metadata={"pricing": {"input": 0.1, "output": 0.2, "unit": 1000}},
        features=[],
    )

    assert BaseLanguageModel.get_pricing(dummy) == (0.1, 0.2, 1000)
    assert (
        BaseLanguageModel.convert_to_human_message(
            dummy, "hello", ["https://img/1"]
        ).content
        == "hello"
    )

    dummy.features = [ModelFeature.IMAGE_INPUT.value]
    message = BaseLanguageModel.convert_to_human_message(
        dummy, "hello", ["https://img/1"]
    )
    assert message.content[0] == {"type": "text", "text": "hello"}
    assert message.content[1] == {
        "type": "image_url",
        "image_url": {"url": "https://img/1"},
    }


def test_base_language_model_helpers_should_reject_local_image_urls():
    dummy = SimpleNamespace(
        metadata={},
        features=[ModelFeature.IMAGE_INPUT.value],
    )

    with pytest.raises(FailException, match="本地图片存储已禁用"):
        BaseLanguageModel.convert_to_human_message(
            dummy,
            "hello",
            ["http://localhost:5001/upload-files/local/2026/05/18/demo.jpeg"],
        )


def test_provider_should_load_model_entities_and_expand_template_parameters(
    monkeypatch, tmp_path
):
    provider_root = tmp_path / "providers" / "demo"
    provider_root.mkdir(parents=True)
    (provider_root / "positions.yaml").write_text(
        yaml.safe_dump(["demo-chat"]), encoding="utf-8"
    )
    (provider_root / "demo-chat.yaml").write_text(
        yaml.safe_dump(
            {
                "model": "demo-chat",
                "label": "Demo Chat",
                "model_type": "chat",
                "context_window": 8192,
                "max_output_tokens": 1024,
                "parameters": [
                    {
                        "name": "temperature",
                        "use_template": "temperature",
                        "required": True,
                    },
                    {
                        "name": "custom_flag",
                        "label": "Custom Flag",
                        "type": "boolean",
                        "required": False,
                    },
                ],
                "metadata": {"pricing": {"input": 1.0, "output": 2.0, "unit": 1000}},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.os.path.abspath",
        lambda _path: str(tmp_path / "entities" / "provider_entity.py"),
    )
    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.dynamic_import",
        lambda module, symbol: f"{module}:{symbol}",
    )

    provider = Provider(
        name="demo",
        position=1,
        provider_entity=ProviderEntity(
            name="demo",
            label="Demo",
            description="demo provider",
            icon="icon.svg",
            background="#fff",
            supported_model_types=[ModelType.CHAT],
        ),
    )

    assert provider.get_model_class(ModelType.CHAT).endswith(":Chat")
    assert provider.get_model_entity("demo-chat").model_name == "demo-chat"
    assert len(provider.get_model_entities()) == 1
    # 这里断言模板字段被补全，确保 use_template 分支被执行。
    assert provider.get_model_entity("demo-chat").parameters[0].help != ""

    with pytest.raises(NotFoundException, match="模型类不存在"):
        provider.get_model_class(ModelType.COMPLETION)
    with pytest.raises(NotFoundException, match="模型实体不存在"):
        provider.get_model_entity("missing")


def test_provider_should_raise_when_positions_yaml_is_not_list(monkeypatch, tmp_path):
    provider_root = tmp_path / "providers" / "demo"
    provider_root.mkdir(parents=True)
    (provider_root / "positions.yaml").write_text(
        yaml.safe_dump({"bad": "shape"}), encoding="utf-8"
    )

    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.os.path.abspath",
        lambda _path: str(tmp_path / "entities" / "provider_entity.py"),
    )
    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.dynamic_import",
        lambda module, symbol: f"{module}:{symbol}",
    )

    with pytest.raises(FailException, match="positions.yaml数据格式错误"):
        Provider(
            name="demo",
            position=1,
            provider_entity=ProviderEntity(
                name="demo",
                label="Demo",
                description="demo provider",
                icon="icon.svg",
                background="#fff",
                supported_model_types=[ModelType.CHAT],
            ),
        )


def test_deepseek_provider_should_expose_latest_models(monkeypatch):
    repo_root = Path(__file__).resolve().parents[5]
    provider_entity_path = repo_root / "api/internal/core/language_model/entities/provider_entity.py"

    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.os.path.abspath",
        lambda _path: str(provider_entity_path),
    )
    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.dynamic_import",
        lambda module, symbol: f"{module}:{symbol}",
    )

    provider = Provider(
        name="deepseek",
        position=1,
        provider_entity=ProviderEntity(
            name="deepseek",
            label="DeepSeek",
            description="DeepSeek provider",
            icon="icon.png",
            background="#FFFFFF",
            supported_model_types=[ModelType.CHAT],
        ),
    )

    model_names = [model.model_name for model in provider.get_model_entities()]
    assert model_names[:2] == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert "deepseek-reasoner" in model_names
    assert "deepseek-chat" in model_names

    flash = provider.get_model_entity("deepseek-v4-flash")
    pro = provider.get_model_entity("deepseek-v4-pro")
    assert flash.context_window == 1_000_000
    assert flash.max_output_tokens == 384_000
    assert flash.attributes["model"] == "deepseek-v4-flash"
    assert pro.context_window == 1_000_000
    assert pro.max_output_tokens == 384_000
    assert pro.attributes["model"] == "deepseek-v4-pro"


def test_provider_pricing_should_match_documented_currency_per_provider():
    repo_root = Path(__file__).resolve().parents[5]
    providers_root = repo_root / "api/internal/core/language_model/providers"

    def assert_all_currency_fields(node, rel_path: str):
        if isinstance(node, dict):
            if "currency" in node:
                expected_currency = "RMB"
                assert (
                    node["currency"] == expected_currency
                ), f"{rel_path} has unexpected currency {node['currency']}"
            for key, value in node.items():
                assert_all_currency_fields(value, f"{rel_path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                assert_all_currency_fields(value, f"{rel_path}[{index}]")

    for yaml_path in providers_root.rglob("*.yaml"):
        if yaml_path.name in {"providers.yaml", "positions.yaml"}:
            continue

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue

        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            assert_all_currency_fields(
                metadata, yaml_path.relative_to(providers_root).as_posix()
            )

    atlascloud_v3 = yaml.safe_load(
        (providers_root / "atlascloud/deepseek-v3-0324.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_v3["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_v3["metadata"]["pricing"]["input"] == pytest.approx(0.216)
    assert atlascloud_v3["metadata"]["pricing"]["output"] == pytest.approx(0.88)
    assert atlascloud_v3["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_v3["context_window"] == 131_072
    assert atlascloud_v3["max_output_tokens"] == 16_384
    assert atlascloud_v3["features"] == ["tool_call", "agent_thought"]

    atlascloud_v4 = yaml.safe_load(
        (providers_root / "atlascloud/deepseek-v4-pro.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_v4["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_v4["metadata"]["pricing"]["input"] == pytest.approx(1.68)
    assert atlascloud_v4["metadata"]["pricing"]["output"] == pytest.approx(3.38)
    assert atlascloud_v4["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_v4["context_window"] == 1_048_576
    assert atlascloud_v4["max_output_tokens"] == 393_216
    assert atlascloud_v4["features"] == ["tool_call", "agent_thought"]

    atlascloud_v4_flash = yaml.safe_load(
        (providers_root / "atlascloud/deepseek-v4-flash.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_v4_flash["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_v4_flash["metadata"]["pricing"]["input"] == pytest.approx(0.14)
    assert atlascloud_v4_flash["metadata"]["pricing"]["output"] == pytest.approx(0.28)
    assert atlascloud_v4_flash["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_v4_flash["context_window"] == 1_048_576
    assert atlascloud_v4_flash["max_output_tokens"] == 393_216
    assert atlascloud_v4_flash["features"] == ["tool_call", "agent_thought"]

    atlascloud_kimi = yaml.safe_load(
        (providers_root / "atlascloud/kimi-k2.6.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_kimi["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_kimi["metadata"]["pricing"]["input"] == pytest.approx(0.95)
    assert atlascloud_kimi["metadata"]["pricing"]["output"] == pytest.approx(4.0)
    assert atlascloud_kimi["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_kimi["context_window"] == 262_144
    assert atlascloud_kimi["max_output_tokens"] == 262_144
    assert atlascloud_kimi["features"] == [
        "tool_call",
        "agent_thought",
        "image_input",
    ]

    atlascloud_qwen_plus = yaml.safe_load(
        (providers_root / "atlascloud/qwen3.6-plus.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_qwen_plus["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_qwen_plus["metadata"]["pricing"]["input"] == pytest.approx(0.325)
    assert atlascloud_qwen_plus["metadata"]["pricing"]["output"] == pytest.approx(1.95)
    assert atlascloud_qwen_plus["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_qwen_plus["metadata"]["pricing_cache_hit"]["currency"] == "RMB"
    assert atlascloud_qwen_plus["metadata"]["pricing_cache_hit"]["input"] == pytest.approx(
        0.325
    )
    assert atlascloud_qwen_plus["metadata"]["pricing_cache_hit"]["output"] == pytest.approx(
        1.95
    )

    atlascloud_qwen_coder = yaml.safe_load(
        (providers_root / "atlascloud/qwen3-coder-next.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_qwen_coder["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_qwen_coder["metadata"]["pricing"]["input"] == pytest.approx(0.18)
    assert atlascloud_qwen_coder["metadata"]["pricing"]["output"] == pytest.approx(1.35)
    assert atlascloud_qwen_coder["metadata"]["pricing"]["unit"] == pytest.approx(0.001)

    atlascloud_glm_51 = yaml.safe_load(
        (providers_root / "atlascloud/glm-5.1.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_glm_51["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_glm_51["metadata"]["pricing"]["input"] == pytest.approx(1.4)
    assert atlascloud_glm_51["metadata"]["pricing"]["output"] == pytest.approx(4.4)
    assert atlascloud_glm_51["metadata"]["pricing"]["unit"] == pytest.approx(0.001)
    assert atlascloud_glm_51["metadata"]["pricing_cache_hit"]["currency"] == "RMB"
    assert atlascloud_glm_51["metadata"]["pricing_cache_hit"]["input"] == pytest.approx(
        1.26
    )
    assert atlascloud_glm_51["metadata"]["pricing_cache_hit"]["output"] == pytest.approx(
        3.96
    )

    atlascloud_minimax = yaml.safe_load(
        (providers_root / "atlascloud/minimax-m2.7.yaml").read_text(encoding="utf-8")
    )
    assert atlascloud_minimax["metadata"]["pricing"]["currency"] == "RMB"
    assert atlascloud_minimax["metadata"]["pricing"]["input"] == pytest.approx(0.3)
    assert atlascloud_minimax["metadata"]["pricing"]["output"] == pytest.approx(1.2)
    assert atlascloud_minimax["metadata"]["pricing"]["unit"] == pytest.approx(0.001)

    deepseek_v4_pro = yaml.safe_load(
        (providers_root / "deepseek/deepseek-v4-pro.yaml").read_text(encoding="utf-8")
    )
    assert deepseek_v4_pro["metadata"]["pricing"]["currency"] == "RMB"
    assert deepseek_v4_pro["metadata"]["pricing"]["input"] == pytest.approx(0.000992)
    assert deepseek_v4_pro["metadata"]["pricing"]["output"] == pytest.approx(0.00595)
    assert deepseek_v4_pro["metadata"]["pricing_cache_hit"]["input"] == pytest.approx(
        0.000248
    )
    assert deepseek_v4_pro["metadata"]["pricing_cache_hit"]["output"] == pytest.approx(
        0.00595
    )

    gemini_pro = yaml.safe_load(
        (providers_root / "google/gemini-2.5-pro.yaml").read_text(encoding="utf-8")
    )
    assert gemini_pro["metadata"]["pricing"]["currency"] == "RMB"
    assert gemini_pro["metadata"]["pricing"]["input"] == pytest.approx(0.008548)
    assert gemini_pro["metadata"]["pricing"]["output"] == pytest.approx(0.068386)
    assert gemini_pro["metadata"]["pricing_tiered"]["long_context"]["currency"] == "RMB"
    assert gemini_pro["metadata"]["pricing_tiered"]["long_context"]["input"] == pytest.approx(
        0.017097
    )
    assert gemini_pro["metadata"]["pricing_tiered"]["long_context"]["output"] == pytest.approx(
        0.102579
    )

    grok_4 = yaml.safe_load((providers_root / "grok/grok-4.yaml").read_text(encoding="utf-8"))
    assert grok_4["metadata"]["pricing"]["currency"] == "RMB"
    assert grok_4["metadata"]["pricing"]["input"] == pytest.approx(0.020516)
    assert grok_4["metadata"]["pricing"]["output"] == pytest.approx(0.102579)
    assert grok_4["metadata"]["pricing_long_context"]["currency"] == "RMB"
    assert grok_4["metadata"]["pricing_long_context"]["input"] == pytest.approx(0.041032)
    assert grok_4["metadata"]["pricing_long_context"]["output"] == pytest.approx(0.205158)
    assert grok_4["metadata"]["pricing_cache_hit"]["currency"] == "RMB"
    assert grok_4["metadata"]["pricing_cache_hit"]["input"] == pytest.approx(0.005129)
    assert grok_4["metadata"]["pricing_cache_hit"]["output"] == pytest.approx(0.102579)

    gpt_5_2_pro = yaml.safe_load(
        (providers_root / "openai/gpt-5.2-pro.yaml").read_text(encoding="utf-8")
    )
    assert gpt_5_2_pro["metadata"]["pricing"]["currency"] == "RMB"
    assert gpt_5_2_pro["metadata"]["pricing"]["input"] == pytest.approx(0.136772)
    assert gpt_5_2_pro["metadata"]["pricing"]["output"] == pytest.approx(0.547089)

    glm_5 = yaml.safe_load((providers_root / "zhipu/glm-5.yaml").read_text(encoding="utf-8"))
    assert glm_5["metadata"]["pricing"]["currency"] == "RMB"
    assert glm_5["metadata"]["pricing"]["input"] == pytest.approx(0.004103)
    assert glm_5["metadata"]["pricing"]["output"] == pytest.approx(0.015045)


def test_atlascloud_provider_should_expose_documented_models(monkeypatch):
    repo_root = Path(__file__).resolve().parents[5]
    provider_entity_path = repo_root / "api/internal/core/language_model/entities/provider_entity.py"

    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.os.path.abspath",
        lambda _path: str(provider_entity_path),
    )
    monkeypatch.setattr(
        "internal.core.language_model.entities.provider_entity.dynamic_import",
        lambda module, symbol: f"{module}:{symbol}",
    )

    provider = Provider(
        name="atlascloud",
        position=1,
        provider_entity=ProviderEntity(
            name="atlascloud",
            label="Atlas Cloud",
            description="Atlas Cloud provider",
            icon="icon.png",
            background="#FFFFFF",
            supported_model_types=[ModelType.CHAT],
        ),
    )

    model_names = [model.model_name for model in provider.get_model_entities()]
    assert model_names == [
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "deepseek-v3.2-speciale",
        "deepseek-v3.2-exp",
        "deepseek-v3.2",
        "deepseek-v3.1-terminus",
        "deepseek-v3-0324",
        "deepseek-r1-0528",
        "kimi-k2.6",
        "kimi-k2.5",
        "kimi-k2-thinking",
        "qwen3-max-2026-01-23",
        "qwen3.6-plus",
        "qwen3.6-35b-a3b",
        "qwen3-next-80b-a3b-thinking",
        "qwen3-next-80b-a3b-instruct",
        "qwen3-coder-next",
        "qwen3-235b-a22b-thinking-2507",
        "qwen3-235b-a22b-instruct-2507",
        "qwen3-30b-a3b-thinking-2507",
        "qwen3-30b-a3b-instruct-2507",
        "qwen3-vl-235b-a22b-thinking",
        "qwen3-vl-235b-a22b-instruct",
        "qwen3-vl-30b-a3b-thinking",
        "qwen3-vl-30b-a3b-instruct",
        "qwen3-vl-8b-instruct",
        "qwen3.5-397b-a17b",
        "qwen3.5-122b-a10b",
        "qwen3.5-35b-a3b",
        "qwen3.5-27b",
        "glm-5.1",
        "glm-5v-turbo",
        "glm-5-turbo",
        "glm-5",
        "minimax-m2.7",
        "minimax-m2.5",
        "minimax-m2.1",
    ]

    v4 = provider.get_model_entity("deepseek-v4-pro")
    v4_flash = provider.get_model_entity("deepseek-v4-flash")
    kimi = provider.get_model_entity("kimi-k2.6")
    kimi_25 = provider.get_model_entity("kimi-k2.5")
    kimi_thinking = provider.get_model_entity("kimi-k2-thinking")
    qwen_plus = provider.get_model_entity("qwen3.6-plus")
    qwen_35b = provider.get_model_entity("qwen3.6-35b-a3b")
    qwen_122b = provider.get_model_entity("qwen3.5-122b-a10b")
    qwen_max = provider.get_model_entity("qwen3-max-2026-01-23")
    qwen_next_thinking = provider.get_model_entity("qwen3-next-80b-a3b-thinking")
    qwen_next_instruct = provider.get_model_entity("qwen3-next-80b-a3b-instruct")
    qwen_coder = provider.get_model_entity("qwen3-coder-next")
    qwen_235b_thinking = provider.get_model_entity("qwen3-235b-a22b-thinking-2507")
    qwen_235b_instruct = provider.get_model_entity("qwen3-235b-a22b-instruct-2507")
    qwen_30b_thinking = provider.get_model_entity("qwen3-30b-a3b-thinking-2507")
    qwen_30b_instruct = provider.get_model_entity("qwen3-30b-a3b-instruct-2507")
    qwen_vl_235b_thinking = provider.get_model_entity("qwen3-vl-235b-a22b-thinking")
    qwen_vl_30b_thinking = provider.get_model_entity("qwen3-vl-30b-a3b-thinking")
    qwen_vl_30b = provider.get_model_entity("qwen3-vl-30b-a3b-instruct")
    qwen_vl_235b = provider.get_model_entity("qwen3-vl-235b-a22b-instruct")
    glm_51 = provider.get_model_entity("glm-5.1")
    glm_5v = provider.get_model_entity("glm-5v-turbo")
    glm_5 = provider.get_model_entity("glm-5")
    minimax = provider.get_model_entity("minimax-m2.7")
    v3 = provider.get_model_entity("deepseek-v3-0324")
    v32 = provider.get_model_entity("deepseek-v3.2")
    v32_exp = provider.get_model_entity("deepseek-v3.2-exp")
    v32_speciale = provider.get_model_entity("deepseek-v3.2-speciale")
    v31_terminus = provider.get_model_entity("deepseek-v3.1-terminus")
    deepseek_r1 = provider.get_model_entity("deepseek-r1-0528")
    qwen_minimax_21 = provider.get_model_entity("minimax-m2.1")
    qwen_minimax_25 = provider.get_model_entity("minimax-m2.5")
    assert v4.context_window == 1_048_576
    assert v4.max_output_tokens == 393_216
    assert v4.attributes["model"] == "deepseek-ai/deepseek-v4-pro"
    assert v4.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v4_flash.context_window == 1_048_576
    assert v4_flash.max_output_tokens == 393_216
    assert v4_flash.attributes["model"] == "deepseek-ai/deepseek-v4-flash"
    assert v4_flash.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert kimi.context_window == 262_144
    assert kimi.max_output_tokens == 262_144
    assert kimi.attributes["model"] == "moonshotai/kimi-k2.6"
    assert kimi.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert kimi_25.context_window == 262_144
    assert kimi_25.max_output_tokens == 262_144
    assert kimi_25.attributes["model"] == "moonshotai/kimi-k2.5"
    assert kimi_25.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert kimi_25.metadata["pricing"]["input"] == pytest.approx(0.49)
    assert kimi_25.metadata["pricing"]["output"] == pytest.approx(2.5)
    assert kimi_thinking.context_window == 262_144
    assert kimi_thinking.max_output_tokens == 262_144
    assert kimi_thinking.attributes["model"] == "moonshotai/Kimi-K2-Thinking"
    assert kimi_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert kimi_thinking.metadata["pricing"]["input"] == pytest.approx(0.6)
    assert kimi_thinking.metadata["pricing"]["output"] == pytest.approx(2.5)
    with pytest.raises(NotFoundException):
        provider.get_model_entity("gpt-5.2")
    assert qwen_plus.context_window == 1_000_000
    assert qwen_plus.max_output_tokens == 65_536
    assert qwen_plus.attributes["model"] == "qwen/qwen3.6-plus"
    assert qwen_plus.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_plus.metadata["pricing"]["input"] == pytest.approx(0.325)
    assert qwen_plus.metadata["pricing"]["output"] == pytest.approx(1.95)
    assert qwen_35b.context_window == 262_144
    assert qwen_35b.max_output_tokens == 65_536
    assert qwen_35b.attributes["model"] == "qwen/qwen3.6-35b-a3b"
    assert qwen_35b.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_35b.metadata["pricing"]["input"] == pytest.approx(0.161)
    assert qwen_35b.metadata["pricing"]["output"] == pytest.approx(0.965)
    assert qwen_122b.context_window == 262_144
    assert qwen_122b.max_output_tokens == 65_536
    assert qwen_122b.attributes["model"] == "qwen/qwen3.5-122b-a10b"
    assert qwen_122b.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert qwen_122b.metadata["pricing"]["input"] == pytest.approx(0.3)
    assert qwen_122b.metadata["pricing"]["output"] == pytest.approx(2.4)
    assert qwen_max.context_window == 252_000
    assert qwen_max.max_output_tokens == 32_000
    assert qwen_max.attributes["model"] == "qwen/qwen3-max-2026-01-23"
    assert qwen_max.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_max.metadata["pricing"]["input"] == pytest.approx(1.2)
    assert qwen_max.metadata["pricing"]["output"] == pytest.approx(6.0)
    assert qwen_next_thinking.context_window == 262_144
    assert qwen_next_thinking.max_output_tokens == 32_768
    assert qwen_next_thinking.attributes["model"] == "Qwen/Qwen3-Next-80B-A3B-Thinking"
    assert qwen_next_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_next_thinking.metadata["pricing"]["input"] == pytest.approx(0.15)
    assert qwen_next_thinking.metadata["pricing"]["output"] == pytest.approx(1.5)
    assert qwen_next_instruct.context_window == 262_144
    assert qwen_next_instruct.max_output_tokens == 131_072
    assert qwen_next_instruct.attributes["model"] == "Qwen/Qwen3-Next-80B-A3B-Instruct"
    assert qwen_next_instruct.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_next_instruct.metadata["pricing"]["input"] == pytest.approx(0.15)
    assert qwen_next_instruct.metadata["pricing"]["output"] == pytest.approx(1.5)
    assert qwen_coder.context_window == 262_144
    assert qwen_coder.max_output_tokens == 262_144
    assert qwen_coder.attributes["model"] == "qwen/qwen3-coder-next"
    assert qwen_coder.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_235b_thinking.context_window == 128_000
    assert qwen_235b_thinking.max_output_tokens == 32_768
    assert qwen_235b_thinking.attributes["model"] == "qwen/qwen3-235b-a22b-thinking-2507"
    assert qwen_235b_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_235b_thinking.metadata["pricing"]["input"] == pytest.approx(0.28)
    assert qwen_235b_thinking.metadata["pricing"]["output"] == pytest.approx(2.3)
    assert qwen_235b_instruct.context_window == 131_072
    assert qwen_235b_instruct.max_output_tokens == 131_072
    assert qwen_235b_instruct.attributes["model"] == "Qwen/Qwen3-235B-A22B-Instruct-2507"
    assert qwen_235b_instruct.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_235b_instruct.metadata["pricing"]["input"] == pytest.approx(0.21)
    assert qwen_235b_instruct.metadata["pricing"]["output"] == pytest.approx(0.63)
    assert qwen_30b_thinking.context_window == 131_072
    assert qwen_30b_thinking.max_output_tokens == 131_072
    assert qwen_30b_thinking.attributes["model"] == "qwen/qwen3-30b-a3b-thinking-2507"
    assert qwen_30b_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_30b_thinking.metadata["pricing"]["input"] == pytest.approx(0.08)
    assert qwen_30b_thinking.metadata["pricing"]["output"] == pytest.approx(0.4)
    assert qwen_30b_instruct.context_window == 131_072
    assert qwen_30b_instruct.max_output_tokens == 131_072
    assert qwen_30b_instruct.attributes["model"] == "Qwen/Qwen3-30B-A3B-Instruct-2507"
    assert qwen_30b_instruct.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
    ]
    assert qwen_30b_instruct.metadata["pricing"]["input"] == pytest.approx(0.1)
    assert qwen_30b_instruct.metadata["pricing"]["output"] == pytest.approx(0.3)
    assert qwen_vl_235b_thinking.context_window == 131_072
    assert qwen_vl_235b_thinking.max_output_tokens == 65_536
    assert qwen_vl_235b_thinking.attributes["model"] == "qwen/qwen3-vl-235b-a22b-thinking"
    assert qwen_vl_235b_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert qwen_vl_235b_thinking.metadata["pricing"]["input"] == pytest.approx(0.5)
    assert qwen_vl_235b_thinking.metadata["pricing"]["output"] == pytest.approx(2.5)
    assert qwen_vl_30b_thinking.context_window == 128_000
    assert qwen_vl_30b_thinking.max_output_tokens == 32_000
    assert qwen_vl_30b_thinking.attributes["model"] == "qwen/qwen3-vl-30b-a3b-thinking"
    assert qwen_vl_30b_thinking.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert qwen_vl_30b_thinking.metadata["pricing"]["input"] == pytest.approx(0.15)
    assert qwen_vl_30b_thinking.metadata["pricing"]["output"] == pytest.approx(1.5)
    assert qwen_vl_30b.context_window == 128_000
    assert qwen_vl_30b.max_output_tokens == 32_000
    assert qwen_vl_30b.attributes["model"] == "qwen/qwen3-vl-30b-a3b-instruct"
    assert qwen_vl_30b.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert qwen_vl_30b.metadata["pricing"]["input"] == pytest.approx(0.15)
    assert qwen_vl_30b.metadata["pricing"]["output"] == pytest.approx(0.6)
    assert qwen_vl_235b.context_window == 131_072
    assert qwen_vl_235b.max_output_tokens == 32_768
    assert qwen_vl_235b.attributes["model"] == "Qwen/Qwen3-VL-235B-A22B-Instruct"
    assert qwen_vl_235b.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert qwen_vl_235b.metadata["pricing"]["input"] == pytest.approx(0.3)
    assert qwen_vl_235b.metadata["pricing"]["output"] == pytest.approx(1.5)
    assert glm_51.context_window == 202_752
    assert glm_51.max_output_tokens == 202_752
    assert glm_51.attributes["model"] == "zai-org/glm-5.1"
    assert glm_51.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert glm_5.context_window == 202_752
    assert glm_5.max_output_tokens == 202_752
    assert glm_5.attributes["model"] == "zai-org/glm-5"
    assert glm_5.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert glm_5.metadata["pricing"]["input"] == pytest.approx(0.95)
    assert glm_5.metadata["pricing"]["output"] == pytest.approx(3.15)
    assert glm_5v.context_window == 202_752
    assert glm_5v.max_output_tokens == 131_072
    assert glm_5v.attributes["model"] == "zai-org/glm-5v-turbo"
    assert glm_5v.features == [
        ModelFeature.TOOL_CALL.value,
        ModelFeature.AGENT_THOUGHT.value,
        ModelFeature.IMAGE_INPUT.value,
    ]
    assert glm_5v.metadata["pricing"]["input"] == pytest.approx(1.2)
    assert glm_5v.metadata["pricing"]["output"] == pytest.approx(4.0)
    assert minimax.context_window == 196_608
    assert minimax.max_output_tokens == 196_608
    assert minimax.attributes["model"] == "minimaxai/minimax-m2.7"
    assert minimax.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v3.context_window == 131_072
    assert v3.max_output_tokens == 16_384
    assert v3.attributes["model"] == "deepseek-ai/DeepSeek-V3-0324"
    assert v3.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v32.context_window == 163_840
    assert v32.max_output_tokens == 163_840
    assert v32.attributes["model"] == "deepseek-ai/deepseek-v3.2"
    assert v32.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v32.metadata["pricing"]["input"] == pytest.approx(0.26)
    assert v32.metadata["pricing"]["output"] == pytest.approx(0.38)
    assert v32_exp.context_window == 163_840
    assert v32_exp.max_output_tokens == 163_840
    assert v32_exp.attributes["model"] == "deepseek-ai/DeepSeek-V3.2-Exp"
    assert v32_exp.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v32_exp.metadata["pricing"]["input"] == pytest.approx(0.27)
    assert v32_exp.metadata["pricing"]["output"] == pytest.approx(0.41)
    assert v32_speciale.context_window == 163_840
    assert v32_speciale.max_output_tokens == 163_840
    assert v32_speciale.attributes["model"] == "deepseek-ai/deepseek-v3.2-speciale"
    assert v32_speciale.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v32_speciale.metadata["pricing"]["input"] == pytest.approx(0.287)
    assert v32_speciale.metadata["pricing"]["output"] == pytest.approx(0.431)
    assert v31_terminus.context_window == 131_072
    assert v31_terminus.max_output_tokens == 65_536
    assert v31_terminus.attributes["model"] == "deepseek-ai/DeepSeek-V3.1-Terminus"
    assert v31_terminus.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert v31_terminus.metadata["pricing"]["input"] == pytest.approx(0.3)
    assert v31_terminus.metadata["pricing"]["output"] == pytest.approx(0.95)
    assert deepseek_r1.context_window == 131_072
    assert deepseek_r1.max_output_tokens == 131_072
    assert deepseek_r1.attributes["model"] == "deepseek-ai/DeepSeek-R1-0528"
    assert deepseek_r1.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert deepseek_r1.metadata["pricing"]["input"] == pytest.approx(0.55)
    assert deepseek_r1.metadata["pricing"]["output"] == pytest.approx(2.15)
    assert qwen_minimax_21.context_window == 196_608
    assert qwen_minimax_21.max_output_tokens == 65_536
    assert qwen_minimax_21.attributes["model"] == "minimaxai/minimax-m2.1"
    assert qwen_minimax_21.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_minimax_21.metadata["pricing"]["input"] == pytest.approx(0.29)
    assert qwen_minimax_21.metadata["pricing"]["output"] == pytest.approx(0.95)
    assert qwen_minimax_25.context_window == 196_608
    assert qwen_minimax_25.max_output_tokens == 196_608
    assert qwen_minimax_25.attributes["model"] == "minimaxai/minimax-m2.5"
    assert qwen_minimax_25.features == [ModelFeature.TOOL_CALL.value, ModelFeature.AGENT_THOUGHT.value]
    assert qwen_minimax_25.metadata["pricing"]["input"] == pytest.approx(0.295)
    assert qwen_minimax_25.metadata["pricing"]["output"] == pytest.approx(1.2)


def test_language_model_manager_should_load_and_delegate(monkeypatch, tmp_path):
    providers_dir = tmp_path / "providers"
    providers_dir.mkdir()
    (providers_dir / "providers.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "name": "alpha",
                    "label": "Alpha",
                    "description": "alpha provider",
                    "icon": "a.svg",
                    "background": "#111",
                    "supported_model_types": ["chat"],
                },
                {
                    "name": "beta",
                    "label": "Beta",
                    "description": "beta provider",
                    "icon": "b.svg",
                    "background": "#222",
                    "supported_model_types": ["completion"],
                },
            ],
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    class _FakeProvider:
        def __init__(self, name, position, provider_entity):
            self.name = name
            self.position = position
            self.provider_entity = provider_entity

        @staticmethod
        def get_model_class(model_type):
            return f"class:{model_type}"

        @staticmethod
        def get_model_entity(_model_name):
            return SimpleNamespace(model_type=ModelType.CHAT)

    monkeypatch.setattr(
        "internal.core.language_model.language_model_manager.os.path.abspath",
        lambda _path: str(tmp_path / "language_model_manager.py"),
    )
    monkeypatch.setattr(
        "internal.core.language_model.language_model_manager.Provider", _FakeProvider
    )

    manager = LanguageModelManager()

    assert [provider.name for provider in manager.get_providers()] == ["alpha", "beta"]
    assert manager.get_provider("alpha").position == 1

    with pytest.raises(NotFoundException, match="服务提供商不存在"):
        manager.get_provider("missing")


def test_language_model_manager_should_preserve_documented_provider_order(monkeypatch):
    repo_root = Path(__file__).resolve().parents[5]
    manager_path = repo_root / "api/internal/core/language_model/language_model_manager.py"
    provider_entity_path = (
        repo_root / "api/internal/core/language_model/entities/provider_entity.py"
    )

    def _fake_abspath(path):
        path_text = str(path)
        if path_text.endswith("language_model_manager.py"):
            return str(manager_path)
        if path_text.endswith("provider_entity.py"):
            return str(provider_entity_path)
        return path_text

    monkeypatch.setattr("os.path.abspath", _fake_abspath)

    manager = LanguageModelManager()
    provider_names = [provider.name for provider in manager.get_providers()]

    assert provider_names[0] == "atlascloud"
    assert provider_names[1] == "deepseek"
    assert provider_names[-1] == "openai"


def test_grok_env_resolver_should_apply_priority(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "")
    monkeypatch.setenv("XAI_API_KEY", "xkey")
    monkeypatch.delenv("GROK_API_BASE", raising=False)
    monkeypatch.delenv("XAI_API_BASE", raising=False)
    grok_resolved = GrokChat.resolve_grok_env({"model": "grok"})
    assert grok_resolved["api_key"] == "xkey"
    assert grok_resolved["base_url"] == "https://api.x.ai/v1"

    explicit = GrokChat.resolve_grok_env(
        {"api_key": "explicit", "base_url": "https://custom"}
    )
    assert explicit["api_key"] == "explicit"
    assert explicit["base_url"] == "https://custom"
    assert GrokChat.resolve_grok_env("raw-values") == "raw-values"

    # 覆盖 grok 的“openai_* 显式参数存在时不覆盖”分支。
    grok_openai = GrokChat.resolve_grok_env(
        {"openai_api_key": "ok", "openai_api_base": "obase"}
    )
    assert "api_key" not in grok_openai
    assert "base_url" not in grok_openai

    # 覆盖 grok 无 key 环境时不注入 api_key 的分支（28->31）。
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_BASE", "https://grok-base")
    grok_no_key = GrokChat.resolve_grok_env({"model": "grok"})
    assert "api_key" not in grok_no_key
    assert grok_no_key["base_url"] == "https://grok-base"

    # 覆盖 grok 中 `if base:` 的 False 分支（37->40）。
    class _FlipBool:
        def __init__(self):
            self.calls = 0

        def __bool__(self):
            self.calls += 1
            # 第一次用于 `or` 表达式时返回 True，第二次用于 `if base:` 时返回 False。
            return self.calls == 1

    flip = _FlipBool()

    def _fake_getenv(key, default=""):
        if key == "GROK_API_BASE":
            return flip
        return ""

    monkeypatch.setattr(
        "internal.core.language_model.providers.grok.chat.os.getenv", _fake_getenv
    )
    grok_flip = GrokChat.resolve_grok_env({"model": "grok"})
    assert "base_url" not in grok_flip


def test_atlascloud_env_resolver_should_apply_priority(monkeypatch):
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "atlas-key")
    monkeypatch.delenv("ATLAS_CLOUD_API_KEY", raising=False)
    monkeypatch.delenv("ATLASCLOUD_API_BASE", raising=False)
    monkeypatch.delenv("ATLAS_CLOUD_API_BASE", raising=False)
    monkeypatch.delenv("ATLASCLOUD_REQUEST_TIMEOUT", raising=False)
    monkeypatch.delenv("ATLAS_CLOUD_REQUEST_TIMEOUT", raising=False)
    monkeypatch.delenv("LLM_REQUEST_TIMEOUT", raising=False)

    resolved = AtlasCloudChat.resolve_atlascloud_env({"model": "deepseek-v3"})
    assert resolved["api_key"] == "atlas-key"
    assert resolved["base_url"] == "https://api.atlascloud.ai/v1"
    assert resolved["timeout"] == 1800.0

    explicit = AtlasCloudChat.resolve_atlascloud_env(
        {
            "api_key": "explicit",
            "base_url": "https://custom.example/v1",
            "timeout": 123,
        }
    )
    assert explicit["api_key"] == "explicit"
    assert explicit["base_url"] == "https://custom.example/v1"
    assert explicit["timeout"] == 123

    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "120")
    fallback = AtlasCloudChat.resolve_atlascloud_env({"model": "deepseek-v3"})
    assert fallback["timeout"] == 1800.0

    monkeypatch.setenv("ATLASCLOUD_REQUEST_TIMEOUT", "2400")
    override = AtlasCloudChat.resolve_atlascloud_env({"model": "deepseek-v3"})
    assert override["timeout"] == 2400.0

    monkeypatch.setenv("ATLASCLOUD_REQUEST_TIMEOUT", "420")
    clamped = AtlasCloudChat.resolve_atlascloud_env({"model": "deepseek-v3"})
    assert clamped["timeout"] == 1800.0

    monkeypatch.delenv("ATLASCLOUD_API_KEY", raising=False)
    monkeypatch.setenv("ATLAS_CLOUD_API_KEY", "fallback-key")
    monkeypatch.setenv("ATLAS_CLOUD_API_BASE", "https://fallback.example/v1")
    fallback = AtlasCloudChat.resolve_atlascloud_env({"model": "deepseek-v3"})
    assert fallback["api_key"] == "fallback-key"
    assert fallback["base_url"] == "https://fallback.example/v1"


def test_tongyi_and_wenxin_default_params_should_merge_extension_fields(monkeypatch):
    monkeypatch.setattr(
        "langchain_community.chat_models.tongyi.ChatTongyi._default_params",
        property(lambda _self: {"base": True}),
    )
    monkeypatch.setattr(
        "langchain_community.chat_models.baidu_qianfan_endpoint.QianfanChatEndpoint._default_params",
        property(lambda _self: {"base": True}),
    )

    tongyi = TongyiChat.model_construct(
        temperature=0.5,
        max_tokens=128,
        presence_penalty=0.2,
        frequency_penalty=0.1,
        enable_search=True,
    )
    params = tongyi._default_params
    assert params["temperature"] == 0.5
    assert params["max_tokens"] == 128
    assert params["presence_penalty"] == 0.2
    assert params["frequency_penalty"] == 0.1
    assert params["enable_search"] is True

    wenxin = WenxinChat.model_construct(max_output_tokens=512, disable_search=True)
    wenxin_params = wenxin._default_params
    assert wenxin_params["max_output_tokens"] == 512
    assert wenxin_params["disable_search"] is True

    # 覆盖所有扩展字段为 None 时的分支（不追加参数）。
    tongyi_none = TongyiChat.model_construct(
        temperature=None,
        max_tokens=None,
        presence_penalty=None,
        frequency_penalty=None,
        enable_search=None,
    )
    assert tongyi_none._default_params == {"base": True}

    wenxin_none = WenxinChat.model_construct(
        max_output_tokens=None, disable_search=None
    )
    assert wenxin_none._default_params == {"base": True}


def test_moonshot_encoding_model_should_force_gpt35(monkeypatch):
    monkeypatch.setattr(
        "internal.core.language_model.providers.moonshot.chat.tiktoken.encoding_for_model",
        lambda model: f"encoding:{model}",
    )
    moonshot = object.__new__(MoonshotChat)

    model, encoding = MoonshotChat._get_encoding_model(moonshot)

    assert model == "gpt-3.5-turbo"
    assert encoding == "encoding:gpt-3.5-turbo"


def test_default_timeout_helper_should_fallback_when_env_is_empty(monkeypatch):
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT", "")

    from internal.core.language_model.providers._defaults import (
        apply_default_model_timeout,
    )

    resolved = apply_default_model_timeout({})

    assert resolved["timeout"] == 120.0
