from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COLLAB = ROOT / "core" / "collaboration.py"
COLLAB.write_text(r'''from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .contracts import AgentResult, TaskSpec, VerificationResult


@dataclass(frozen=True)
class Proposal:
    execution_id: str
    task_id: str
    agent_id: str
    output: Any
    evidence_digest: str


@dataclass(frozen=True)
class Critique:
    execution_id: str
    task_id: str
    agent_id: str
    target_agent_id: str
    accepted: bool
    output: Any
    evidence_digest: str


@dataclass(frozen=True)
class Reconciliation:
    execution_id: str
    task_id: str
    proposal_agent_id: str
    critic_agent_id: str
    accepted: bool
    output: Any
    proposal_digest: str
    critique_digest: str


class AgentCollaboration:
    """Bounded proposal -> critique -> reconciliation protocol."""

    def __init__(self, verifier):
        self.verifier = verifier

    @staticmethod
    def _digest(value: Any) -> str:
        return sha256(repr(value).encode("utf-8", "replace")).hexdigest()

    def _review_task(self, task: TaskSpec, proposal: Proposal) -> TaskSpec:
        return TaskSpec(
            task_id=f"{task.task_id}:critique",
            task_type="agent_critique",
            objective=(
                "Review the PRIMARY proposal below against the original objective. "
                "Return a concise critique. Start with exactly APPROVE or REJECT, "
                "then explain evidence, risks and corrections. Do not claim execution.\n"
                f"ORIGINAL OBJECTIVE: {task.objective}\n"
                f"PRIMARY PROPOSAL: {proposal.output!r}"
            ),
            input=task.input,
            constraints=task.constraints,
            verification_requirements=task.verification_requirements,
            risk_class=task.risk_class,
            execution_id=task.execution_id,
        )

    def _revision_task(self, task: TaskSpec, proposal: Proposal, critique: Critique) -> TaskSpec:
        return TaskSpec(
            task_id=f"{task.task_id}:reconcile",
            task_type="agent_reconciliation",
            objective=(
                "Produce the reconciled answer using the PRIMARY proposal and SECONDARY critique. "
                "Preserve correct parts, fix supported issues, and do not invent evidence. "
                "If evidence is insufficient, explicitly say INSUFFICIENT_EVIDENCE.\n"
                f"ORIGINAL OBJECTIVE: {task.objective}\n"
                f"PRIMARY PROPOSAL: {proposal.output!r}\n"
                f"SECONDARY CRITIQUE: {critique.output!r}"
            ),
            input=task.input,
            constraints=task.constraints,
            verification_requirements=task.verification_requirements,
            risk_class=task.risk_class,
            execution_id=task.execution_id,
        )

    def run(self, task: TaskSpec, primary, secondary) -> tuple[Reconciliation | None, VerificationResult]:
        if not isinstance(task, TaskSpec) or not task.execution_id:
            return None, VerificationResult(False, "collaboration", "invalid_collaboration_task")
        if primary.agent_id == secondary.agent_id:
            return None, VerificationResult(False, "collaboration", "agents_must_be_distinct")

        primary_task = TaskSpec(
            f"{task.task_id}:proposal", "agent_proposal", task.objective,
            task.input, task.constraints, task.verification_requirements,
            task.risk_class, task.execution_id,
        )
        proposal_result = primary.run(primary_task)
        if not isinstance(proposal_result, AgentResult) or proposal_result.status != "completed" or proposal_result.output is None:
            return None, VerificationResult(False, "collaboration", "primary_proposal_failed")
        proposal = Proposal(task.execution_id, task.task_id, primary.agent_id, proposal_result.output, self._digest(proposal_result.output))

        critique_result = secondary.run(self._review_task(task, proposal))
        if not isinstance(critique_result, AgentResult) or critique_result.status != "completed" or critique_result.output is None:
            return None, VerificationResult(False, "collaboration", "secondary_critique_failed")
        text = str(critique_result.output).strip()
        first = text.split(None, 1)[0].upper() if text else ""
        if first not in {"APPROVE", "REJECT"}:
            return None, VerificationResult(False, "collaboration", "unstructured_secondary_critique")
        critique = Critique(task.execution_id, task.task_id, secondary.agent_id, primary.agent_id, first == "APPROVE", text, self._digest(text))

        revision_result = primary.run(self._revision_task(task, proposal, critique))
        if not isinstance(revision_result, AgentResult) or revision_result.status != "completed" or revision_result.output is None:
            return None, VerificationResult(False, "collaboration", "reconciliation_failed")
        output_check = self.verifier.verify_output(revision_result.output, stage="agent_result")
        if not isinstance(output_check, VerificationResult) or not output_check.is_well_formed() or not output_check.valid:
            return None, VerificationResult(False, "collaboration", "reconciled_output_unverified")
        reconciliation = Reconciliation(
            task.execution_id, task.task_id, primary.agent_id, secondary.agent_id,
            True, revision_result.output, proposal.evidence_digest, critique.evidence_digest,
        )
        return reconciliation, VerificationResult(True, "collaboration", "proposal_critique_reconciled")
''', encoding="utf-8")

h = ROOT / "core" / "hypersynth.py"
s = h.read_text(encoding="utf-8")
old = "        self.tool_executor = tool_executor\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")"
new = "        self.tool_executor = tool_executor\n        from .collaboration import AgentCollaboration\n        self.collaboration = AgentCollaboration(verifier)\n        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError(\"invalid_recovery_controller\")"
if old not in s:
    raise SystemExit("hypersynth constructor anchor not found")
s = s.replace(old, new, 1)

