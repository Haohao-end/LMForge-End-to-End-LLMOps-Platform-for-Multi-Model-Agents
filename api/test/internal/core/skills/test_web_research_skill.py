from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[4] / "internal/core/skills/catalog/web_research/skill.py"
    spec = importlib.util.spec_from_file_location("web_research_skill", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_research_skill_should_parse_search_results_and_summaries(monkeypatch):
    module = _load_module()

    search_html = """
    <html>
      <body>
        <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fa">结果 A</a>
        <a class="result__a" href="https://example.com/b">结果 B</a>
      </body>
    </html>
    """

    def _fake_fetch(url, timeout=15):
        if "duckduckgo" in url:
            return search_html
        return "<html><head><title>示例标题</title></head><body><p>第一段内容</p></body></html>"

    monkeypatch.setattr(module, "_fetch_url", _fake_fetch)

    search_result = module.search_web({"query": "skills"})
    assert search_result["query"] == "skills"
    assert len(search_result["results"]) == 2
    assert search_result["results"][0]["title"] == "结果 A"
    assert search_result["results"][0]["url"] == "https://example.com/a"

    summary_result = module.summarize_sources(
        {"sources": ["https://example.com/page"], "prompt": "提炼结论"}
    )
    assert summary_result["source_count"] == 1
    assert "示例标题" in summary_result["summary"]
    assert "提炼结论" in summary_result["summary"]
