import os
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import model_validator

from internal.core.language_model.entities.model_entity import BaseLanguageModel
from internal.core.language_model.providers._defaults import apply_default_model_timeout


def _resolve_atlascloud_timeout(default: float = 1800.0) -> float:
    """Resolve Atlas Cloud timeout with a generous floor for long-running agent tasks."""
    for env_name in ("ATLASCLOUD_REQUEST_TIMEOUT", "ATLAS_CLOUD_REQUEST_TIMEOUT", "LLM_REQUEST_TIMEOUT"):
        raw_value = str(os.getenv(env_name, "")).strip()
        if not raw_value:
            continue
        try:
            return max(float(raw_value), default)
        except (TypeError, ValueError):
            continue
    return default


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
            key = os.getenv("ATLASCLOUD_API_KEY", "") or os.getenv("ATLAS_CLOUD_API_KEY", "")
            if key:
                resolved["api_key"] = key

        if not resolved.get("base_url") and not resolved.get("openai_api_base"):
            base = (
                os.getenv("ATLASCLOUD_API_BASE", "")
                or os.getenv("ATLAS_CLOUD_API_BASE", "")
                or "https://api.atlascloud.ai/v1"
            )
            if base:
                resolved["base_url"] = base

        if not resolved.get("timeout") and not resolved.get("request_timeout"):
            resolved["timeout"] = _resolve_atlascloud_timeout()

        apply_default_model_timeout(resolved)
        return resolved
