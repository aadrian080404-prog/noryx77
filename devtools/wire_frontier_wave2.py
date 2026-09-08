from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"WIRE_ABORTED: {path} anchor count={count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


def ensure_import(path: str, line: str) -> None:
    text = read(path)
    lines = text.splitlines()
    if line in lines:
        # Deduplicate the exact import while preserving the first occurrence.
        seen = False
        out = []
        for item in lines:
            if item == line:
                if seen:
                    continue
                seen = True
            out.append(item)
        write(path, "\n".join(out) + "\n")
        return
    marker = "\n\n"
    head, sep, tail = text.partition(marker)
    if not sep:
        raise SystemExit(f"WIRE_ABORTED: import section missing in {path}")
    write(path, head + "\n" + line + marker + tail)


# ---- Reasoning: one verified primary hypothesis plus an explicit alternative ----
ensure_import("core/reasoning.py", "from .contracts import AgentResult, TaskSpec, VerificationResult")
replace_once(
    "core/reasoning.py",
    "    basis: tuple[str, ...] = ()\n",
    "    basis: tuple[str, ...] = ()\n    score: float = 0.6\n    alternative_statement: str = \"\"\n",
)
replace_once(
    "core/reasoning.py",
    "        return tuple(Hypothesis(f\"{task.task_id}:h{index}\", task.task_id, step.objective, (step.step_id,)) for index, step in enumerate(plan.steps))",
    "        return tuple(Hypothesis(f\"{task.task_id}:h{index}\", task.task_id, step.objective, (step.step_id,), score=0.6, alternative_statement=f\"Independently validate and cross-check: {step.objective}\") for index, step in enumerate(plan.steps))",
)
replace_once(
    "core/reasoning.py",
    "            if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n",
    "            if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n            if not isinstance(hypothesis.score, (int, float)) or not 0.0 <= float(hypothesis.score) <= 1.0: return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_score\")\n            if not isinstance(hypothesis.alternative_statement, str) or not hypothesis.alternative_statement.strip(): return VerificationResult(False, \"hypothesis\", \"missing_alternative_hypothesis\")\n",
)
if "class HypothesisComparator:" not in read("core/reasoning.py"):
    write(
        "core/reasoning.py",
        read("core/reasoning.py")
        + '''\n\n@dataclass(frozen=True)\nclass HypothesisComparison:\n    hypothesis_id: str\n    primary_score: float\n    alternative_score: float\n    selected_strategy: str\n    reason: str\n\n\nclass HypothesisComparator:\n    """Bounded comparison of the planned hypothesis against its explicit alternative."""\n    def compare(self, hypotheses: tuple[Hypothesis, ...], simulations: tuple[SimulationResult, ...]) -> tuple[HypothesisComparison, ...]:\n        if not hypotheses or len(hypotheses) != len(simulations):\n            return ()\n        output = []\n        for hypothesis, simulation in zip(hypotheses, simulations):\n            primary = min(1.0, float(hypothesis.score) + (0.35 if simulation.feasible else 0.0) + (0.05 if hypothesis.basis else 0.0))\n            alternative = min(1.0, float(hypothesis.score) + (0.35 if simulation.feasible else 0.0) + 0.02)\n            selected = "primary" if primary >= alternative else "alternative"\n            output.append(HypothesisComparison(hypothesis.hypothesis_id, primary, alternative, selected, "bounded_simulation_comparison"))\n        return tuple(output)\n\n    def verify(self, comparisons: tuple[HypothesisComparison, ...]) -> VerificationResult:\n        if not comparisons:\n            return VerificationResult(False, "hypothesis_comparison", "empty_comparison")\n        if any(not 0.0 <= item.primary_score <= 1.0 or not 0.0 <= item.alternative_score <= 1.0 for item in comparisons):\n            return VerificationResult(False, "hypothesis_comparison", "invalid_comparison_score")\n        if any(item.selected_strategy not in {"primary", "alternative"} for item in comparisons):\n            return VerificationResult(False, "hypothesis_comparison", "invalid_selected_strategy")\n        return VerificationResult(True, "hypothesis_comparison", "comparison_ok")\n''',
    )

