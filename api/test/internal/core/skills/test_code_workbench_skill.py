from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[4] / "internal/core/skills/catalog/code_workbench/skill.py"
    spec = importlib.util.spec_from_file_location("code_workbench_skill", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_code_workbench_skill_should_analyze_and_generate_patch():
    module = _load_module()

    analysis = module.analyze_request({"request": "为当前页面补充只读 Markdown 详情"})
    assert analysis["summary"] == "为当前页面补充只读 Markdown 详情"
    assert analysis["next_steps"]

    patch_result = module.generate_patch(
        {
            "request": "修改技能页",
            "context": "app/src/views/SkillPage.vue\nREADME.md",
        }
    )
    assert patch_result["request"] == "修改技能页"
    assert "SkillPage.vue" in patch_result["patch_hint"] or "README.md" in patch_result["patch_hint"]
