from dataclasses import dataclass
from typing import Any

from .audit import AuditLog
from .context import ContextManager
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .decomposition import TaskDecomposer
from .planning import Planner
from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator
from .supervisor import AgentSupervisor
from .metacognition import MetacognitionEngine


@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0


class Hypersynth:
    """Bounded cognitive kernel: perceive -> context -> plan -> reason -> allocate -> execute -> verify -> reflect."""

    PHASES = ("perception", "context", "planning", "hypothesis", "simulation", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None, action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None):
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
        self.metacognition = metacognition or MetacognitionEngine()

    def _state(self, phase, task, context, confidence=0.0): return CognitiveState(phase, task.task_id, context=context, confidence=confidence)

    def _reject(self, phase, task, check, **extra):
        self.audit.record("hypersynth_rejected", task_id=getattr(task, "task_id", None), phase=phase, reason=check.reason)
        result = {"status": "rejected", "phase": phase, "verification": check}; result.update(extra); return result

    @staticmethod
    def _accepts_verification(check, stage: str) -> bool:
        return isinstance(check, VerificationResult) and check.is_well_formed() and check.valid and check.stage == stage

    def _deadline_rejection(self, task, phase, deadline_check):
        if deadline_check is not None and deadline_check():
            return self._reject(phase, task, VerificationResult(False, "limits", "task_time_limit_exceeded"))
        return None

    def run(self, task: TaskSpec, *, deadline_check=None):
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None))
        try:
            task_check = self.verifier.verify_task(task)
        except Exception:
            return self._reject("perception", task, VerificationResult(False, "task", "task_verification_failure"))
        if not self._accepts_verification(task_check, "task"):
            check = task_check if isinstance(task_check, VerificationResult) and task_check.is_well_formed() else VerificationResult(False, "task", "invalid_task_verification")
            return self._reject("perception", task, check)
        timeout = self._deadline_rejection(task, "perception", deadline_check)
        if timeout: return timeout
        subtasks = self._decompose(task)
        if isinstance(subtasks, dict): return subtasks
        timeout = self._deadline_rejection(task, "context", deadline_check)
        if timeout: return timeout
        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))
        self.audit.record("context_acquired", task_id=task.task_id, version=context.version)
        timeout = self._deadline_rejection(task, "planning", deadline_check)
        if timeout: return timeout
        try: plan = self.planner.build(task); plan_check = self.planner.verify(plan, task)
        except Exception: plan_check, plan = VerificationResult(False, "planning", "planner_failure"), None
        if not self._accepts_verification(plan_check, "plan"):
            check = plan_check if isinstance(plan_check, VerificationResult) and plan_check.is_well_formed() else VerificationResult(False, "plan", "invalid_plan_verification")
            return self._reject("planning", task, check)
        if not plan.steps or len(plan.steps) > self.max_agents: return self._reject("planning", task, VerificationResult(False, "planning", "plan_exceeds_execution_bound"))
        self.audit.record("plan_verified", task_id=task.task_id, steps=len(plan.steps))
        timeout = self._deadline_rejection(task, "hypothesis", deadline_check)
        if timeout: return timeout
        try: hypotheses = self.hypothesis_engine.generate(task, plan); hypothesis_check = self.hypothesis_engine.verify(hypotheses, task)
        except Exception: return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_failure"))
        if not self._accepts_verification(hypothesis_check, "hypothesis"):
            check = hypothesis_check if isinstance(hypothesis_check, VerificationResult) and hypothesis_check.is_well_formed() else VerificationResult(False, "hypothesis", "invalid_hypothesis_verification")
            return self._reject("hypothesis", task, check)
        if len(hypotheses) != len(plan.steps): return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))
        self.audit.record("hypotheses_verified", task_id=task.task_id, count=len(hypotheses))
        timeout = self._deadline_rejection(task, "simulation", deadline_check)
        if timeout: return timeout
        try: simulations = self.simulator.simulate(task, hypotheses); simulation_check = self.simulator.verify(simulations)
        except Exception: return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_failure"))
        if not self._accepts_verification(simulation_check, "simulation"):
            check = simulation_check if isinstance(simulation_check, VerificationResult) and simulation_check.is_well_formed() else VerificationResult(False, "simulation", "invalid_simulation_verification")
            return self._reject("simulation", task, check)
        expected_hypothesis_ids = tuple(h.hypothesis_id for h in hypotheses)
        actual_simulation_ids = tuple(s.hypothesis_id for s in simulations)
        if actual_simulation_ids != expected_hypothesis_ids: return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))
        if len(simulations) != len(hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_mismatch"))
        self.audit.record("simulation_verified", task_id=task.task_id, count=len(simulations))
        timeout = self._deadline_rejection(task, "allocation", deadline_check)
        if timeout: return timeout
        assignments = []
        agents = self.router.available()
        if not agents: return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        for index, step in enumerate(plan.steps):
            agent_id = agents[index % len(agents)]
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input, task.constraints, task.verification_requirements, step.risk_class)
            try: selected, decision = self.supervisor.select(child, preferred=agent_id)
            except Exception: return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_selection_failure"))
            if not decision.accepted or selected is None: return self._reject("allocation", task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step))
        results = []
        for index, (agent, child, step) in enumerate(assignments):
            timeout = self._deadline_rejection(task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            action = ActionSpec("act:" + child.task_id, step.action_type, risk_class=step.risk_class)
            if self.action_gate is not None:
                decision = self.action_gate.authorize(action, calls_used=index)
                self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
                if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))
            try: result = agent.run(child)
            except Exception: return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))
            timeout = self._deadline_rejection(task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            admission = self.supervisor.admit(child, result, selected_agent_id=agent.agent_id)
            if not admission.valid: return self._reject("verification", task, admission, results=tuple(results))
            results.append(result)
            self.audit.record("agent_result_verified", task_id=child.task_id, agent_id=agent.agent_id)
        timeout = self._deadline_rejection(task, "verification", deadline_check)
        if timeout: return dict(timeout, results=tuple(results))
        cross_check = self.cross_checker.verify(task, tuple(results), hypotheses)
        if not cross_check.valid: return self._reject("verification", task, cross_check, results=tuple(results), hypotheses=hypotheses)
        if len({r.task_id for r in results}) == 1:
            consensus = self._verify_consensus(tuple(results))
            if not consensus.valid: return self._reject("verification", task, consensus, results=tuple(results))
        timeout = self._deadline_rejection(task, "metacognition", deadline_check)
        if timeout: return dict(timeout, results=tuple(results))
        final_output = results[-1].output
        try: output_check = self.verifier.verify_output(final_output, stage="hypersynth_result")
        except Exception: return self._reject("verification", task, VerificationResult(False, "hypersynth_result", "output_verification_failure"), results=tuple(results))
        if not self._accepts_verification(output_check, "hypersynth_result"):
            check = output_check if isinstance(output_check, VerificationResult) and output_check.is_well_formed() else VerificationResult(False, "hypersynth_result", "invalid_output_verification")
            return self._reject("verification", task, check, results=tuple(results))
        metacognitive_check, reflection = self.metacognition.reflect(task, plan, hypotheses, simulations, tuple(results), output_check)
        if not isinstance(metacognitive_check, VerificationResult) or not metacognitive_check.is_well_formed() or not metacognitive_check.valid:
            check = metacognitive_check if isinstance(metacognitive_check, VerificationResult) else VerificationResult(False, "metacognition", "invalid_metacognition_result")
            return self._reject("metacognition", task, check, results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if metacognitive_check.stage != "metacognition":
            return self._reject("metacognition", task, VerificationResult(False, "metacognition", "metacognition_stage_mismatch"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        self.audit.record("metacognition_verified", task_id=task.task_id, confidence=reflection.confidence)
        if self.memory is not None:
            try:
                from .memory import MemoryItem
                self.memory.put(MemoryItem("task:" + task.task_id, final_output, kind="working", source=task.task_id, importance=0.5))
            except Exception: self.audit.record("memory_write_failed", task_id=task.task_id)
        final_state = self._state("metacognition", task, context, confidence=reflection.confidence)
        self.audit.record("hypersynth_complete", task_id=task.task_id, status="completed")
        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "audit": self.audit.snapshot()}

    def _decompose(self, task):
        try: subtasks = self.decomposer.decompose(task)
        except Exception: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if not subtasks: return self._reject("context", task, VerificationResult(False, "decomposition", "no_subtasks"))
        return subtasks

    def _verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not isinstance(results, tuple) or not results:
            return VerificationResult(False, "consensus", "no_results")
        if any(not isinstance(r, AgentResult) or not r.is_well_formed() for r in results):
            return VerificationResult(False, "consensus", "malformed_result")
        if any(r.status != "completed" for r in results):
            return VerificationResult(False, "consensus", "incomplete_result")
        if len({r.agent_id for r in results}) != len(results):
            return VerificationResult(False, "consensus", "duplicate_agent_result")
        if len({r.task_id for r in results}) != 1:
            return VerificationResult(False, "consensus", "task_identity_mismatch")
        if any(r.verification is None or not r.verification.is_well_formed() or not r.verification.valid for r in results):
            return VerificationResult(False, "consensus", "unverified_result")
        if any(r.verification.stage != "agent_result" for r in results):
            return VerificationResult(False, "consensus", "verification_stage_mismatch")
        outputs = [r.output for r in results]
        if any(output != outputs[0] for output in outputs[1:]):
            return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
