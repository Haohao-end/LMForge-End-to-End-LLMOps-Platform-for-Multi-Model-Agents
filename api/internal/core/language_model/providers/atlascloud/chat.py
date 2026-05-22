import os
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import model_validator

from internal.core.language_model.entities.model_entity import BaseLanguageModel
from internal.core.language_model.providers._defaults import apply_default_model_timeout


class Chat(ChatOpenAI, BaseLanguageModel):
    """Atlas Cloud 聊天模型（OpenAI 兼容接口）。"""

    @model_validator(mode="before")
    @classmethod
    def resolve_atlascloud_env(cls, values: Any) -> Any:
        """Resolve Atlas Cloud credentials and endpoint from env when omitted."""
        if not isinstance(values, dict):
            return values

        resolved = dict(values)

        if not resolved.get("api_key") and not resolved.get("openai_api_key"):
            key = (
                os.getenv("ATLAS_CLOUD_API_KEY", "")
                or os.getenv("ATLASCLOUD_API_KEY", "")
            )
            if key:
                resolved["api_key"] = key

        if not resolved.get("base_url") and not resolved.get("openai_api_base"):
            base = (
                os.getenv("ATLAS_CLOUD_API_BASE", "")
                or os.getenv("ATLASCLOUD_API_BASE", "")
                or "https://api.atlascloud.ai/v1"
            )
            if base:
                resolved["base_url"] = base

        # Align with the ai-hands-on Atlas preset so local env can swap models
        # without changing the checked-in provider yaml.
        env_model = os.getenv("ATLAS_CLOUD_MODEL", "") or os.getenv(
            "ATLASCLOUD_MODEL", ""
        )
        if env_model:
            resolved["model"] = env_model

        apply_default_model_timeout(resolved)
        return resolved
