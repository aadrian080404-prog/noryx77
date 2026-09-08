from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import html
import re
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ResearchSource:
    url: str
    title: str
    snippet: str
    retrieved_at: str
    status: str


class WebResearchEngine:
    MAX_RESULTS = 5
    MAX_BYTES = 750_000
    TIMEOUT = 8
    TRIGGERS = (
        "latest", "today", "current", "recent", "news", "research", "source", "sources",
        "evidence", "verify", "internet", "web", "online", "live", "prezzo", "price",
        "mercato", "normativa",
    )

    def should_research(self, task) -> bool:
        text = " ".join(str(x or "") for x in (getattr(task, "objective", ""), getattr(task, "input", ""))).lower()
        return any(trigger in text for trigger in self.TRIGGERS)

    def _fetch(self, query: str) -> str:
        request = Request(
            "https://html.duckduckgo.com/html/?q=" + quote(query, safe=""),
            headers={"User-Agent": "NORYX7/1.0 research"},
        )
        with urlopen(request, timeout=self.TIMEOUT) as response:
            data = response.read(self.MAX_BYTES + 1)
        if len(data) > self.MAX_BYTES:
            raise ValueError("research_response_limit_exceeded")
        return data.decode("utf-8", "replace")

    def search(self, query: str) -> tuple[ResearchSource, ...]:
        try:
            page = self._fetch(query)
        except Exception:
            return ()
        now = datetime.now(timezone.utc).isoformat()
        results = []
        pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
        for match in pattern.finditer(page):
            href, raw_title = match.groups()
            title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
            chunk = page[match.end():match.end() + 2500]
            snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', chunk, re.I | re.S)
            snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_match.group(1) if snippet_match else "")).strip()
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = urljoin("https://html.duckduckgo.com", href)
            if not href.startswith("http") or not title:
                continue
            results.append(ResearchSource(href, title[:300], snippet[:600], now, "retrieved"))
            if len(results) >= self.MAX_RESULTS:
                break
        return tuple(results)

    def run(self, task) -> dict:
        if not self.should_research(task):
            return {"enabled": False, "query": None, "sources": (), "status": "not_needed"}
        query = f"{getattr(task, 'objective', '')} {getattr(task, 'input', '')}".strip()[:1000]
        sources = self.search(query)
        return {
            "enabled": True,
            "query": query,
            "sources": tuple(asdict(source) for source in sources),
            "status": "ok" if sources else "unavailable",
        }
