"""Lawful scientific-source discovery adapters.

These adapters retrieve public metadata/abstract records from documented APIs.
They never bypass access controls, paywalls, or licensing restrictions and never
turn a source into execution authority.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .scientific_knowledge import ResearchSource


class ScientificSourceError(RuntimeError):
    pass


class _HTTPSource:
    def __init__(self, *, timeout_seconds: float = 10.0):
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("invalid_source_timeout")
        self.timeout_seconds = float(timeout_seconds)

    def _get(self, url: str, *, accept: str) -> bytes:
        request = Request(url, headers={"Accept": accept, "User-Agent": "NORYX7/1.0 scientific-research-client"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except Exception as exc:
            raise ScientificSourceError("scientific_source_request_failed") from exc


class PubMedSourceProvider(_HTTPSource):
    """Discover PubMed records through NCBI E-utilities metadata APIs."""

    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    def __init__(self, *, email: str, tool: str = "noryx7", api_key: str | None = None, timeout_seconds: float = 10.0):
        super().__init__(timeout_seconds=timeout_seconds)
        if not isinstance(email, str) or "@" not in email:
            raise ValueError("pubmed_email_required")
        self.email = email
        self.tool = tool
        self.api_key = api_key

    def search(self, query: str, *, retmax: int = 8) -> tuple[ResearchSource, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("research_query_required")
        if isinstance(retmax, bool) or not isinstance(retmax, int) or not 1 <= retmax <= 50:
            raise ValueError("invalid_research_result_limit")
        params = {"db": "pubmed", "term": query.strip(), "retmax": str(retmax), "retmode": "json", "tool": self.tool, "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        payload = json.loads(self._get(self.BASE + "esearch.fcgi?" + urlencode(params), accept="application/json"))
        ids = tuple(str(value) for value in payload.get("esearchresult", {}).get("idlist", ()))
        if not ids:
            return ()
        summary_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": self.tool, "email": self.email}
        if self.api_key:
            summary_params["api_key"] = self.api_key
        summary = json.loads(self._get(self.BASE + "esummary.fcgi?" + urlencode(summary_params), accept="application/json"))
        result = summary.get("result", {})
        sources = []
        for pmid in ids:
            item = result.get(pmid, {})
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            sources.append(ResearchSource(
                source_id=f"pubmed:{pmid}",
                title=title,
                discipline="medicine",
                source_type="pubmed",
                uri=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                access_status="metadata_only",
                license="provider_terms",
            ))
        return tuple(sources)


class ArxivSourceProvider(_HTTPSource):
    """Discover arXiv metadata through its public API."""

    BASE = "https://export.arxiv.org/api/query"

    def search(self, query: str, *, max_results: int = 8) -> tuple[ResearchSource, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("research_query_required")
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 50:
            raise ValueError("invalid_research_result_limit")
        params = urlencode({"search_query": f"all:{query.strip()}", "start": 0, "max_results": max_results})
        root = ElementTree.fromstring(self._get(self.BASE + "?" + params, accept="application/atom+xml"))
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        sources = []
        for entry in root.findall("atom:entry", ns):
            entry_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            title = " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split())
            summary = " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split())
            if not entry_id or not title:
                continue
            source_id = "arxiv:" + entry_id.rstrip("/").rsplit("/", 1)[-1]
            sources.append(ResearchSource(source_id, title, "interdisciplinary", "preprint", entry_id, "authorized", "arxiv_terms", summary, ResearchSource.digest_content(summary) if summary else ""))
        return tuple(sources)


class CrossrefSourceProvider(_HTTPSource):
    """Discover scholarly metadata through Crossref's public REST API."""

    BASE = "https://api.crossref.org/works"

    def search(self, query: str, *, rows: int = 8) -> tuple[ResearchSource, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("research_query_required")
        if isinstance(rows, bool) or not isinstance(rows, int) or not 1 <= rows <= 50:
            raise ValueError("invalid_research_result_limit")
        params = urlencode({"query.bibliographic": query.strip(), "rows": rows})
        payload = json.loads(self._get(self.BASE + "?" + params, accept="application/json"))
        items = payload.get("message", {}).get("items", ())
        sources = []
        for item in items:
            doi = str(item.get("DOI", "")).strip()
            title_values = item.get("title") or ()
            title = str(title_values[0]).strip() if title_values else ""
            if not doi or not title:
                continue
            sources.append(ResearchSource(
                source_id=f"crossref:{doi}",
                title=title,
                discipline="interdisciplinary",
                source_type="journal_metadata",
                uri=f"https://doi.org/{doi}",
                access_status="metadata_only",
                license="provider_terms",
            ))
        return tuple(sources)