anchor = "        agents = self.router.available()\n        if not agents: return self._reject(\"allocation\", task, VerificationResult(False, \"allocation\", \"no_agents_available\"))"
insert = '''        agents = self.router.available()\n        if not agents: return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))\n        # General reasoning uses an explicit Primary -> Secondary -> Primary loop.\n        # Capability tasks stay on ToolExecutor so external effects remain gated.\n        if (\n            self.tool_executor is None\n            and task.task_type not in {"web_research", "chess_analyze", "payments", "flights", "insurance"}\n            and len(agents) >= 2\n            and len(plan.steps) == 1\n        ):\n            try:\n                primary_id = preferred_agent or agents[0]\n                secondary_id = next(agent_id for agent_id in agents if agent_id != primary_id)\n                primary = self.router.get(primary_id)\n                secondary = self.router.get(secondary_id)\n                reconciliation, collaboration_check = self.collaboration.run(task, primary, secondary)\n                if not collaboration_check.valid or reconciliation is None:\n                    return self._reject("verification", task, collaboration_check)\n                self.audit.record("agent_proposal", task_id=task.task_id, execution_id=task.execution_id, agent_id=primary_id)\n                self.audit.record("agent_critique", task_id=task.task_id, execution_id=task.execution_id, agent_id=secondary_id)\n                self.audit.record("agent_reconciliation", task_id=task.task_id, execution_id=task.execution_id, agent_id=primary_id)\n                final_check = self.verifier.verify_output(reconciliation.output, stage="hypersynth_result")\n                if not self._accepts_verification(final_check, "hypersynth_result"):\n                    return self._reject("verification", task, final_check)\n                synthetic = AgentResult(\n                    primary_id, plan.steps[0].step_id, "completed", reconciliation.output,\n                    VerificationResult(True, "agent_result", "reconciled_result_verified"), task.execution_id,\n                )\n                metacognitive_check, reflection = self.metacognition.reflect(\n                    task, plan, hypotheses, simulations, (synthetic,), final_check,\n                )\n                if not metacognitive_check.valid:\n                    return self._reject("metacognition", task, metacognitive_check)\n                if self.memory is not None:\n                    from .memory import MemoryItem\n                    self.memory.put(MemoryItem(\n                        "task:" + task.execution_id + ":" + task.task_id,\n                        reconciliation.output, kind="working", source=task.task_id,\n                        importance=0.5, execution_id=task.execution_id,\n                    ))\n                return {\n                    "status": "completed", "phase": "metacognition",\n                    "state": self._state("metacognition", task, context, confidence=reflection.confidence),\n                    "context": context, "plan": plan, "hypotheses": hypotheses,\n                    "simulations": simulations, "results": (synthetic,),\n                    "collaboration": reconciliation, "verification": final_check,\n                    "reflection": reflection, "execution_id": task.execution_id,\n                    "audit": self.audit.snapshot(),\n                }\n            except Exception:\n                return self._reject("execution", task, VerificationResult(False, "collaboration", "collaboration_failure"))\n'''
if anchor not in s:
    raise SystemExit("hypersynth allocation anchor not found")
s = s.replace(anchor, insert, 1)
h.write_text(s, encoding="utf-8")

r = ROOT / "core" / "reasoning.py"
s = r.read_text(encoding="utf-8")
s = s.replace("class Hypothesis:\n    hypothesis_id: str\n    task_id: str\n    statement: str\n    basis: tuple[str, ...] = ()", "class Hypothesis:\n    hypothesis_id: str\n    task_id: str\n    statement: str\n    basis: tuple[str, ...] = ()\n    score: float = 0.0\n    alternative: bool = False")
s = s.replace("return tuple(Hypothesis(f\"{task.task_id}:h{index}\", task.task_id, step.objective, (step.step_id,)) for index, step in enumerate(plan.steps))", "return tuple(Hypothesis(f\"{task.task_id}:h{index}\", task.task_id, step.objective, (step.step_id,), score=1.0, alternative=False) for index, step in enumerate(plan.steps))")
s = s.replace("if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")", "if hypothesis.hypothesis_id in ids: return VerificationResult(False, \"hypothesis\", \"duplicate_hypothesis_id\")\n            if not isinstance(hypothesis.score, (int, float)) or not 0.0 <= float(hypothesis.score) <= 1.0: return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_score\")\n            if not isinstance(hypothesis.alternative, bool): return VerificationResult(False, \"hypothesis\", \"invalid_hypothesis_alternative\")")
r.write_text(s, encoding="utf-8")

p = ROOT / "core" / "frontier_capabilities.py"
s = p.read_text(encoding="utf-8")
old = 'raise CapabilityUnavailable(f"{self.name}_adapter_requires_explicit_operation_contract")'
new = '''payload = {"operation": self.name, "target": target, "parameters": dict(parameters or {})}\n        req = Request(endpoint, data=__import__("json").dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "User-Agent": "NORYX7/1.0 frontier-provider"}, method="POST")\n        try:\n            context = ssl.create_default_context()\n            with urlopen(req, timeout=self.timeout, context=context) as response:\n                body = response.read(self.max_bytes + 1)\n                if len(body) > self.max_bytes: raise CapabilityUnavailable(f"{self.name}_response_too_large")\n                data = __import__("json").loads(body.decode("utf-8", "replace"))\n        except CapabilityUnavailable:\n            raise\n        except Exception as exc:\n            raise CapabilityUnavailable(f"{self.name}_provider_request_failed") from exc\n        if not isinstance(data, dict) or data.get("status") not in {"completed", "accepted"}:\n            raise CapabilityUnavailable(f"{self.name}_provider_contract_rejected")\n        return data'''
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

print("NORYX7 FRONTIER INTEGRATION WAVE 2 PATCHED")
