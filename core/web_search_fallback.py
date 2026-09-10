from __future__ import annotations


class WebSearchFallback:
    """Optional metasearch fallback kept behind a small, explicit contract."""

    def __init__(self, timeout: float = 10.0, max_results: int = 10):
        self.timeout = timeout
        self.max_results = max_results

    def search(self, query: str) -> list[dict]:
        try:
            from ddgs import DDGS
        except ImportError:
            return []
        try:
            raw = DDGS(timeout=self.timeout).text(query, max_results=self.max_results)
        except Exception:
            return []
        results = []
        for item in raw or []:
            url = str(item.get("href") or item.get("url") or "").strip()
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("body") or item.get("snippet") or "").strip()
            if url and title:
                results.append({
                    "title": title[:300],
                    "url": url[:1000],
                    "snippet": snippet[:600],
                })
        return results[: self.max_results]
