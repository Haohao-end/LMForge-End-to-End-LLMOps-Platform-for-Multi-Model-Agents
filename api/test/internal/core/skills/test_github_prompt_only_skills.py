from __future__ import annotations

from internal.core.skills.skill_catalog import SkillCatalogManager


def test_github_prompt_only_skills_are_loaded_and_remain_prompt_only():
    manager = SkillCatalogManager()
    packages = {package.source_key: package for package in manager.list_packages()}

    expected_keys = {
        "caveman",
        "handoff",
        "triage",
        "zoom-out",
        "setup-pre-commit",
        "scaffold-exercises",
        "migrate-to-shoehorn",
        "migrate-to-codex",
        "git-guardrails-claude-code",
        "qa-only",
        "diagnose",
        "grill-with-docs",
        "grill-me",
        "to-issues",
        "to-prd",
        "improve-codebase-architecture",
        "tdd",
        "write-a-skill",
        "setup-matt-pocock-skills",
        "find-skills",
        "frontend-skill",
        "develop-web-game",
        "figma-implement-design",
        "frontend-design",
        "creative",
    }

    assert expected_keys.issubset(packages.keys())
    assert len(packages) >= 50

    for key in expected_keys:
        package = packages[key]
        assert package.executor_type == "prompt"
        assert package.tools == []
        assert package.readme
