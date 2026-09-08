from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"WIRE_ABORTED: expected one anchor in {path}, got {count}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_any(path: str, old_variants: tuple[str, ...], new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    matches = [old for old in old_variants if old in text]
    if len(matches) != 1:
        raise SystemExit(f"WIRE_ABORTED: expected one compatible anchor in {path}, got {len(matches)}")
    target.write_text(text.replace(matches[0], new, 1), encoding="utf-8")


def ensure_top_import(path: str, import_line: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    head, sep, tail = text.partition("\n\n")
    if not sep:
        raise SystemExit(f"WIRE_ABORTED: import section not found in {path}")
    lines = [line for line in head.splitlines() if line.strip() != import_line.strip()]
    lines.append(import_line.rstrip("\n"))
    target.write_text("\n".join(lines) + "\n\n" + tail, encoding="utf-8")


def ensure_single_import(path: str, import_line: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    seen = False
    out = []
    for line in lines:
        if line.strip() == import_line.strip():
            if seen:
                continue
            seen = True
        out.append(line)
    if not seen:
        raise SystemExit(f"WIRE_ABORTED: import anchor missing in {path}")
    target.write_text("".join(out), encoding="utf-8")


# Normalize imports first. This makes the repair safe after an interrupted run.
ensure_top_import("core/hypersynth.py", "from .collaboration import AgentCollaboration")
ensure_top_import("core/hypersynth.py", "from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator")
ensure_single_import("core/hypersynth.py", "from .collaboration import AgentCollaboration")

replace_any(
    "core/hypersynth.py",
    (
        "        self.tool_executor = tool_executor\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")",
        "        self.tool_executor = tool_executor\n        self.collaboration = AgentCollaboration(verifier)\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")",
    ),
    "        self.tool_executor = tool_executor\n        self.collaboration = AgentCollaboration(verifier)\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")",
)

replace("core/reasoning.py", "    basis: tuple[str, ...] = ()\n", "    basis: tuple[str, ...] = ()\n    score: float = 0.0\n    alternative: bool = False\n")
replace_any(
    "core/reasoning.py",
    (
        "        return tuple(Hypothesis(f\"{task.task_id}:h{index}\", task.task_id, step.objective, (step.step_id,)) for index, step in enumerate(plan.steps))",
        "        hypotheses = []\n        for index, step in enumerate(plan.steps):\n            hypotheses.append(Hypothesis(f\"{task.task_id}:h{index}:primary\", task.task_id, step.objective, (step.step_id,), score=0.6, alternative=False))\n            if len(plan.steps) == 1:\n                hypotheses.append(Hypothesis(f\"{task.task_id}:h{index}:alternative\", task.task_id, f\"Alternative approach: independently validate and cross-check {step.objective}\", (step.step_id,), score=0.4, alternative=True))\n        return tuple(hypotheses)",
    ),
    "        hypotheses = []\n        for index, step in enumerate(plan.steps):\n            hypotheses.append(Hypothesis(f\"{task.task_id}:h{index}:primary\", task.task_id, step.objective, (step.step_id,), score=0.6, alternative=False))\n            if len(plan.steps) == 1:\n                hypotheses.append(Hypothesis(f\"{task.task_id}:h{index}:alternative\", task.task_id, f\"Alternative approach: independently validate and cross-check {step.objective}\", (step.step_id,), score=0.4, alternative=True))\n        return tuple(hypotheses)",
)
replace_any(
    "core/reasoning.py",
    (
        "            if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n",
        "            if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n            if not isinstance(hypothesis.score, (int, float)) or not 0.0 <= float(hypothesis.score) <= 1.0: return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_score\")\n            if not isinstance(hypothesis.alternative, bool): return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_alternative\")\n",
    ),
    "            if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n            if not isinstance(hypothesis.score, (int, float)) or not 0.0 <= float(hypothesis.score) <= 1.0: return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_score\")\n            if not isinstance(hypothesis.alternative, bool): return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_alternative\")\n",
)
replace_any(
    "core/reasoning.py",
    (
        "        return VerificationResult(True, \"hypothesis\", \"hypotheses_ok\")",
        "        if len(hypotheses) == 2 and not any(h.alternative for h in hypotheses): return VerificationResult(False, \"hypothesis\", \"missing_alternative_hypothesis\")\n        return VerificationResult(True, \"hypothesis\", \"hypotheses_ok\")",
    ),
    "        if len(hypotheses) == 2 and not any(h.alternative for h in hypotheses): return VerificationResult(False, \"hypothesis\", \"missing_alternative_hypothesis\")\n        return VerificationResult(True, \"hypothesis\", \"hypotheses_ok\")",
)

