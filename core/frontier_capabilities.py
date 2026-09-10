from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
from html.parser import HTMLParser
from html import unescape
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit
from urllib.request import Request, urlopen


class CapabilityUnavailable(RuntimeError):
    pass


class _SearchResultParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self._anchor = False
        self._href = ""
        self._text = []
        self._snippet = False
        self._snippet_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(str(attrs.get("class") or "").split())
        if "result__a" in classes and tag.lower() == "a":
            self._anchor = True
            self._href = str(attrs.get("href") or "")
            self._text = []
        if "result__snippet" in classes:
            self._snippet = True
            self._snippet_text = []

    def handle_data(self, data):
        if self._anchor:
            self._text.append(data)
        if self._snippet:
            self._snippet_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor:
            self.results.append({"title": "".join(self._text), "url": self._href, "snippet": ""})
            self._anchor = False
        if self._snippet and tag.lower() in {"a", "div", "span"}:
            snippet = " ".join(self._snippet_text).strip()
            for item in reversed(self.results):
                if not item.get("snippet"):
                    item["snippet"] = snippet
                    break
            self._snippet = False


class WebResearchCapability:
    name = "web_research"

    def __init__(self, *, timeout: float = 10.0, max_bytes: int = 256_000):
        self.timeout = timeout
        self.max_bytes = max_bytes

    @staticmethod
    def _clean_text(value: str, *, limit: int = 1000) -> str:
        text = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", value or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:limit]

    @staticmethod
    def _source_title(body: str, fallback: str) -> str:
        match = re.search(r"(?is)<title[^>]*>(.*?)</title>", body or "")
        title = WebResearchCapability._clean_text(match.group(1), limit=300) if match else ""
        return title or fallback

    @staticmethod
    def _resolve_search_url(href: str) -> str:
        value = unescape(str(href or "").strip())
        if value.startswith("//"):
            value = "https:" + value
        if value.startswith("/"):
            parsed = urlsplit("https://duckduckgo.com" + value)
        else:
            parsed = urlsplit(value)
        redirected = parse_qs(parsed.query).get("uddg")
        if redirected:
            try:
                value = unquote(redirected[0])
            except Exception:
                return ""
        return value if value.startswith("https://") else ""

    @staticmethod
    def _parse_results(body: str) -> list[dict]:
        parser = _SearchResultParser()
        try:
            parser.feed(body or "")
            parser.close()
        except Exception:
            return []
        results = []
        seen = set()
        for item in parser.results:
            title = WebResearchCapability._clean_text(item.get("title", ""), limit=300)
            url = WebResearchCapability._resolve_search_url(item.get("url", ""))
            snippet = WebResearchCapability._clean_text(item.get("snippet", ""), limit=600)
            if not title or not url or url in seen:
                continue
            seen.add(url)
            results.append({"title": title, "url": url[:1000], "snippet": snippet})
        return results[:10]

    def __call__(self, target: str, parameters: dict) -> dict:
        target_value = str(target or "").strip()
        explicit_url = str(parameters.get("url") or "").strip()
        if explicit_url:
            return self._fetch(explicit_url)
        if target_value.startswith(("http://", "https://")):
            return self._fetch(target_value)
        query = str(parameters.get("query") or target_value).strip()
        if not query:
            raise ValueError("web_research_requires_query_or_url")

        templates = []
        configured = os.environ.get("NORYX7_SEARCH_URL_TEMPLATE", "").strip()
        if configured:
            templates.append(configured)
        templates.extend([
            "https://html.duckduckgo.com/html/?q={query}",
            "https://html.duckduckgo.com/lite/?q={query}",
        ])

        for template in dict.fromkeys(templates):
            search_url = template.format(query=quote_plus(query))
            try:
                page = self._fetch(search_url)
            except Exception:
                continue
            links = self._parse_results(page.get("body", ""))
            if links:
                return self._build_result(query, page["url"], links)

        try:
            from core.web_search_fallback import WebSearchFallback
            links = WebSearchFallback(timeout=self.timeout).search(query)
        except Exception:
            links = []
        if links:
            return self._build_result(query, "metasearch", links)
        raise CapabilityUnavailable("web_search_provider_unavailable")

    def _build_result(self, query: str, source_url: str, links: list[dict]) -> dict:
        evidence = []
        for item in links[:10]:
            snippet = str(item.get("snippet") or "").strip()
            if not snippet:
                try:
                    source = self._fetch(item["url"])
                except Exception:
                    continue
                source_body = source.get("body", "")
                snippet = self._clean_text(source_body)
                if not snippet:
                    continue
                evidence.append({
                    "url": source["url"],
                    "title": self._source_title(source_body, item["title"]),
                    "snippet": snippet,
                    "content_sha256": hashlib.sha256(source_body.encode("utf-8", "replace")).hexdigest(),
                    "status_code": source["status_code"],
                    "content_type": source["content_type"],
                })
            else:
                evidence.append({
                    "url": item["url"],
                    "title": item["title"],
                    "snippet": snippet,
                    "content_sha256": "",
                    "status_code": 200,
                    "content_type": "search-result",
                })
        return {
            "status": "completed",
            "query": query,
            "source": source_url,
            "results": links[:10],
            "evidence": evidence[:10],
        }

    def _fetch(self, url: str) -> dict:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError("web_research_https_url_required")
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NORYX7/1.0; +https://noryx7.onrender.com)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
            "Referer": "https://html.duckduckgo.com/",
        })
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
    _VALUES = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 20000}

    @classmethod
    def _material(cls, board) -> int:
        score = 0
        for piece_type, value in cls._VALUES.items():
            score += len(board.pieces(piece_type, True)) * value
            score -= len(board.pieces(piece_type, False)) * value
        return score if board.turn else -score

    @classmethod
    def _search(cls, board, depth: int) -> tuple[int, str | None]:
        if board.is_checkmate():
            return -1_000_000 + depth, None
        if board.is_stalemate() or board.is_insufficient_material():
            return 0, None
        if depth <= 0:
            return cls._material(board), None
        best_score = -10**9
        best_move = None
        moves = list(board.legal_moves)
        moves.sort(key=lambda move: board.is_capture(move), reverse=True)
        for move in moves[:64]:
            board.push(move)
            child, _ = cls._search(board, depth - 1)
            score = -child
            board.pop()
            if score > best_score:
                best_score, best_move = score, move
        return best_score, best_move.uci() if best_move else None

    def __call__(self, target: str, parameters: dict) -> dict:
        try:
            import chess
        except ImportError as exc:
            raise CapabilityUnavailable("python_chess_required") from exc
        fen = str(parameters.get("fen") or "").strip()
        try:
            board = chess.Board(fen) if fen else chess.Board()
        except Exception as exc:
            raise ValueError("invalid_chess_position") from exc
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
            before = self._material(board)
            board.push(parsed)
            after = self._material(board)
            return {
                "status": "completed", "fen": board.fen(), "move": parsed.uci(), "legal": True,
                "check": board.is_check(), "checkmate": board.is_checkmate(),
                "stalemate": board.is_stalemate(), "material_delta": after - before,
            }
        requested_depth = parameters.get("depth", 2)
        try:
            depth = max(1, min(int(requested_depth), 3))
        except (TypeError, ValueError):
            raise ValueError("invalid_chess_depth")
        score, best_move = self._search(board, depth)
        legal = [m.uci() for m in board.legal_moves]
        return {
            "status": "completed", "fen": board.fen(), "legal_move_count": len(legal),
            "legal_moves": legal[:100], "best_move": best_move, "evaluation": score, "depth": depth,
            "check": board.is_check(), "checkmate": board.is_checkmate(), "stalemate": board.is_stalemate(),
            "engine_note": "bounded deterministic material/minimax analysis; not a strong chess engine",
        }


