import os.path
from typing import Any

import yaml
from injector import inject, singleton
from pydantic import BaseModel, Field

from internal.core.tools.mcp_tools.entities import McpCatalogProvider, McpProviderEntity


@inject
@singleton
class McpProviderManager(BaseModel):
    """MCP 目录管理器，加载魔搭社区公开 MCP 目录。"""

    provider_map: dict[str, McpCatalogProvider] = Field(default_factory=dict)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._get_provider_map()

    def get_provider(self, provider_name: str) -> McpCatalogProvider | None:
        return self.provider_map.get(provider_name)

    def get_providers(self) -> list[McpCatalogProvider]:
        return list(self.provider_map.values())

    def _get_provider_map(self):
        if self.provider_map:
            return

        current_path = os.path.abspath(__file__)
        providers_path = os.path.dirname(current_path)
        providers_yaml_path = os.path.join(providers_path, "providers.yaml")

        with open(providers_yaml_path, encoding="utf-8") as f:
            providers_yaml_data = yaml.safe_load(f) or []

        for idx, provider_data in enumerate(providers_yaml_data):
            provider_entity = McpProviderEntity(**provider_data)
            self.provider_map[provider_entity.name] = McpCatalogProvider(
                name=provider_entity.name,
                position=idx + 1,
                provider_entity=provider_entity,
            )
