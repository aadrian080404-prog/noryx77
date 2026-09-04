from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .actions import ActionGate, ActionSpec
from .audit import AuditLog
from .context import ContextManager
from .contracts import AgentResult, TaskSpec, VerificationResult
from .decomposition import Subtask, TaskDecomposer
from .limits import RuntimeLimits
from .planning import Planner
from .policy import PolicyEngine
from .reasoning import CrossChecker, HypothesisEngine, InternalSimulator
from .security import SecurityBoundary
from .supervisor import AgentSupervisor
from .metacognition import MetacognitionEngine
from .provenance import ProvenanceContext, canonical_digest, seal_provenance, verify_provenance


@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0
    execution_id: str = ""


class Hypersynth:
    """Bounded cognitive kernel with immutable execution and optional cryptographic provenance."""
    PHASES = ("perception", "context", "planning", "hypothesis", "simulation", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None, action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None, provenance_key=None, runtime_id="", model_fabric=None):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1: raise ValueError("max_steps must be a positive integer")
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or max_agents < 1: raise ValueError("max_agents must be a positive integer")
        if provenance_key is not None and (not isinstance(provenance_key, bytes) or len(provenance_key) < 32): raise ValueError("provenance key must contain at least 32 bytes")
        if not isinstance(runtime_id, str) or len(runtime_id.encode("utf-8")) > 256: raise ValueError("invalid runtime_id")
        if model_fabric is not None and getattr(model_fabric, "runtime_id", None) != runtime_id: raise ValueError("model_fabric runtime identity mismatch")
        self.verifier, self.router, self.max_steps, self.max_agents = verifier, router, max_steps, max_agents
        self.provenance_key = bytes(provenance_key) if provenance_key is not None else None
        self.runtime_id = runtime_id
        self.model_fabric = model_fabric
        bounded_steps = min(max_steps, max_agents)
        self.planner = planner or Planner(max_steps=bounded_steps)
        self.decomposer = decomposer or TaskDecomposer()
        self.context_manager = context_manager or ContextManager()
        if action_gate is None:
            policy = PolicyEngine()
            security = SecurityBoundary(policy, verifier)
            action_gate = ActionGate(policy, security, RuntimeLimits(max_actions_per_task=bounded_steps))
        if not isinstance(action_gate, ActionGate): raise ValueError("invalid_action_gate")
        self.action_gate = action_gate
        self.audit = audit or AuditLog()
        self.supervisor = supervisor or AgentSupervisor(router, verifier, audit=self.audit)
        self.memory = memory
        self.hypothesis_engine = hypothesis_engine or HypothesisEngine()
        self.simulator = simulator or InternalSimulator()
        self.cross_checker = cross_checker or CrossChecker()
        self.metacognition = metacognition or MetacognitionEngine()

    def _state(self, phase, task, context, confidence=0.0): return CognitiveState(phase, task.task_id, context=context, confidence=confidence, execution_id=task.execution_id)
    def _reject(self, phase, task, check, **extra):
        self.audit.record("hypersynth_rejected", task_id=getattr(task, "task_id", None), phase=phase, reason=check.reason, execution_id=getattr(task, "execution_id", ""))
        result = {"status": "rejected", "phase": phase, "verification": check}; result.update(extra); return result
    @staticmethod
    def _accepts_verification(check, stage: str) -> bool: return isinstance(check, VerificationResult) and check.is_well_formed() and check.valid and check.stage == stage
    def _deadline_rejection(self, task, phase, deadline_check):
        if deadline_check is not None and deadline_check(): return self._reject(phase, task, VerificationResult(False, "limits", "task_time_limit_exceeded"))
        return None
    @staticmethod
    def _bind_execution(task: TaskSpec) -> TaskSpec:
        if not isinstance(task, TaskSpec): return task
        if task.execution_id: return task
        return TaskSpec(task.task_id, task.task_type, task.objective, task.input, task.constraints, task.verification_requirements, task.risk_class, uuid4().hex)

    def _provenance_start(self, task, route_digest=""):
        if self.provenance_key is None: return None
        principal_id = task.constraints.get("principal_id", "") if hasattr(task.constraints, "get") else ""
        if not isinstance(principal_id, str) or not principal_id.strip(): raise ValueError("missing_provenance_principal")
        runtime_id = self.runtime_id or task.constraints.get("runtime_id", "")
        if not runtime_id: raise ValueError("missing_provenance_runtime")
        memory_digest = canonical_digest(tuple(self.memory.list(execution_id=task.execution_id))) if self.memory is not None else canonical_digest(())
        return ProvenanceContext(runtime_id, task.execution_id, principal_id, memory_digest, route_digest or canonical_digest(()), canonical_digest(task))

    def _provenance_verify(self, context):
        if context is None: return True
        return verify_provenance(context, seal_provenance(context, self.provenance_key), self.provenance_key)

    def run(self, task: TaskSpec, *, deadline_check=None):
        task = self._bind_execution(task)
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None), execution_id=getattr(task, "execution_id", ""))
        try: task_check = self.verifier.verify_task(task)
        except Exception: return self._reject("perception", task, VerificationResult(False, "contract", "task_verification_failure"))
        if not self._accepts_verification(task_check, "contract"):
            check = task_check if isinstance(task_check, VerificationResult) and task_check.is_well_formed() else VerificationResult(False, "contract", "invalid_task_verification")
            return self._reject("perception", task, check)
        timeout = self._deadline_rejection(task, "perception", deadline_check)
        if timeout: return timeout
        try: subtasks = self._decompose(task)
        except Exception: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if isinstance(subtasks, dict): return subtasks
        timeout = self._deadline_rejection(task, "context", deadline_check)
        if timeout: return timeout
        context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))
        timeout = self._deadline_rejection(task, "planning", deadline_check)
        if timeout: return timeout
        try: plan = self.planner.build(task); plan_check = self.planner.verify(plan, task)
        except Exception: plan_check, plan = VerificationResult(False, "planning", "planner_failure"), None
        if not self._accepts_verification(plan_check, "plan"): return self._reject("planning", task, plan_check if isinstance(plan_check, VerificationResult) and plan_check.is_well_formed() else VerificationResult(False, "plan", "invalid_plan_verification"))
        if not plan.steps or len(plan.steps) > self.max_agents: return self._reject("planning", task, VerificationResult(False, "planning", "plan_exceeds_execution_bound"))
        timeout = self._deadline_rejection(task, "hypothesis", deadline_check)
        if timeout: return timeout
        try: hypotheses = self.hypothesis_engine.generate(task, plan); hypothesis_check = self.hypothesis_engine.verify(hypotheses, task)
        except Exception: return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_failure"))
        if not self._accepts_verification(hypothesis_check, "hypothesis"): return self._reject("hypothesis", task, hypothesis_check if isinstance(hypothesis_check, VerificationResult) and hypothesis_check.is_well_formed() else VerificationResult(False, "hypothesis", "invalid_hypothesis_verification"))
        if len(hypotheses) != len(plan.steps): return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))
        timeout = self._deadline_rejection(task, "simulation", deadline_check)
        if timeout: return timeout
        try: simulations = self.simulator.simulate(task, hypotheses); simulation_check = self.simulator.verify(simulations)
        except Exception: return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_failure"))
        if not self._accepts_verification(simulation_check, "simulation"): return self._reject("simulation", task, simulation_check if isinstance(simulation_check, VerificationResult) and simulation_check.is_well_formed() else VerificationResult(False, "simulation", "invalid_simulation_verification"))
        if tuple(s.hypothesis_id for s in simulations) != tuple(h.hypothesis_id for h in hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))
        if len(simulations) != len(hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_mismatch"))
        timeout = self._deadline_rejection(task, "allocation", deadline_check)
        if timeout: return timeout
        agents = self.router.available()
        if not agents: return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        assignments = []
        for index, step in enumerate(plan.steps):
            agent_id = "model_fabric" if self.model_fabric is not None else agents[index % len(agents)]
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input, task.constraints, task.verification_requirements, step.risk_class, task.execution_id)
            try: selected, decision = self.supervisor.select(child, preferred=agent_id)
            except Exception: return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_selection_failure"))
            if not decision.accepted or selected is None: return self._reject("allocation", task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step))
        try:
            route_digest = canonical_digest(tuple((child.task_id, agent.agent_id, step.action_type, step.risk_class) for agent, child, step in assignments))
            provenance = self._provenance_start(task, route_digest)
            if provenance is not None and not self._provenance_verify(provenance): return self._reject("allocation", task, VerificationResult(False, "provenance", "provenance_seal_failure"))
        except Exception as exc:
            return self._reject("allocation", task, VerificationResult(False, "provenance", str(exc)))
        results = []
        for index, (agent, child, step) in enumerate(assignments):
            timeout = self._deadline_rejection(task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            action = ActionSpec("act:" + child.task_id, step.action_type, risk_class=step.risk_class, execution_id=task.execution_id)
            try:
                decision, result = self.action_gate.authorize_and_execute(action, lambda: agent.run(child), calls_used=index, execution_id=task.execution_id)
                if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))
            except Exception: return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))
            timeout = self._deadline_rejection(task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            admission = self.supervisor.admit(child, result, selected_agent_id=agent.agent_id)
            if not admission.valid: return self._reject("verification", task, admission, results=tuple(results))
            if not isinstance(result, AgentResult): return self._reject("verification", task, VerificationResult(False, "agent_result", "malformed_agent_result"), results=tuple(results))
            if result.execution_id != task.execution_id: return self._reject("verification", task, VerificationResult(False, "agent_result", "execution_identity_mismatch"), results=tuple(results))
            results.append(result)
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
        if not self._accepts_verification(output_check, "hypersynth_result"): return self._reject("verification", task, output_check if isinstance(output_check, VerificationResult) and output_check.is_well_formed() else VerificationResult(False, "hypersynth_result", "invalid_output_verification"), results=tuple(results))
        if provenance is not None:
            try:
                provenance = provenance.bind_result(final_output)
                provenance_seal = seal_provenance(provenance, self.provenance_key)
                if not verify_provenance(provenance, provenance_seal, self.provenance_key): return self._reject("verification", task, VerificationResult(False, "provenance", "result_provenance_failure"), results=tuple(results))
            except Exception: return self._reject("verification", task, VerificationResult(False, "provenance", "result_provenance_failure"), results=tuple(results))
        metacognitive_check, reflection = self.metacognition.reflect(task, plan, hypotheses, simulations, tuple(results), output_check)
        if not isinstance(metacognitive_check, VerificationResult) or not metacognitive_check.is_well_formed() or not metacognitive_check.valid: return self._reject("metacognition", task, metacognitive_check if isinstance(metacognitive_check, VerificationResult) else VerificationResult(False, "metacognition", "invalid_metacognition_result"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if metacognitive_check.stage != "metacognition": return self._reject("metacognition", task, VerificationResult(False, "metacognition", "metacognition_stage_mismatch"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if self.memory is not None:
            try:
                from .memory import MemoryItem
                memory_key = "task:" + task.execution_id + ":" + task.task_id
                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=task.task_id, importance=0.5, execution_id=task.execution_id))
            except Exception: return self._reject("verification", task, VerificationResult(False, "memory", "memory_persistence_failure"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        final_state = self._state("metacognition", task, context, confidence=reflection.confidence)
        response = {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": task.execution_id, "audit": self.audit.snapshot()}
        if provenance is not None: response["provenance"] = provenance; response["provenance_seal"] = provenance_seal
        return response

    def _decompose(self, task):
        try: subtasks = self.decomposer.decompose(task)
        except Exception: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if not isinstance(subtasks, tuple) or not subtasks: return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_collection"))
        seen = set()
        for subtask in subtasks:
            if not isinstance(subtask, Subtask): return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask"))
            if subtask.subtask_id in seen: return self._reject("context", task, VerificationResult(False, "decomposition", "duplicate_subtask_id"))
            seen.add(subtask.subtask_id)
        return subtasks

    @staticmethod
    def _verify_consensus(results):
        outputs = [canonical_digest(result.output) for result in results]
        return VerificationResult(len(set(outputs)) == 1, "consensus", "" if len(set(outputs)) == 1 else "consensus_mismatch")
