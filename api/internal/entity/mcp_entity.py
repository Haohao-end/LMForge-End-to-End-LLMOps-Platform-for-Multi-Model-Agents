from __future__ import annotations

from enum import Enum
from typing import Any


class McpSourceType(str, Enum):
    """MCP 来源类型。"""

    CATALOG = "catalog"
    CUSTOM = "custom"


MCP_CATEGORY_OPTIONS: list[dict[str, Any]] = [
    {
        "id": "general",
        "name": "通用",
        "priority": 1,
        "background": "#DBEAFE",
    },
    {
        "id": "productivity",
        "name": "效率工具",
        "priority": 2,
        "background": "#DCFCE7",
    },
    {
        "id": "coding",
        "name": "编程工具",
        "priority": 3,
        "background": "#E0E7FF",
    },
    {
        "id": "content_creation",
        "name": "内容创作",
        "priority": 4,
        "background": "#FEE2E2",
    },
    {
        "id": "media",
        "name": "媒体音视频",
        "priority": 5,
        "background": "#FCE7F3",
    },
    {
        "id": "data_analysis",
        "name": "数据分析",
        "priority": 6,
        "background": "#EDE9FE",
    },
    {
        "id": "observability",
        "name": "可观测运维",
        "priority": 7,
        "background": "#FEF3C7",
    },
    {
        "id": "other",
        "name": "其他",
        "priority": 99,
        "background": "#E5E7EB",
    },
]

MCP_CATEGORY_MAP = {item["id"]: item for item in MCP_CATEGORY_OPTIONS}

MCP_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "content_creation": [
        "图片",
        "生图",
        "文生图",
        "内容创作",
        "视频",
        "剪辑",
        "发布",
        "小红书",
        "创作",
    ],
    "media": [
        "语音",
        "音频",
        "字幕",
        "变声",
        "配音",
        "TTS",
        "ASR",
        "视频翻译",
    ],
    "observability": [
        "日志",
        "链路",
        "监控",
        "可观测",
        "SLS",
        "ARMS",
        "观测",
    ],
    "coding": [
        "代码",
        "编程",
        "开发",
        "调试",
        "重构",
        "API",
        "SQL",
        "Python",
    ],
    "data_analysis": [
        "数据",
        "分析",
        "报表",
        "统计",
        "BI",
        "仪表盘",
        "查询",
    ],
    "productivity": [
        "效率",
        "自动化",
        "工作流",
        "任务",
        "管理",
        "搜索",
        "整理",
    ],
}


def normalize_mcp_transport(transport: Any) -> str:
    """归一化 MCP transport。"""
    normalized = str(transport or "").strip().lower()
    if normalized in {"streamable-http", "streamable_http"}:
        return "streamable_http"
    return normalized


def normalize_mcp_category(category: Any, *, name: str = "", description: str = "") -> str:
    """归一化 MCP 分类。"""
    normalized = str(category or "").strip().lower()
    if normalized in MCP_CATEGORY_MAP:
        return normalized

    combined_text = f"{name} {description}".lower()
    for category_id, keywords in MCP_CATEGORY_KEYWORDS.items():
        if any(keyword.lower() in combined_text for keyword in keywords):
            return category_id

    return "other"


def get_mcp_category_meta(category: Any) -> dict[str, Any]:
    """获取 MCP 分类元信息。"""
    normalized_category = normalize_mcp_category(category)
    return MCP_CATEGORY_MAP.get(normalized_category, MCP_CATEGORY_MAP["other"])

