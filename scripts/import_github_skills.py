from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import yaml


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text.strip()

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break

    if end_index is None:
        return {}, text.strip()

    frontmatter_text = "\n".join(lines[1:end_index]).strip()
    body = "\n".join(lines[end_index + 1 :]).strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except Exception:
        frontmatter = {}
    if not isinstance(frontmatter, dict):
        frontmatter = {}
    return frontmatter, body


def _infer_category(skill_name: str) -> str:
    if skill_name.startswith(("gh-", "git")):
        return "GitHub"
    if skill_name.startswith("figma"):
        return "设计"
    if skill_name.startswith("notion"):
        return "协作"
    if skill_name.startswith("security"):
        return "安全"
    if skill_name.endswith("-deploy") or skill_name in {"render-deploy"}:
        return "部署"
    if skill_name in {"speech", "transcribe"}:
        return "多媒体"
    if skill_name in {"pdf", "screenshot", "playwright", "playwright-interactive", "jupyter-notebook"}:
        return "内容处理"
    if skill_name in {"cli-creator", "migrate-to-codex", "openai-docs", "aspnet-core", "chatgpt-apps", "linear", "sentry", "yeet"}:
        return "开发"
    return "GitHub"


def _build_manifest(skill_name: str, frontmatter: dict[str, Any], body: str) -> dict[str, Any]:
    display_name = str(frontmatter.get("name") or skill_name).strip()
    description = str(frontmatter.get("description") or body.splitlines()[0] if body.splitlines() else "").strip()
    return {
        "source_key": skill_name,
        "name": display_name,
        "label": display_name,
        "description": description,
        "category": _infer_category(skill_name),
        "tags": ["github", "curated", "skill-md"],
        "icon": "",
        "enabled": True,
        "version": 1,
        "executor_type": "prompt",
        "capabilities": {},
        "tools": [],
    }


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def import_skill(source_root: Path, dest_root: Path, skill_name: str) -> None:
    source_dir = source_root / skill_name
    if not source_dir.exists():
        raise FileNotFoundError(f"source skill not found: {source_dir}")

    skill_md_path = source_dir / "SKILL.md"
    if not skill_md_path.exists():
        raise FileNotFoundError(f"SKILL.md not found: {skill_md_path}")

    frontmatter, body = _split_frontmatter(skill_md_path.read_text(encoding="utf-8"))
    manifest = _build_manifest(skill_name, frontmatter, body)

    dest_dir = dest_root / skill_name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    (dest_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (dest_dir / "skill.md").write_text(body + "\n", encoding="utf-8")

    # Keep the original upstream file for provenance/debugging.
    shutil.copy2(skill_md_path, dest_dir / "SKILL.md")

    for extra_name in ("agents", "assets", "scripts"):
        extra_dir = source_dir / extra_name
        if extra_dir.exists():
            shutil.copytree(extra_dir, dest_dir / extra_name, dirs_exist_ok=True)

    license_path = source_dir / "LICENSE.txt"
    if license_path.exists():
        shutil.copy2(license_path, dest_dir / "LICENSE.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import GitHub SKILL.md packages into the local catalog format.")
    parser.add_argument("--source-root", required=True, help="Path to the upstream skills directory")
    parser.add_argument("--dest-root", required=True, help="Local catalog directory")
    parser.add_argument("--skill", action="append", required=True, help="Skill directory name to import")
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    dest_root = Path(args.dest_root).resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    for skill_name in args.skill:
        import_skill(source_root, dest_root, skill_name.strip())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