class ExternalProviderCapability:
    """Canonical HTTPS JSON provider adapter; provider-specific contracts stay explicit."""

    def __init__(self, name: str, env_prefix: str, *, timeout: float = 15.0, max_bytes: int = 256_000):
        self.name = name
        self.env_prefix = env_prefix
        self.timeout = timeout
        self.max_bytes = max_bytes

    def __call__(self, target: str, parameters: dict) -> dict:
        endpoint = os.environ.get(self.env_prefix + "_ENDPOINT", "").strip()
        token = os.environ.get(self.env_prefix + "_TOKEN", "").strip()
        if not endpoint or not token:
            raise CapabilityUnavailable(f"{self.name}_provider_not_configured")
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or not parts.netloc:
            raise CapabilityUnavailable(f"{self.name}_provider_https_required")
        execution_id = str(parameters.get("execution_id") or "").strip()
        if not execution_id:
            raise CapabilityUnavailable(f"{self.name}_execution_id_required")
        operation = str(parameters.get("operation") or target or self.name).strip()
        payload = {
            "operation": operation, "target": str(target or ""),
            "parameters": {k: v for k, v in dict(parameters).items() if k != "token"},
            "execution_id": execution_id, "idempotency_key": execution_id,
        }
        req = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {token}",
            "User-Agent": "NORYX7/1.0 frontier-provider", "X-NORYX7-Execution-ID": execution_id,
            "Idempotency-Key": execution_id,
        }, method="POST")
        try:
            with urlopen(req, timeout=self.timeout, context=ssl.create_default_context()) as response:
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise CapabilityUnavailable(f"{self.name}_response_too_large")
                data = json.loads(body.decode("utf-8", "replace"))
        except CapabilityUnavailable:
            raise
        except Exception as exc:
            raise CapabilityUnavailable(f"{self.name}_provider_request_failed") from exc
        if not isinstance(data, dict) or data.get("status") not in {"completed", "accepted"}:
            raise CapabilityUnavailable(f"{self.name}_provider_contract_rejected")
        provider_execution_id = str(data.get("execution_id") or data.get("correlation_id") or "").strip()
        if provider_execution_id != execution_id:
            raise CapabilityUnavailable(f"{self.name}_execution_identity_mismatch")
        if not data.get("verified", False):
            raise CapabilityUnavailable(f"{self.name}_provider_result_unverified")
        return data


def install_frontier_capabilities(tool_executor) -> tuple[str, ...]:
    """Install only concrete capability handlers; external providers remain fail-closed."""
    tool_executor.capabilities.register("web_research", WebResearchCapability(), risk_class="normal")
    tool_executor.capabilities.register("chess_analyze", ChessCapability(), risk_class="normal")
    tool_executor.capabilities.register("payments", ExternalProviderCapability("payments", "NORYX7_PAYMENTS"), risk_class="high")
    tool_executor.capabilities.register("flights", ExternalProviderCapability("flights", "NORYX7_FLIGHTS"), risk_class="high")
    tool_executor.capabilities.register("insurance", ExternalProviderCapability("insurance", "NORYX7_INSURANCE"), risk_class="high")
    return tool_executor.capabilities.names()
