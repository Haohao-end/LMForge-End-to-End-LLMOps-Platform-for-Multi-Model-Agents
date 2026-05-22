from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class McpProviderEntity(BaseModel):
    """MCP 提供者实体，对应公开目录或用户配置的单个 MCP。"""

    name: str
    label: str
    description: str
    icon: str = ""
    background: str = ""
    category: str = "other"
    transport: str = "streamable_http"
    url: str = ""
    command: str = ""
    headers: list[dict[str, str]] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30
    source_type: str = "catalog"
    source_key: str = ""
    source_url: str = ""
    created_at: int = 0
    is_public: bool = True


class McpCatalogProvider(BaseModel):
    """MCP 目录提供者包装体。"""

    name: str
    position: int
    provider_entity: McpProviderEntity
    tool_entity_map: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(protected_namespaces=())

