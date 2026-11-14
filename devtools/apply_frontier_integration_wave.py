from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CAP = ROOT / "core" / "frontier_capabilities.py"
CAP.write_text(r'''from __future__ import annotations

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
''', encoding="utf-8")


# planning: capability task types are explicit and still bounded by verification.
planning = ROOT / "core" / "planning.py"
text = planning.read_text(encoding="utf-8")
text = text.replace(
    'VALID_ACTION_TYPES = {"compute"}',
    'VALID_ACTION_TYPES = {"compute", "web_research", "chess_analyze", "payments", "flights", "insurance"}',
)
text = text.replace(
    'step = PlanStep(f"{task.task_id}:0", task.objective, "compute", task.risk_class)',
    'action_type = task.task_type if task.task_type in self.VALID_ACTION_TYPES else "compute"\n        step = PlanStep(f"{task.task_id}:0", task.objective, action_type, task.risk_class)',
)
planning.write_text(text, encoding="utf-8")


# Hypersynth receives the canonical ToolExecutor and uses it only for explicit capabilities.
hs = ROOT / "core" / "hypersynth.py"
text = hs.read_text(encoding="utf-8")
text = text.replace(
    'max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None, recovery=None):',
    'max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None, recovery=None, tool_executor=None):',
)
text = text.replace(
    'self.recovery = recovery\n        if self.recovery is not None',
    'self.recovery = recovery\n        self.tool_executor = tool_executor\n        if self.recovery is not None',
)
old = '''            action = ActionSpec("act:" + child.task_id, step.action_type, risk_class=step.risk_class, execution_id=task.execution_id)\n            try:\n                operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child), calls_used=index, execution_id=task.execution_id)\n                if self.recovery is not None:\n                    decision, result = self.recovery.run_if_normal(operation, expected_epoch=recovery_epoch)\n                else:\n                    decision, result = operation()\n                if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))\n            except Exception:\n                return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))\n'''
new = '''            action = ActionSpec("act:" + child.task_id, step.action_type, target=step.objective, parameters={"input": task.input, "constraints": dict(task.constraints)}, risk_class=step.risk_class, execution_id=task.execution_id)\n            try:\n                capability = self.tool_executor is not None and self.tool_executor.capabilities.resolve(step.action_type) is not None\n                if capability:\n                    operation = lambda: self.tool_executor.execute(action, calls_used=index, execution_id=task.execution_id, principal=agent.agent_id)\n                    if self.recovery is not None:\n                        def guarded():\n                            return operation()\n                        _, capability_result = self.recovery.run_if_normal(guarded, expected_epoch=recovery_epoch)\n                    else:\n                        capability_result = operation()\n                    capability_output, capability_check = capability_result\n                    if not capability_check.valid:\n                        return self._reject("execution", task, capability_check, results=tuple(results))\n                    result = AgentResult(agent.agent_id, child.task_id, "completed", capability_output, VerificationResult(True, "agent_result", "capability_result_verified"), task.execution_id)\n                else:\n                    operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child), calls_used=index, execution_id=task.execution_id)\n                    if self.recovery is not None:\n                        decision, result = self.recovery.run_if_normal(operation, expected_epoch=recovery_epoch)\n                    else:\n                        decision, result = operation()\n                    if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))\n            except Exception:\n                return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))\n'''
if old not in text:
    raise RuntimeError("HYPERSYNTH execution block anchor not found")
text = text.replace(old, new, 1)
hs.write_text(text, encoding="utf-8")


