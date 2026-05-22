"""网页研究技能包的可执行实现。"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(text)).strip()


def _fetch_url(url: str, timeout: int = 15) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="ignore")


class _DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._capture = False
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        class_value = attrs_dict.get("class", "")
        if "result__a" in class_value:
            self._capture = True
            self._current_href = attrs_dict.get("href", "")
            self._current_text = []

    def handle_data(self, data: str):
        if self._capture:
            self._current_text.append(data)

    def handle_endtag(self, tag: str):
        if tag != "a" or not self._capture:
            return
        title = _normalize_text("".join(self._current_text))
        href = _normalize_text(self._current_href)
        if title and href:
            self.results.append(
                {
                    "title": title,
                    "url": _normalize_text(_decode_search_url(href)),
                }
            )
        self._capture = False
        self._current_href = ""
        self._current_text = []


def _decode_search_url(url: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    if "uddg" in query_params:
        return unquote(query_params["uddg"][0])
    if url.startswith("//"):
        return f"https:{url}"
    return url


def search_web(params: dict[str, Any]) -> dict[str, Any]:
    query = _normalize_text(params.get("query", ""))
    if not query:
        return {"query": "", "results": []}

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html_text = _fetch_url(search_url)
    parser = _DuckDuckGoResultParser()
    parser.feed(html_text)

    results = parser.results[:5]
    if not results:
        results = [{"title": query, "url": search_url}]

    return {
        "query": query,
        "results": results,
    }


def summarize_sources(params: dict[str, Any]) -> dict[str, Any]:
    sources = params.get("sources", [])
    prompt = _normalize_text(params.get("prompt", ""))
    if not isinstance(sources, list):
        sources = []

    summaries: list[str] = []
    normalized_sources: list[str] = []
    for source in sources:
        source_text = _normalize_text(source)
        if not source_text:
            continue
        normalized_sources.append(source_text)
        if source_text.startswith(("http://", "https://")):
            try:
                page_html = _fetch_url(source_text)
                title_match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.IGNORECASE | re.DOTALL)
                title = _strip_html_tags(title_match.group(1)) if title_match else source_text
                text = _strip_html_tags(page_html)
                snippet = text[:240]
                summaries.append(f"- {title}: {snippet}")
            except Exception as exc:
                summaries.append(f"- {source_text}: 无法抓取内容（{exc}）")
        else:
            summaries.append(f"- {source_text}")

    summary_text = "；".join(summaries) if summaries else "没有可总结的来源。"
    if prompt:
        summary_text = f"{summary_text} 关注点：{prompt}。"

    return {
        "source_count": len(normalized_sources),
        "prompt": prompt,
        "summary": summary_text,
        "sources": normalized_sources,
    }