# ---- HYPERSYNTH imports and collaboration capability ----
ensure_import("core/hypersynth.py", "from .collaboration import AgentCollaboration")
ensure_import("core/hypersynth.py", "from .reasoning import HypothesisComparator")
replace_once(
    "core/hypersynth.py",
    "        self.tool_executor = tool_executor\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")",
    "        self.tool_executor = tool_executor\n        self.collaboration = AgentCollaboration(verifier)\n        self.hypothesis_comparator = HypothesisComparator()\n        if self.tool_executor is not None and self.tool_executor.capabilities.resolve(\"agent_collaboration\") is None:\n            self.tool_executor.capabilities.register(\"agent_collaboration\", self._execute_collaboration_capability, risk_class=\"normal\")\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")",
)
replace_once(
    "core/hypersynth.py",
    "    def _state(self, phase, task, context, confidence=0.0): return CognitiveState(phase, task.task_id, context=context, confidence=confidence, execution_id=task.execution_id)\n",
    '''    def _execute_collaboration_capability(self, target, parameters):\n        primary_id = parameters.get("primary_agent_id")\n        secondary_id = parameters.get("secondary_agent_id")\n        primary = self.router.route(primary_id)\n        secondary = self.router.route(secondary_id)\n        collaboration_task = TaskSpec(\n            parameters["task_id"],\n            parameters["task_type"],\n            parameters["objective"],\n            parameters["input"],\n            parameters["constraints"],\n            tuple(parameters["verification_requirements"]),\n            parameters["risk_class"],\n            parameters["execution_id"],\n        )\n        reconciliation, check = self.collaboration.run(collaboration_task, primary, secondary)\n        if not check.valid:\n            raise RuntimeError("collaboration_not_verified")\n        return reconciliation.output\n\n    def _state(self, phase, task, context, confidence=0.0): return CognitiveState(phase, task.task_id, context=context, confidence=confidence, execution_id=task.execution_id)\n''',
)
replace_once(
    "core/hypersynth.py",
    "        if len(hypotheses) != len(plan.steps): return self._reject(\"hypothesis\", task, VerificationResult(False, \"hypothesis\", \"hypothesis_plan_mismatch\"))",
    "        if len(hypotheses) != len(plan.steps): return self._reject(\"hypothesis\", task, VerificationResult(False, \"hypothesis\", \"hypothesis_plan_mismatch\"))",
)
replace_once(
    "core/hypersynth.py",
    "        if len(simulations) != len(hypotheses): return self._reject(\"simulation\", task, VerificationResult(False, \"simulation\", \"simulation_hypothesis_mismatch\"))",
    "        if len(simulations) != len(hypotheses): return self._reject(\"simulation\", task, VerificationResult(False, \"simulation\", \"simulation_hypothesis_mismatch\"))\n        hypothesis_comparisons = self.hypothesis_comparator.compare(hypotheses, simulations)\n        hypothesis_comparison_check = self.hypothesis_comparator.verify(hypothesis_comparisons)\n        if not self._accepts_verification(hypothesis_comparison_check, \"hypothesis_comparison\"): return self._reject(\"simulation\", task, hypothesis_comparison_check)",
)
replace_once(
    "core/hypersynth.py",
    '            action = ActionSpec("act:" + child.task_id, step.action_type, target=step.objective, parameters={"input": task.input, "constraints": dict(task.constraints)}, risk_class=step.risk_class, execution_id=task.execution_id)',
    '''            use_collaboration = (\n                len(plan.steps) == 1\n                and len(ordered_agents) >= 2\n                and task.task_type not in {"web_research", "chess_analyze", "payments", "flights", "insurance"}\n            )\n            action_type = "agent_collaboration" if use_collaboration else step.action_type\n            parameters = {"input": task.input, "constraints": dict(task.constraints), "execution_id": task.execution_id}\n            if use_collaboration:\n                parameters.update({\n                    "task_id": task.task_id,\n                    "task_type": task.task_type,\n                    "objective": task.objective,\n                    "verification_requirements": tuple(task.verification_requirements),\n                    "risk_class": step.risk_class,\n                    "primary_agent_id": ordered_agents[0],\n                    "secondary_agent_id": ordered_agents[1],\n                })\n            action = ActionSpec("act:" + child.task_id, action_type, target=step.objective, parameters=parameters, risk_class=step.risk_class, execution_id=task.execution_id)''',
)
replace_once(
    "core/hypersynth.py",
    '        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": task.execution_id, "audit": self.audit.snapshot()}',
    '        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "hypothesis_comparisons": hypothesis_comparisons, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": task.execution_id, "audit": self.audit.snapshot()}',
)

# Execution identity is explicit at the tool boundary.
replace_once(
    "core/hypersynth.py",
    'parameters={"input": task.input, "constraints": dict(task.constraints)}',
    'parameters={"input": task.input, "constraints": dict(task.constraints), "execution_id": task.execution_id}',
)

print("NORYX7 REAL FRONTIER CONNECTIONS WIRED")
print("CHAIN = TASK -> HYPERSYNTH -> HYPOTHESIS/ALTERNATIVE -> SIMULATION/COMPARISON -> PRIMARY/SECONDARY -> ACTIONGATE -> TOOL EXECUTOR -> VERIFICATION -> MEMORY/STATE")
