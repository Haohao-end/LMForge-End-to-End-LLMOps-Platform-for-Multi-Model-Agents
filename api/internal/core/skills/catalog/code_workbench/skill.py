"""代码工坊技能包的可执行实现。"""

from __future__ import annotations

from typing import Any
import re


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _split_keywords(text: str) -> list[str]:
    return [token for token in re.split(r"[\s,，。;；:/\\|]+", text) if token]


def analyze_request(params: dict[str, Any]) -> dict[str, Any]:
    request = _normalize_text(params.get("request", ""))
    keywords = _split_keywords(request)
    next_steps = [
        "确认输入输出边界",
        "定位涉及文件与模块",
        "先给出最小修改方案",
    ]
    if any(token in request for token in ("补丁", "修改", "修复", "实现")):
        next_steps.append("拆分成可审查的代码变更")
    if any(token in request for token in ("测试", "单测", "test")):
        next_steps.append("补充或更新测试用例")

    return {
        "summary": request or "未提供明确需求",
        "next_steps": next_steps,
        "keywords": keywords[:8],
    }


def generate_patch(params: dict[str, Any]) -> dict[str, Any]:
    request = _normalize_text(params.get("request", ""))
    context = _normalize_text(params.get("context", ""))
    file_hints = []
    for line in context.splitlines():
        candidate = line.strip()
        if candidate.endswith((".py", ".ts", ".tsx", ".vue", ".js", ".json", ".yaml", ".yml", ".md")):
            file_hints.append(candidate)

    patch_hint = "先定位目标文件，再做最小化修改，并补充测试。"
    if file_hints:
        unique_files = list(dict.fromkeys(file_hints))[:5]
        patch_hint = f"优先修改这些文件: {', '.join(unique_files)}。"

    return {
        "request": request,
        "context": context,
        "patch_hint": patch_hint,
    }
