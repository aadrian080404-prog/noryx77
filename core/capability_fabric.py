from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


@dataclass(frozen=True)
class CapabilityIntent:
    capability: str
    operation: str
    risk_class: str
    confidence: float
    rationale: str
    requires_external_provider: bool
    requires_user_confirmation: bool


class CapabilityFabric:
    """Single intent-to-capability boundary used by the canonical runtime.

    It does not execute external side effects. It only classifies an already
    authenticated request and produces an explicit capability contract for the
    normal HYPERSYNTH pipeline. High-risk capabilities always require a later
    authorization/confirmation decision before an external provider can act.
    """

    _RULES = (
        ("flights", ("volo", "voli", "aereo", "aerei", "flight", "flights", "prenota un volo", "prenotare un volo", "biglietto aereo"), "booking", "high"),
        ("payments", ("paga", "pagare", "pagamento", "bolletta", "bollette", "bonifico", "payment", "pay"), "payment", "high"),
        ("contracts", ("contratto", "contratti", "firma il contratto", "firma contratto", "accordo", "contract", "signing"), "contract", "high"),
        ("bureaucracy", ("burocrazia", "burocratico", "modulo", "moduli", "agenzia delle entrate", "inps", "comune", "documentazione", "domanda amministrativa", "pratica"), "procedure", "high"),
        ("insurance", ("assicurazione", "assicurazione auto", "polizza", "insurance"), "quote", "high"),
        ("web_research", ("cerca online", "cerca sul web", "ricerca web", "internet", "online", "search the web", "web research"), "research", "normal"),
        ("chess_analyze", ("scacchi", "scacchiera", "chess", "mossa migliore"), "analysis", "normal"),
    )

    def classify(self, text: str, *, explicit_capability: str | None = None) -> CapabilityIntent:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("capability_intent_input_required")
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        if explicit_capability:
            capability = explicit_capability.strip().lower()
            known = {item[0]: item for item in self._RULES}
            if capability not in known:
                raise ValueError("capability_not_supported")
            _, phrases, operation, risk = known[capability]
            return CapabilityIntent(capability, operation, risk, 1.0, "explicit_capability", capability not in {"web_research", "chess_analyze"}, risk == "high")
        scored: list[tuple[int, int, str, str, str]] = []
        for order, (capability, phrases, operation, risk) in enumerate(self._RULES):
            score = sum(2 if phrase in normalized else 0 for phrase in phrases)
            if score:
                scored.append((score, -order, capability, operation, risk))
        if not scored:
            return CapabilityIntent("compute", "answer", "normal", 0.0, "no_specialized_capability_match", False, False)
        scored.sort(reverse=True)
        score, _, capability, operation, risk = scored[0]
        confidence = min(1.0, 0.5 + 0.1 * score)
        return CapabilityIntent(capability, operation, risk, confidence, "deterministic_intent_match", capability not in {"web_research", "chess_analyze", "compute"}, risk == "high")

    @staticmethod
    def enrich_constraints(constraints: Mapping[str, object] | None, intent: CapabilityIntent) -> dict[str, object]:
        result = dict(constraints or {})
        result.update({
            "_noryx7_capability": intent.capability,
            "_noryx7_operation": intent.operation,
            "_noryx7_capability_confidence": intent.confidence,
            "_noryx7_requires_external_provider": intent.requires_external_provider,
            "_noryx7_requires_user_confirmation": intent.requires_user_confirmation,
        })
        return result
