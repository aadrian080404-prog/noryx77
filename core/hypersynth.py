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
    """Bounded cognitive kernel with immutable execution and cryptographic provenance."""
    PHASES = ("perception", "context", "planning", "hypothesis", "simulation", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None, action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None, provenance_key=None, runtime_id="", model_fabric=None):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1: raise ValueError("max_steps must be a positive integer")
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or max_agents < 1: raise ValueError("max_agents must be a positive integer")
        if provenance_key is not None and (not isinstance(provenance_key, bytes) or len(provenance_key) < 32): raise ValueError("provenance key must contain at least 32 bytes")
        if not isinstance(runtime_id, str) or len(runtime_id.encode("utf-8")) > 256: raise ValueError("invalid runtime_id")
        self.verifier, self.router, self.max_steps, self.max_agents = verifier, router, max_steps, max_agents
        self.provenance_key = bytes(provenance_key) if provenance_key is not None else None
        self.runtime_id = runtime_id
        self.model_fabric = model_fabric
        if self.model_fabric is not None and self.runtime_id and getattr(self.model_fabric, "runtime_id", None) != self.runtime_id: raise ValueError("model_fabric runtime identity mismatch")
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

    def _provenance_verify(self, context): return context is None or verify_provenance(context, seal_provenance(context, self.provenance_key), self.provenance_key)

    def _model_agent(self, task, step):
        if self.model_fabric is None: return None, None
        from .agents import Agent
        from noryx7_runtime.model_fabric import ModelRequest
        constraints = task.constraints if hasattr(task.constraints, "get") else {}
        capabilities = constraints.get("required_capabilities", ())
        preferred = constraints.get("preferred_capabilities", ())
        tools = constraints.get("tools", ())
        raw_max_cost = constraints.get("max_cost")
        raw_max_latency = constraints.get("max_latency_ms")
        raw_min_models = constraints.get("min_models", 1)
        raw_max_models = constraints.get("max_models", self.max_agents)
        try:
            min_models = int(raw_min_models)
            max_models = int(raw_max_models)
        except (TypeError, ValueError):
            raise ValueError("invalid model fan-out")
        min_models = max(1, min(self.max_agents, min_models))
        max_models = max(min_models, min(self.max_agents, max_models))
        if raw_max_cost is not None and (not isinstance(raw_max_cost, (int, float)) or isinstance(raw_max_cost, bool) or raw_max_cost < 0):
            raise ValueError("invalid model cost limit")
        if raw_max_latency is not None and (not isinstance(raw_max_latency, (int, float)) or isinstance(raw_max_latency, bool) or raw_max_latency <= 0):
            raise ValueError("invalid model latency limit")
        request = ModelRequest(
            prompt=step.objective,
            required_capabilities=frozenset(capabilities),
            preferred_capabilities=frozenset(preferred),
            max_cost=raw_max_cost,
            max_latency_ms=raw_max_latency,
            min_models=min_models,
            max_models=max_models,
            tools=tuple(tools),
            runtime_id=self.runtime_id,
        )
        fabric = self.model_fabric
        class FabricAgent(Agent):
            def __init__(self):
                super().__init__("model-fabric")
                self.last_fabric_result = None
            def run(self, child):
                result = fabric.execute(request)
                if not fabric.verify_result(request, result): raise RuntimeError("model_result_integrity_failure")
                self.last_fabric_result = result
                verification = VerificationResult(True, "agent_result", "model_fabric_verified")
                return AgentResult(self.agent_id, child.task_id, "completed", result.output, verification, child.execution_id)
        return FabricAgent(), request

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
        if self.model_fabric is not None: agents = tuple(agents) + ("model-fabric",)
        if not agents: return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        assignments = []
        for index, step in enumerate(plan.steps):
            agent_id = agents[index % len(agents)]
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input, task.constraints, task.verification_requirements, step.risk_class, task.execution_id)
            try:
                if agent_id == "model-fabric": selected, request = self._model_agent(task, step); decision = type("Decision", (), {"accepted": selected is not None, "reason": "model_fabric_selected"})()
                else: selected, decision = self.supervisor.select(child, preferred=agent_id); request = None
            except Exception: return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_selection_failure"))
            if not decision.accepted or selected is None: return self._reject("allocation", task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step, request))
        try:
            route_digest = canonical_digest(tuple((child.task_id, agent.agent_id, step.action_type, step.risk_class) for agent, child, step, _ in assignments))
            provenance = self._provenance_start(task, route_digest)
            if provenance is not None and not self._provenance_verify(provenance): return self._reject("allocation", task, VerificationResult(False, "provenance", "provenance_seal_failure"))
        except Exception as exc: return self._reject("allocation", task, VerificationResult(False, "provenance", str(exc)))
        results = []
        for index, (agent, child, step, request) in enumerate(assignments):
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
            if provenance is not None and request is not None:
                fabric_result = getattr(agent, "last_fabric_result", None)
                if fabric_result is None or not self.model_fabric.verify_result(request, fabric_result):
                    return self._reject("verification", task, VerificationResult(False, "provenance", "model_result_integrity_failure"), results=tuple(results))
                try:
                    provenance = provenance.bind_model(fabric_result.request_digest, fabric_result)
                except Exception:
                    return self._reject("verification", task, VerificationResult(False, "provenance", "model_provenance_binding_failure"), results=tuple(results))
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
        provenance_seal = None
        if provenance is not None:
            try: provenance = provenance.bind_result(final_output); provenance_seal = seal_provenance(provenance, self.provenance_key)
            except Exception: return self._reject("verification", task, VerificationResult(False, "provenance", "provenance_binding_failure"), results=tuple(results))
            if not verify_provenance(provenance, provenance_seal, self.provenance_key): return self._reject("verification", task, VerificationResult(False, "provenance", "provenance_seal_failure"), results=tuple(results))
        reflection = self.metacognition.reflect(task, plan, hypotheses, simulations, tuple(results), output_check)
        if not reflection[0].valid: return self._reject("metacognition", task, reflection[0], results=tuple(results))
        self._persist_memory(task, final_output, reflection[1])
        self.audit.record("hypersynth_completed", task_id=task.task_id, execution_id=task.execution_id)
        return {"status": "completed", "phase": "metacognition", "execution_id": task.execution_id, "state": self._state("metacognition", task, context, reflection[1].confidence), "results": tuple(results), "hypotheses": hypotheses, "simulations": simulations, "reflection": reflection[1], "provenance": provenance, "provenance_seal": provenance_seal, "verification": output_check, "verified": True, "audit": self.audit.snapshot()}

    def _decompose(self, task):
        result = self.decomposer.decompose(task)
        if isinstance(result, dict): return result
        if not isinstance(result, tuple): return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_collection"))
        if not result or len(result) > self.max_steps: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_limit_exceeded"))
        seen = set()
        for item in result:
            if not isinstance(item, Subtask): return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_type"))
            if not isinstance(item.subtask_id, str) or not item.subtask_id.strip() or not item.subtask_id.startswith(task.task_id + ":"):
                return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_identity"))
            if item.subtask_id in seen: return self._reject("context", task, VerificationResult(False, "decomposition", "duplicate_subtask_identity"))
            seen.add(item.subtask_id)
            if item.task_type != task.task_type or not isinstance(item.objective, str) or not item.objective.strip():
                return self._reject("context", task, VerificationResult(False, "decomposition", "subtask_contract_mismatch"))
        return result

    def _verify_consensus(self, results):
        if not results: return VerificationResult(False, "consensus", "no_results")
        if any(not isinstance(result, AgentResult) or not result.is_well_formed() for result in results): return VerificationResult(False, "consensus", "malformed_agent_result")
        agent_ids = [result.agent_id for result in results]
        if len(agent_ids) != len(set(agent_ids)): return VerificationResult(False, "consensus", "duplicate_agent_result")
        if any(result.status != "completed" for result in results): return VerificationResult(False, "consensus", "incomplete_result")
        execution_ids = {result.execution_id for result in results}
        if "" in execution_ids: return VerificationResult(False, "consensus", "missing_execution_identity")
        if len(execution_ids) != 1: return VerificationResult(False, "consensus", "execution_identity_mismatch")
        task_ids = {result.task_id for result in results}
        if len(task_ids) != 1: return VerificationResult(False, "consensus", "task_identity_mismatch")
        for result in results:
            if not isinstance(result.verification, VerificationResult) or not result.verification.is_well_formed() or not result.verification.valid: return VerificationResult(False, "consensus", "unverified_result")
            if result.verification.stage != "agent_result": return VerificationResult(False, "consensus", "verification_stage_mismatch")
        outputs = {repr(result.output) for result in results}
        if len(outputs) != 1: return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_verified")

    def _persist_memory(self, task, output, reflection):
        if self.memory is not None: self.memory.put(task.task_id, {"execution_id": task.execution_id, "output": output, "confidence": reflection.confidence}, execution_id=task.execution_id)