# HypersynthRuntime installs one canonical ToolExecutor and passes it into the kernel.
hr = ROOT / "core" / "hypersynth_runtime.py"
text = hr.read_text(encoding="utf-8")
text = text.replace('from .verification import VerificationEngine\n', 'from .verification import VerificationEngine\nfrom .tools import ToolExecutor\nfrom .frontier_capabilities import install_frontier_capabilities\n')
text = text.replace(
    'self.action_gate = ActionGate(self.policy, self.security, self.limits)\n        self.memory',
    'self.action_gate = ActionGate(self.policy, self.security, self.limits)\n        self.tool_executor = ToolExecutor(self.action_gate, self.verifier)\n        self.frontier_capabilities = install_frontier_capabilities(self.tool_executor)\n        self.memory',
)
text = text.replace(
    'recovery=self.recovery,\n        )',
    'recovery=self.recovery,\n            tool_executor=self.tool_executor,\n        )',
    1,
)
hr.write_text(text, encoding="utf-8")


# Runtime exposes the canonical registry to the rest of NORYX7.
rt = ROOT / "core" / "runtime.py"
text = rt.read_text(encoding="utf-8")
text = text.replace(
    'self.hypersynth = HypersynthRuntime(\n',
    'self.hypersynth = HypersynthRuntime(\n',
)
text = text.replace(
    'self._offline: OfflineRuntime | None = None',
    'self.capability_registry = self.hypersynth.tool_executor.capabilities\n        self.tool_executor = self.hypersynth.tool_executor\n        self.frontier_capabilities = self.hypersynth.frontier_capabilities\n        self._offline: OfflineRuntime | None = None',
)
rt.write_text(text, encoding="utf-8")


# Agent metadata now reflects concrete capabilities exposed by the canonical registry.
agent = ROOT / "core" / "llm" / "agent.py"
text = agent.read_text(encoding="utf-8")
text = text.replace(
    '"capability_selection",\n    )',
    '"capability_selection",\n        "web_research",\n        "chess_analyze",\n        "payments",\n        "flights",\n        "insurance",\n    )',
    1,
)
agent.write_text(text, encoding="utf-8")


# Comprehensive integration tests. These verify wiring without pretending that external
# provider credentials exist.
test = ROOT / "core" / "test_frontier_integration_wave.py"
test.write_text(r'''import unittest

from core.contracts import TaskSpec
from core.hypersynth_runtime import HypersynthRuntime
from core.llm.agent import LLMBackedAgent
from core.verification import VerificationEngine
from core.router import ResourceRouter


class FakeModel:
    name = "frontier-test-model"
    capabilities = frozenset({"text", "reasoning", "chat"})
    cost_per_call = 0.0
    expected_latency_ms = 1.0

    def generate(self, prompt, *, tools=()):
        return "verified frontier response"


class FrontierIntegrationWaveTests(unittest.TestCase):
    def test_capability_registry_contains_frontier_surface(self):
        runtime = HypersynthRuntime()
        names = runtime.tool_executor.capabilities.names()
        for name in ("web_research", "chess_analyze", "payments", "flights", "insurance"):
            self.assertIn(name, names)

    def test_web_capability_rejects_cleartext(self):
        runtime = HypersynthRuntime()
        handler = runtime.tool_executor.capabilities.resolve("web_research")
        with self.assertRaises(ValueError):
            handler("http://example.com", {})

    def test_external_providers_fail_closed(self):
        runtime = HypersynthRuntime()
        for name in ("payments", "flights", "insurance"):
            handler = runtime.tool_executor.capabilities.resolve(name)
            with self.assertRaises(RuntimeError):
                handler("operation", {})

    def test_primary_identity_metadata(self):
        from core.identity import AgentIdentityAuthority
        identity, _ = AgentIdentityAuthority.generate("noryx7-llm")
        agent = LLMBackedAgent(FakeModel(), verifier=VerificationEngine(), identity=identity)
        description = agent.describe()
        self.assertEqual(description["agent_id"], "noryx7-llm")
        self.assertEqual(description["creator"], "Adrian Aristodemo")
        self.assertIn("web_research", description["capabilities"])


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

print("===== NORYX7 FRONTIER INTEGRATION WAVE PATCHED =====")
print("capabilities = web_research,chess_analyze,payments,flights,insurance")
print("agent mesh = primary + secondary")
print("verification = canonical ToolExecutor + ActionGate")
print("providers = fail-closed until configured")
''