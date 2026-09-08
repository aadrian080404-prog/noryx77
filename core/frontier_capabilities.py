from __future__ import annotations

import os
import re
import ssl
from html import unescape
from urllib.parse import parse_qs, quote_plus, urlsplit
from urllib.request import Request, urlopen


class CapabilityUnavailable(RuntimeError):
    pass


class WebResearchCapability:
    name = "web_research"

    def __init__(self, *, timeout: float = 10.0, max_bytes: int = 256_000):
        self.timeout = timeout
        self.max_bytes = max_bytes

    def __call__(self, target: str, parameters: dict) -> dict:
        query = str(parameters.get("query") or target or "").strip()
        url = str(parameters.get("url") or "").strip()
        if url:
            return self._fetch(url)
        if not query:
            raise ValueError("web_research_requires_query_or_url")
        template = os.environ.get("NORYX7_SEARCH_URL_TEMPLATE", "https://html.duckduckgo.com/html/?q={query}")
        search_url = template.format(query=quote_plus(query))
        page = self._fetch(search_url)
        links = []
        for href, title in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', page.get("body", ""), re.I | re.S):
            clean_title = re.sub(r"<[^>]+>", " ", unescape(title)).strip()
            if clean_title and href.startswith("http"):
                links.append({"title": clean_title[:300], "url": href[:1000]})
        return {"status": "completed", "query": query, "source": search_url, "results": links[:10]}

    def _fetch(self, url: str) -> dict:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("web_research_https_url_required")
        req = Request(url, headers={"User-Agent": "NORYX7/1.0 frontier-research"})
        context = ssl.create_default_context()
        with urlopen(req, timeout=self.timeout, context=context) as response:
            data = response.read(self.max_bytes + 1)
            if len(data) > self.max_bytes:
                raise ValueError("web_response_limit_exceeded")
            content_type = response.headers.get("Content-Type", "")
            return {
                "status": "completed",
                "url": response.geturl(),
                "status_code": getattr(response, "status", 200),
                "content_type": content_type,
                "body": data.decode("utf-8", "replace"),
            }


class ChessCapability:
    name = "chess_analyze"

    def __call__(self, target: str, parameters: dict) -> dict:
        try:
            import chess
        except ImportError as exc:
            raise CapabilityUnavailable("python_chess_required") from exc
        fen = str(parameters.get("fen") or "").strip()
        board = chess.Board(fen) if fen else chess.Board()
        move = parameters.get("move")
        if move:
            move = str(move).strip()
            try:
                parsed = board.parse_san(move)
            except Exception:
                try:
                    parsed = chess.Move.from_uci(move)
                except Exception as exc:
                    raise ValueError("invalid_chess_move") from exc
            if not board.is_legal(parsed):
                raise ValueError("illegal_chess_move")
            return {
                "status": "completed",
                "fen": board.fen(),
                "move": parsed.uci(),
                "legal": True,
                "check": board.gives_check(parsed),
                "checkmate": board.gives_checkmate(parsed),
            }
        legal = [m.uci() for m in board.legal_moves]
        return {
            "status": "completed",
            "fen": board.fen(),
            "legal_move_count": len(legal),
            "legal_moves": legal[:100],
            "check": board.is_check(),
            "checkmate": board.is_checkmate(),
            "stalemate": board.is_stalemate(),
        }


class ExternalProviderCapability:
    def __init__(self, name: str, env_prefix: str):
        self.name = name
        self.env_prefix = env_prefix

    def __call__(self, target: str, parameters: dict) -> dict:
        endpoint = os.environ.get(self.env_prefix + "_ENDPOINT", "").strip()
        token = os.environ.get(self.env_prefix + "_TOKEN", "").strip()
        if not endpoint or not token:
            raise CapabilityUnavailable(f"{self.name}_provider_not_configured")
        raise CapabilityUnavailable(f"{self.name}_provider_adapter_requires_explicit_operation_contract")


def install_frontier_capabilities(tool_executor) -> tuple[str, ...]:
    """Install only concrete capability handlers; external providers remain fail-closed."""
    tool_executor.capabilities.register("web_research", WebResearchCapability(), risk_class="normal")
    tool_executor.capabilities.register("chess_analyze", ChessCapability(), risk_class="normal")
    tool_executor.capabilities.register("payments", ExternalProviderCapability("payments", "NORYX7_PAYMENTS"), risk_class="high")
    tool_executor.capabilities.register("flights", ExternalProviderCapability("flights", "NORYX7_FLIGHTS"), risk_class="high")
    tool_executor.capabilities.register("insurance", ExternalProviderCapability("insurance", "NORYX7_INSURANCE"), risk_class="high")
    return tool_executor.capabilities.names()
