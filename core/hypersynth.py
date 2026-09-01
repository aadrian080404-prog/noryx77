from dataclasses import dataclass
from typing import Any

from .actions import ActionGate
from .audit import AuditLog
from .context import ContextManager, ContextSnapshot
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .decomposition import TaskDecomposer
from .planning import Planner
from .supervisor import AgentSupervisor


@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0


class Hypersynth:
    """Bounded cognitive kernel: perceive -> context -> plan -> allocate -> execute -> verify -> reflect."""

    PHASES = ("perception", "context", "planning", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None,
                 action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2):
        self.verifier = verifier
        self.router = router
        self.planner = planner or Planner(max_steps=max_steps)
        self.decomposer = decomposer or TaskDecomposer()
        self.context_manager = context_manager or ContextManager()
        self.action_gate = action_gate
        self.supervisor = supervisor or AgentSupervisor(router, verifier, audit=audit)
        self.memory = memory
        self.audit = audit or AuditLog()
        self.max_steps = max_steps
        self.max_agents = max_agents

    def _state(self, phase, task, context, confidence=0.0):
        return CognitiveState(phase, task.task_id, context=context, confidence=confidence)

    def _reject(self, phase, task, check, **extra):
        self.audit.record("hypersynth_rejected", task_id=task.task_id, phase=phase, reason=check.reason)
        result = {"status": "rejected", "phase": phase, "verification": check}
        result.update(extra)
        return result

    def run(self, task: TaskSpec):
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None))

        task_check = self.verifier.verify_task(task)
        if not task_check.valid:
            return self._reject("perception", task, task_check)
        state = self._state("perception", task, task.input)

        try:
            subtasks = self.decomposer.decompose(task)
        except Exception:
            check = VerificationResult(False, "decomposition", "decomposition_failure")
            return self._reject("context", task, check)
        if not subtasks:
            return self._reject("context", task, VerificationResult(False, "decomposition", "no_subtasks"))

        context = self.context_manager.build(
            task.task_id,
            {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)},
            source_ids=(task.task_id,),
        )
        state = self._state("context", task, context)
        self.audit.record("context_acquired", task_id=task.task_id, version=context.version)

        plan = self.planner.build(task)
        plan_check = self.planner.verify(plan, task)
        if not plan_check.valid:
            return self._reject("planning", task, plan_check)
        state = self._state("planning", task, context)
        self.audit.record("plan_verified", task_id=task.task_id, steps=len(plan.steps))

        assignments = []
        agents = self.router.available()
        if not agents:
            return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        for index, step in enumerate(plan.steps[:self.max_agents]):
            agent_id = agents[index % len(agents)]
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input,
                             task.constraints, task.verification_requirements, step.risk_class)
            selected, decision = self.supervisor.select(child, preferred=agent_id)
            if not decision.accepted or selected is None:
                return self._reject("allocation", task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step))
        state = self._state("allocation", task, context)

        results = []
        for index, (agent, child, step) in enumerate(assignments):
            action = ActionSpec("act:" + child.task_id, step.action_type, risk_class=step.risk_class)
            if self.action_gate is not None:
                decision = self.action_gate.authorize(action, calls_used=index)
                self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
                if not decision.allowed:
                    return self._reject("execution", task, decision.verification, results=tuple(results))
            try:
                result = agent.run(child)
            except Exception:
                check = VerificationResult(False, "execution", "agent_execution_failure")
                return self._reject("execution", task, check, results=tuple(results))
            admission = self.supervisor.admit(child, result)
            if not admission.valid:
                return self._reject("verification", task, admission, results=tuple(results))
            if result.verification is None or not result.verification.valid:
                return self._reject("verification", task, VerificationResult(False, "agent_result", "missing_verification"), results=tuple(results))
            results.append(result)
            self.audit.record("agent_result_verified", task_id=child.task_id, agent_id=agent.agent_id)

        state = self._state("execution", task, context)
        consensus = self._verify_consensus(results)
        if not consensus.valid:
            return self._reject("verification", task, consensus, results=tuple(results))

        final_output = results[-1].output
        output_check = self.verifier.verify_output(final_output, stage="hypersynth_result")
        if not output_check.valid:
            return self._reject("verification", task, output_check, results=tuple(results))

        # Metacognition is deliberately a high-level validation summary, never hidden chain-of-thought.
        reflection = {
            "result_verified": True,
            "agents_used": tuple(r.agent_id for r in results),
            "steps_executed": len(results),
            "confidence": 1.0,
        }
        if self.memory is not None:
            try:
                from .memory import MemoryItem
                self.memory.put(MemoryItem("task:" + task.task_id, final_output, kind="working", source=task.task_id, importance=0.5))
            except Exception:
                self.audit.record("memory_write_failed", task_id=task.task_id)

        final_state = self._state("metacognition", task, context, confidence=1.0)
        self.audit.record("hypersynth_complete", task_id=task.task_id, status="completed")
        return {
            "status": "completed",
            "phase": final_state.phase,
            "state": final_state,
            "context": context,
            "plan": plan,
            "results": tuple(results),
            "verification": output_check,
            "reflection": reflection,
            "audit": self.audit.snapshot(),
        }

    def _verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not results:
            return VerificationResult(False, "consensus", "no_results")
        if any(r.status != "completed" for r in results):
            return VerificationResult(False, "consensus", "incomplete_result")
        outputs = {repr(r.output) for r in results}
        if len(outputs) > 1:
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
