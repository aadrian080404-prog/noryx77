from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"FINALIZE_ABORTED: anchor not found in {path}: {old[:100]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"FINALIZE_ABORTED: anchor is not unique in {path}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# Collaboration must remain active even with the canonical ToolExecutor installed.
replace(
    "core/hypersynth.py",
    '        if (\n            self.tool_executor is None\n            and task.task_type not in {"web_research", "chess_analyze", "payments", "flights", "insurance"}\n',
    '        if (\n            task.task_type not in {"web_research", "chess_analyze", "payments", "flights", "insurance"}\n',
)

# Generate a primary hypothesis plus an explicit alternative for a single-step reasoning task.
replace(
    "core/reasoning.py",
    '''        return tuple(Hypothesis(f"{task.task_id}:h{index}", task.task_id, step.objective, (step.step_id,)) for index, step in enumerate(plan.steps))\n''',
    '''        hypotheses = []\n        for index, step in enumerate(plan.steps):\n            hypotheses.append(Hypothesis(f"{task.task_id}:h{index}:primary", task.task_id, step.objective, (step.step_id,)))\n            if len(plan.steps) == 1:\n                hypotheses.append(Hypothesis(\n                    f"{task.task_id}:h{index}:alternative",\n                    task.task_id,\n                    f"Alternative approach: independently validate and cross-check {step.objective}",\n                    (step.step_id,),\n                ))\n        return tuple(hypotheses)\n''',
)

# Verification requires an explicit alternative whenever the plan is a single reasoning step.
replace(
    "core/reasoning.py",
    '''        return VerificationResult(True, "hypothesis", "hypotheses_ok")\n''',
    '''        if len(hypotheses) == 2 and not any("Alternative approach:" in h.statement for h in hypotheses):\n            return VerificationResult(False, "hypothesis", "missing_alternative_hypothesis")\n        return VerificationResult(True, "hypothesis", "hypotheses_ok")\n''',
)

# Deterministic simulation metadata; no claim of external truth.
replace(
    "core/reasoning.py",
    '''        return tuple(SimulationResult(h.hypothesis_id, bool(h.statement and h.task_id == task.task_id), "feasible" if h.statement and h.task_id == task.task_id else "invalid_hypothesis") for h in hypotheses if isinstance(h, Hypothesis))\n''',
    '''        simulated = []\n        for h in hypotheses:\n            valid = isinstance(h, Hypothesis) and bool(h.statement) and h.task_id == task.task_id\n            reason = "feasible_primary" if valid and ":primary" in h.hypothesis_id else ("feasible_alternative" if valid else "invalid_hypothesis")\n            simulated.append(SimulationResult(h.hypothesis_id, valid, reason))\n        return tuple(simulated)\n''',
)
replace(
    "core/reasoning.py",
    '''            if item.feasible and item.reason != "feasible": return VerificationResult(False, "simulation", "feasible_reason_mismatch")\n''',
    '''            if item.feasible and not item.reason.startswith("feasible_"): return VerificationResult(False, "simulation", "feasible_reason_mismatch")\n''',
)

# Add a bounded, inspectable hypothesis comparison engine.
append = '''\n\n@dataclass(frozen=True)\nclass HypothesisComparison:\n    hypothesis_id: str\n    score: float\n    selected: bool\n    reason: str\n\n\nclass HypothesisComparator:\n    """Deterministic comparison of declared hypotheses and bounded simulations."""\n    def compare(self, hypotheses: tuple[Hypothesis, ...], simulations: tuple[SimulationResult, ...]) -> tuple[HypothesisComparison, ...]:\n        if not hypotheses or len(hypotheses) != len(simulations):\n            return ()\n        scores = []\n        for h, sim in zip(hypotheses, simulations):\n            score = 0.0\n            if sim.feasible:\n                score += 0.6\n            if ":primary" in h.hypothesis_id:\n                score += 0.2\n            if h.basis:\n                score += 0.2\n            scores.append((h.hypothesis_id, min(score, 1.0)))\n        best_id, _ = max(scores, key=lambda item: (item[1], item[0]))\n        return tuple(\n            HypothesisComparison(hid, score, hid == best_id, "selected" if hid == best_id else "alternative_cross_check")\n            for hid, score in scores\n        )\n\n    def verify(self, comparisons: tuple[HypothesisComparison, ...]) -> VerificationResult:\n        if not comparisons:\n            return VerificationResult(False, "hypothesis_comparison", "no_comparisons")\n        if sum(1 for item in comparisons if item.selected) != 1:\n            return VerificationResult(False, "hypothesis_comparison", "selection_not_unique")\n        if any(not 0.0 <= item.score <= 1.0 for item in comparisons):\n            return VerificationResult(False, "hypothesis_comparison", "invalid_hypothesis_score")\n        return VerificationResult(True, "hypothesis_comparison", "comparison_ok")\n'''
reasoning = ROOT / "core/reasoning.py"
text = reasoning.read_text(encoding="utf-8")
if "class HypothesisComparator:" not in text:
    reasoning.write_text(text + append, encoding="utf-8")

# Wire the comparator into HYPERSYNTH.
replace(
    "core/hypersynth.py",
    'from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator\n',
    'from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator, HypothesisComparator\n',
)
replace(
    "core/hypersynth.py",
    '        self.cross_checker = cross_checker or CrossChecker()\n',
    '        self.cross_checker = cross_checker or CrossChecker()\n        self.hypothesis_comparator = HypothesisComparator()\n',
)
replace(
    "core/hypersynth.py",
    '        if not self._accepts_verification(hypothesis_check, "hypothesis"): return self._reject("hypothesis", task, hypothesis_check if isinstance(hypothesis_check, VerificationResult) and hypothesis_check.is_well_formed() else VerificationResult(False, "hypothesis", "invalid_hypothesis_verification"))\n        if len(hypotheses) != len(plan.steps): return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))\n',
    '        if not self._accepts_verification(hypothesis_check, "hypothesis"): return self._reject("hypothesis", task, hypothesis_check if isinstance(hypothesis_check, VerificationResult) and hypothesis_check.is_well_formed() else VerificationResult(False, "hypothesis", "invalid_hypothesis_verification"))\n        expected_hypothesis_count = 2 if len(plan.steps) == 1 and task.task_type not in {"web_research", "chess_analyze", "payments", "flights", "insurance"} else len(plan.steps)\n        if len(hypotheses) != expected_hypothesis_count: return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))\n',
)
replace(
    "core/hypersynth.py",
    '        if tuple(s.hypothesis_id for s in simulations) != tuple(h.hypothesis_id for h in hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))\n',
    '        if tuple(s.hypothesis_id for s in simulations) != tuple(h.hypothesis_id for h in hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))\n        comparisons = self.hypothesis_comparator.compare(hypotheses, simulations)\n        comparison_check = self.hypothesis_comparator.verify(comparisons)\n        if not self._accepts_verification(comparison_check, "hypothesis_comparison"):\n            return self._reject("simulation", task, comparison_check)\n',
)
replace(
    "core/hypersynth.py",
    '        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": task.execution_id, "audit": self.audit.snapshot()}\n',
    '        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "hypothesis_comparisons": comparisons, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": task.execution_id, "audit": self.audit.snapshot()}\n',
)

print("FRONTIER_WAVE2_FINALIZATION_PATCHED")