reasoning = ROOT / "core/reasoning.py"
if "class HypothesisComparator:" not in reasoning.read_text(encoding="utf-8"):
    reasoning.write_text(
        reasoning.read_text(encoding="utf-8")
        + '''\n\n@dataclass(frozen=True)\nclass HypothesisComparison:\n    hypothesis_id: str\n    score: float\n    selected: bool\n    reason: str\n\n\nclass HypothesisComparator:\n    """Bounded heuristic comparison; never presented as an oracle of truth."""\n    def compare(self, hypotheses: tuple[Hypothesis, ...], simulations: tuple[SimulationResult, ...]) -> tuple[HypothesisComparison, ...]:\n        if not hypotheses or len(hypotheses) != len(simulations):\n            return ()\n        scores = []\n        for hypothesis, simulation in zip(hypotheses, simulations):\n            score = float(hypothesis.score)\n            if simulation.feasible:\n                score += 0.35\n            if hypothesis.basis:\n                score += 0.05\n            score = min(1.0, score)\n            scores.append((hypothesis.hypothesis_id, score))\n        best_id, _ = max(scores, key=lambda item: (item[1], item[0]))\n        return tuple(HypothesisComparison(hid, score, hid == best_id, "selected" if hid == best_id else "cross_checked_alternative") for hid, score in scores)\n\n    def verify(self, comparisons: tuple[HypothesisComparison, ...]) -> VerificationResult:\n        if not comparisons or sum(item.selected for item in comparisons) != 1:\n            return VerificationResult(False, "hypothesis_comparison", "selection_not_unique")\n        if any(not 0.0 <= item.score <= 1.0 for item in comparisons):\n            return VerificationResult(False, "hypothesis_comparison", "invalid_hypothesis_score")\n        return VerificationResult(True, "hypothesis_comparison", "comparison_ok")\n''',
        encoding="utf-8",
    )

ensure_top_import("core/hypersynth.py", "from .reasoning import HypothesisComparator")

replace("core/hypersynth.py", "        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()\n", "        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()\n        self.hypothesis_comparator = HypothesisComparator()\n")
replace(
    "core/hypersynth.py",
    "        if len(hypotheses) != len(plan.steps): return self._reject(\"hypothesis\", task, VerificationResult(False, \"hypothesis\", \"hypothesis_plan_mismatch\"))",
    "        expected_hypotheses = 2 if len(plan.steps) == 1 and task.task_type not in {\"web_research\", \"chess_analyze\", \"payments\", \"flights\", \"insurance\"} else len(plan.steps)\n        if len(hypotheses) != expected_hypotheses: return self._reject(\"hypothesis\", task, VerificationResult(False, \"hypothesis\", \"hypothesis_plan_mismatch\"))",
)
replace(
    "core/hypersynth.py",
    "        if len(simulations) != len(hypotheses): return self._reject(\"simulation\", task, VerificationResult(False, \"simulation\", \"simulation_hypothesis_mismatch\"))",
    "        if len(simulations) != len(hypotheses): return self._reject(\"simulation\", task, VerificationResult(False, \"simulation\", \"simulation_hypothesis_mismatch\"))\n        hypothesis_comparisons = self.hypothesis_comparator.compare(hypotheses, simulations)\n        hypothesis_comparison_check = self.hypothesis_comparator.verify(hypothesis_comparisons)\n        if not self._accepts_verification(hypothesis_comparison_check, \"hypothesis_comparison\"): return self._reject(\"simulation\", task, hypothesis_comparison_check)\n        selected_ids = {item.hypothesis_id for item in hypothesis_comparisons if item.selected}\n        execution_hypotheses = tuple(h for h in hypotheses if h.hypothesis_id in selected_ids)\n        if len(execution_hypotheses) != len(plan.steps): return self._reject(\"simulation\", task, VerificationResult(False, \"hypothesis_comparison\", \"selected_hypothesis_plan_mismatch\"))",
)
replace(
    "core/hypersynth.py",
    'action = ActionSpec("act:" + child.task_id, step.action_type, target=step.objective, parameters={"input": task.input, "constraints": dict(task.constraints)}, risk_class=step.risk_class, execution_id=task.execution_id)',
    'action = ActionSpec("act:" + child.task_id, step.action_type, target=step.objective, parameters={"input": task.input, "constraints": dict(task.constraints), "execution_id": task.execution_id}, risk_class=step.risk_class, execution_id=task.execution_id)',
)
replace("core/hypersynth.py", "        cross_check = self.cross_checker.verify(task, tuple(results), hypotheses)", "        cross_check = self.cross_checker.verify(task, tuple(results), execution_hypotheses)")
replace("core/hypersynth.py", "        metacognitive_check, reflection = self.metacognition.reflect(task, plan, hypotheses, simulations, tuple(results), output_check)", "        metacognitive_check, reflection = self.metacognition.reflect(task, plan, execution_hypotheses, simulations, tuple(results), output_check)")

print("NORYX7 REAL FRONTIER CONNECTIONS WIRED")
print("CHAIN = TASK -> HYPERSYNTH -> HYPOTHESES -> COMPARISON -> PRIMARY/SECONDARY -> GATED EXECUTION -> VERIFICATION -> MEMORY/STATE")
