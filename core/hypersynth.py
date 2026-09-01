from dataclasses import dataclass
from typing import Any

from .audit import AuditLog
from .context import ContextManager
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .decomposition import TaskDecomposer
from .planning import Planner
from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator
from .supervisor import AgentSupervisor


@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0


class Hypersynth:
    """Bounded cognitive kernel with explicit phase and evidence integrity gates."""

    PHASES = ("perception", "context", "planning", "hypothesis", "simulation", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None, action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1: raise ValueError("max_steps must be a positive integer")
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or max_agents < 1: raise ValueError("max_agents must be a positive integer")
        self.verifier, self.router, self.max_steps, self.max_agents = verifier, router, max_steps, max_agents
        bounded_steps = min(max_steps, max_agents)
        self.planner = planner or Planner(max_steps=bounded_steps)
        self.decomposer = decomposer or TaskDecomposer()
        self.context_manager = context_manager or ContextManager()
        self.action_gate = action_gate
        self.audit = audit or AuditLog()
        self.supervisor = supervisor or AgentSupervisor(router, verifier, audit=self.audit)
        self.memory = memory
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.simulator = simulator or InternalSimulator()
        self.cross_checker = cross_checker or CrossChecker()

    def _state(self, phase, task, context, confidence=0.0):
        return CognitiveState(phase, task.task_id, context=context, confidence=confidence)

    def _reject(self, phase, task, check, **extra):
        self.audit.record("hypersynth_rejected", task_id=getattr(task, "task_id", None), phase=phase, reason=check.reason)
        result = {"status": "rejected", "phase": phase, "verification": check}
        result.update(extra)
        return result

    def _advance_phase(self, current_index, target_phase, task):
        if target_phase not in self.PHASES:
            return VerificationResult(False, "phase", "unknown_phase")
        target_index = self.PHASES.index(target_phase)
        if target_index != current_index + 1:
            return VerificationResult(False, "phase", "phase_order_violation")
        self.audit.record("phase_entered", task_id=task.task_id, phase=target_phase, index=target_index)
        return VerificationResult(True, "phase", "phase_order_ok")

    def _verify_agent_result(self, child: TaskSpec, agent, result: AgentResult) -> VerificationResult:
        if not isinstance(result, AgentResult):
            return VerificationResult(False, "agent_result", "invalid_agent_result")
        if not result.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_agent_result")
        if result.agent_id != getattr(agent, "agent_id", None):
            return VerificationResult(False, "agent_result", "agent_id_mismatch")
        if result.task_id != child.task_id:
            return VerificationResult(False, "agent_result", "task_id_mismatch")
        if result.status != "completed":
            return VerificationResult(False, "agent_result", "agent_not_completed")
        output_check = self.verifier.verify_output(result.output, requirements=child.verification_requirements, stage="runtime_output")
        if not output_check.valid:
            return output_check
        if result.verification is None or not result.verification.is_well_formed():
            return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.valid:
            return VerificationResult(False, "agent_result", "result_verification_failed")
        if result.verification.stage not in ("result", "agent_result", result.agent_id):
            return VerificationResult(False, "agent_result", "verification_identity_mismatch")
        return VerificationResult(True, "agent_result", "independent_result_verified")

    def _evidence_confidence(self, evidence: list[str], required: int) -> float:
        if required <= 0:
            return 0.0
        return min(1.0, max(0.0, len(evidence) / required))

    def run(self, task: TaskSpec):
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None))
        evidence: list[str] = []
        phase_index = 0
        task_check = self.verifier.verify_task(task)
        if not task_check.valid:
            return self._reject("perception", task, task_check)
        evidence.append("task_contract")
        self.audit.record("phase_verified", task_id=task.task_id, phase="perception")

        subtasks = self._decompose(task)
        if isinstance(subtasks, dict):
            return subtasks
        phase_check = self._advance_phase(phase_index, "context", task)
        if not phase_check.valid:
            return self._reject("context", task, phase_check)
        phase_index += 1
        if any(not getattr(s, "subtask_id", None) for s in subtasks):
            return self._reject("context", task, VerificationResult(False, "context", "invalid_subtask"))
        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))
        if context.task_id != task.task_id or context.source_ids != (task.task_id,):
            return self._reject("context", task, VerificationResult(False, "context", "context_identity_mismatch"))
        evidence.append("context_integrity")
        self.audit.record("context_acquired", task_id=task.task_id, version=context.version)

        phase_check = self._advance_phase(phase_index, "planning", task)
        if not phase_check.valid:
            return self._reject("planning", task, phase_check)
        phase_index += 1
        try:
            plan = self.planner.build(task)
            plan_check = self.planner.verify(plan, task)
        except Exception:
            plan_check, plan = VerificationResult(False, "planning", "planner_failure"), None
        if not plan_check.valid:
            return self._reject("planning", task, plan_check)
        if not plan.steps or len(plan.steps) > self.max_agents:
            return self._reject("planning", task, VerificationResult(False, "planning", "plan_exceeds_execution_bound"))
        evidence.append("plan_integrity")
        self.audit.record("plan_verified", task_id=task.task_id, steps=len(plan.steps))

        phase_check = self._advance_phase(phase_index, "hypothesis", task)
        if not phase_check.valid:
            return self._reject("hypothesis", task, phase_check)
        phase_index += 1
        try:
            hypotheses = self.hypothesis_engine.generate(task, plan)
            hypothesis_check = self.hypothesis_engine.verify(hypotheses, task)
        except Exception:
            return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_failure"))
        if not hypothesis_check.valid or len(hypotheses) != len(plan.steps):
            return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))
        evidence.append("hypothesis_integrity")
        self.audit.record("hypotheses_verified", task_id=task.task_id, count=len(hypotheses))

        phase_check = self._advance_phase(phase_index, "simulation", task)
        if not phase_check.valid:
            return self._reject("simulation", task, phase_check)
        phase_index += 1
        try:
            simulations = self.simulator.simulate(task, hypotheses)
            simulation_check = self.simulator.verify(simulations)
        except Exception:
            return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_failure"))
        if not simulation_check.valid:
            return self._reject("simulation", task, simulation_check)
        expected_hypothesis_ids = tuple(h.hypothesis_id for h in hypotheses)
        actual_simulation_ids = tuple(s.hypothesis_id for s in simulations)
        if actual_simulation_ids != expected_hypothesis_ids:
            return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))
        if len(simulations) != len(hypotheses):
            return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_mismatch"))
        evidence.append("simulation_integrity")
        self.audit.record("simulation_verified", task_id=task.task_id, count=len(simulations))

        phase_check = self._advance_phase(phase_index, "allocation", task)
        if not phase_check.valid:
            return self._reject("allocation", task, phase_check)
        phase_index += 1
        assignments = []
        agents = self.router.available()
        if not agents:
            return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        for index, step in enumerate(plan.steps):
            agent_id = agents[index % len(agents)]
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input, task.constraints, task.verification_requirements, step.risk_class)
            try:
                selected, decision = self.supervisor.select(child, preferred=agent_id)
            except Exception:
                return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_selection_failure"))
            if not decision.accepted or selected is None:
                return self._reject("allocation", task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step))
        if len(assignments) != len(plan.steps):
            return self._reject("allocation", task, VerificationResult(False, "allocation", "assignment_count_mismatch"))
        evidence.append("allocation_integrity")

        phase_check = self._advance_phase(phase_index, "execution", task)
        if not phase_check.valid:
            return self._reject("execution", task, phase_check)
        phase_index += 1
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
                return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))
            results.append(result)
        if len(results) != len(assignments):
            return self._reject("execution", task, VerificationResult(False, "execution", "result_count_mismatch"), results=tuple(results))
        evidence.append("execution_integrity")

        phase_check = self._advance_phase(phase_index, "verification", task)
        if not phase_check.valid:
            return self._reject("verification", task, phase_check, results=tuple(results))
        phase_index += 1
        for index, (agent, child, _step) in enumerate(assignments):
            check = self._verify_agent_result(child, agent, results[index])
            if not check.valid:
                return self._reject("verification", task, check, results=tuple(results))
        cross_check = self.cross_checker.verify(task, tuple(results), hypotheses)
        if not cross_check.valid:
            return self._reject("verification", task, cross_check, results=tuple(results), hypotheses=hypotheses)
        if len({r.task_id for r in results}) == 1:
            consensus = self._verify_consensus(tuple(results))
            if not consensus.valid:
                return self._reject("verification", task, consensus, results=tuple(results))
        final_output = results[-1].output
        output_check = self.verifier.verify_output(final_output, requirements=task.verification_requirements, stage="hypersynth_result")
        if not output_check.valid:
            return self._reject("verification", task, output_check, results=tuple(results))
        evidence.append("result_integrity")
        evidence.append("cross_check")
        self.audit.record("agent_results_independently_verified", task_id=task.task_id, count=len(results))

        phase_check = self._advance_phase(phase_index, "metacognition", task)
        if not phase_check.valid:
            return self._reject("metacognition", task, phase_check, results=tuple(results))
        confidence = self._evidence_confidence(evidence, 9)
        reflection = {
            "result_verified": True,
            "agents_used": tuple(r.agent_id for r in results),
            "steps_executed": len(results),
            "hypotheses_verified": len(hypotheses),
            "simulations_verified": len(simulations),
            "evidence_count": len(evidence),
            "evidence_required": 9,
            "confidence": confidence,
        }
        if self.memory is not None:
            try:
                from .memory import MemoryItem
                self.memory.put(MemoryItem("task:" + task.task_id, final_output, kind="working", source=task.task_id, importance=0.5))
            except Exception:
                self.audit.record("memory_write_failed", task_id=task.task_id)
        final_state = self._state("metacognition", task, context, confidence=confidence)
        self.audit.record("hypersynth_complete", task_id=task.task_id, status="completed", confidence=confidence, evidence_count=len(evidence))
        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "audit": self.audit.snapshot()}

    def _decompose(self, task):
        try:
            subtasks = self.decomposer.decompose(task)
        except Exception:
            return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if not subtasks:
            return self._reject("context", task, VerificationResult(False, "decomposition", "no_subtasks"))
        return subtasks

    def _verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not results:
            return VerificationResult(False, "consensus", "no_results")
        if any(r.status != "completed" for r in results):
            return VerificationResult(False, "consensus", "incomplete_result")
        if len({r.agent_id for r in results}) != len(results):
            return VerificationResult(False, "consensus", "duplicate_agent_result")
        if any(r.verification is None or not r.verification.valid for r in results):
            return VerificationResult(False, "consensus", "unverified_result")
        outputs = {repr(r.output) for r in results}
        if len(outputs) > 1:
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
