from internal.core.skills.skill_catalog import SkillCatalogManager


def test_github_curated_skills_should_load_and_hide_examples():
    packages = SkillCatalogManager().list_packages()
    enabled_packages = [package for package in packages if package.enabled]
    enabled_source_keys = {package.source_key for package in enabled_packages}

    assert len(enabled_packages) >= 27
    assert "code_workbench" in enabled_source_keys
    assert "web_research" in enabled_source_keys
    assert any(package.readme.strip() for package in enabled_packages)

    executable_packages = {
        package.source_key: package
        for package in enabled_packages
        if package.executor_type.lower() == "scf" and package.tools
    }
    assert "code_workbench" in executable_packages
    assert "web_research" in executable_packages
