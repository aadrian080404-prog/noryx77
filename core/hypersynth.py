from dataclasses import dataclass
from typing import Any
from uuid import uuid4
import inspect

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
from .recovery import RecoveryController
from .subtask_uif import SubtaskUIFRouter
from .subtask_verification import verify_subtasks
from .universal_intelligence import DomainAssessment, Evidence, UniversalIntelligenceFabric


@dataclass(frozen=True)
class CognitiveState:
    phase: str
    task_id: str
    context: Any = None
    confidence: float = 0.0
    execution_id: str = ""


class Hypersynth:
    """Bounded cognitive kernel with one immutable execution identity per run."""
    PHASES = ("perception", "context", "planning", "hypothesis", "simulation", "allocation", "execution", "verification", "metacognition")

    def __init__(self, verifier, router, *, planner=None, decomposer=None, context_manager=None, action_gate=None, supervisor=None, memory=None, audit=None, max_steps=8, max_agents=2, hypothesis_engine=None, simulator=None, cross_checker=None, metacognition=None, recovery=None, tool_executor=None, universal_intelligence=None, subtask_uif_router=None):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1: raise ValueError("max_steps must be a positive integer")
        if isinstance(max_agents, bool) or not isinstance(max_agents, int) or max_agents < 1: raise ValueError("max_agents must be a positive integer")
        self.verifier, self.router, self.max_steps, self.max_agents = verifier, router, max_steps, max_agents
        bounded_steps = min(max_steps, max_agents)
        self.planner = planner or Planner(max_steps=bounded_steps)
        self.decomposer = decomposer or TaskDecomposer()
        self.context_manager = context_manager or ContextManager(memory=memory)
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
        self.recovery = recovery
        self.tool_executor = tool_executor
        self.universal_intelligence = universal_intelligence or UniversalIntelligenceFabric()
        if not isinstance(self.universal_intelligence, UniversalIntelligenceFabric): raise TypeError("invalid_universal_intelligence_fabric")
        self.subtask_uif_router = subtask_uif_router or SubtaskUIFRouter(self.universal_intelligence)
        if not isinstance(self.subtask_uif_router, SubtaskUIFRouter): raise TypeError("invalid_subtask_uif_router")
        if self.recovery is not None and not isinstance(self.recovery, RecoveryController): raise TypeError("invalid_recovery_controller")

    def _state(self, phase, task, context, confidence=0.0): return CognitiveState(phase, task.task_id, context=context, confidence=confidence, execution_id=task.execution_id)
    def _reject(self, phase, task, check, **extra):
        self.audit.record("hypersynth_rejected", task_id=getattr(task, "task_id", None), phase=phase, reason=check.reason, execution_id=getattr(task, "execution_id", ""))
        result = {
            "status": "rejected",
            "phase": phase,
            "verification": check,
            "execution_id": getattr(task, "execution_id", ""),
        }; result.update(extra); return result
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

    def run(self, task: TaskSpec, *, deadline_check=None, preferred_agent=None, interaction_context=None):
        task = self._bind_execution(task)
        recovery_epoch = self.recovery.epoch if self.recovery is not None else None
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None), execution_id=getattr(task, "execution_id", ""))
        try: task_check = self.verifier.verify_task(task)
        except Exception: return self._reject("perception", task, VerificationResult(False, "contract", "task_verification_failure"))
        if not self._accepts_verification(task_check, "contract"):
            check = task_check if isinstance(task_check, VerificationResult) and task_check.is_well_formed() else VerificationResult(False, "contract", "invalid_task_verification")
            return self._reject("perception", task, check)
        timeout = self._deadline_rejection(task, "perception", deadline_check)
        if timeout: return timeout
        if self.recovery is not None:
            try: self.recovery.require_normal(expected_epoch=recovery_epoch)
            except PermissionError as exc: return self._reject("perception", task, VerificationResult(False, "recovery", str(exc)))
        try:
            specialist_route = self.universal_intelligence.route(task)
        except Exception:
            return self._reject("perception", task, VerificationResult(False, "universal_intelligence", "specialist_route_failure"))
        self.audit.record("universal_intelligence_route", task_id=task.task_id, execution_id=task.execution_id, domain=specialist_route.domain, strategy=specialist_route.strategy, budget=specialist_route.budget, rationale=specialist_route.rationale)
        routed_constraints = dict(task.constraints)
        routed_constraints.update({
            "_noryx7_specialist_domain": specialist_route.domain,
            "_noryx7_cognitive_strategy": specialist_route.strategy,
            "_noryx7_cognitive_budget": specialist_route.budget,
        })
        routed_task = TaskSpec(task.task_id, task.task_type, task.objective, task.input, routed_constraints, task.verification_requirements, task.risk_class, task.execution_id)
        subtasks = self._decompose(routed_task)
        if isinstance(subtasks, dict): return subtasks
        try:
            subtask_routes = self.subtask_uif_router.route(routed_task, subtasks)
        except Exception:
            return self._reject("context", routed_task, VerificationResult(False, "subtask_routing", "subtask_route_failure"))
        if not subtask_routes.verification.is_well_formed() or not subtask_routes.verification.valid:
            return self._reject("context", routed_task, subtask_routes.verification, subtask_routes=subtask_routes)
        route_by_id = {item.subtask_id: item for item in subtask_routes.routes}
        if tuple(route_by_id) != tuple(s.subtask_id for s in subtasks):
            return self._reject("context", routed_task, VerificationResult(False, "subtask_routing", "subtask_route_coverage_invalid"), subtask_routes=subtask_routes)
        self.audit.record("subtask_uif_routes", task_id=routed_task.task_id, execution_id=routed_task.execution_id, routes=tuple({"subtask_id": item.subtask_id, "domain": item.route.domain, "strategy": item.route.strategy, "budget": item.route.budget, "route_authority": item.route_authority} for item in subtask_routes.routes))
        timeout = self._deadline_rejection(routed_task, "context", deadline_check)
        if timeout: return timeout
        context = self.context_manager.build(
            routed_task.task_id,
            {"input": routed_task.input, "objective": routed_task.objective, "subtasks": tuple(s.subtask_id for s in subtasks), "specialist_route": specialist_route, "subtask_routes": subtask_routes},
            source_ids=(routed_task.task_id,),
            execution_id=routed_task.execution_id,
        )
        timeout = self._deadline_rejection(routed_task, "planning", deadline_check)
        if timeout: return timeout
        try: plan = self.planner.build(routed_task); plan_check = self.planner.verify(plan, routed_task)
        except Exception: plan_check, plan = VerificationResult(False, "planning", "planner_failure"), None
        if not self._accepts_verification(plan_check, "plan"): return self._reject("planning", routed_task, plan_check if isinstance(plan_check, VerificationResult) and plan_check.is_well_formed() else VerificationResult(False, "plan", "invalid_plan_verification"))
        if not plan.steps or len(plan.steps) > self.max_agents: return self._reject("planning", routed_task, VerificationResult(False, "planning", "plan_exceeds_execution_bound"))

        # Legacy/custom planners may materialize more execution steps than the
        # decomposer emitted when the task has no explicit structured subtasks.
        # Preserve the canonical decomposition contract for explicit subtasks,
        # while deriving bounded subtask identities from the verified plan for
        # legacy planners. Every executable plan step must still receive its own
        # UIF route before allocation.
        planned_subtask_ids = tuple(step.step_id for step in plan.steps)
        decomposed_subtask_ids = tuple(item.subtask_id for item in subtasks)
        if planned_subtask_ids != decomposed_subtask_ids:
            if routed_task.constraints.get("subtasks") is not None:
                return self._reject(
                    "planning",
                    routed_task,
                    VerificationResult(False, "planning", "subtask_plan_coverage_invalid"),
                    subtask_routes=subtask_routes,
                )
            try:
                planned_subtasks = tuple(
                    Subtask(step.step_id, step.objective, routed_task.task_type, step.dependencies)
                    for step in plan.steps
                )
                subtask_routes = self.subtask_uif_router.route(routed_task, planned_subtasks)
            except Exception:
                return self._reject(
                    "planning",
                    routed_task,
                    VerificationResult(False, "subtask_routing", "subtask_plan_route_failure"),
                )
            if not subtask_routes.verification.is_well_formed() or not subtask_routes.verification.valid:
                return self._reject("planning", routed_task, subtask_routes.verification, subtask_routes=subtask_routes)
            subtasks = planned_subtasks
            route_by_id = {item.subtask_id: item for item in subtask_routes.routes}
            self.audit.record(
                "subtask_uif_legacy_planner_reconciled",
                task_id=routed_task.task_id,
                execution_id=routed_task.execution_id,
                planned_subtasks=planned_subtask_ids,
            )
            context = self.context_manager.build(
                routed_task.task_id,
                {
                    "input": routed_task.input,
                    "objective": routed_task.objective,
                    "subtasks": planned_subtask_ids,
                    "specialist_route": specialist_route,
                    "subtask_routes": subtask_routes,
                },
                source_ids=(routed_task.task_id,),
                execution_id=routed_task.execution_id,
            )
        timeout = self._deadline_rejection(routed_task, "hypothesis", deadline_check)
        if timeout: return timeout
        try: hypotheses = self.hypothesis_engine.generate(routed_task, plan); hypothesis_check = self.hypothesis_engine.verify(hypotheses, routed_task)
        except Exception: return self._reject("hypothesis", routed_task, VerificationResult(False, "hypothesis", "hypothesis_failure"))
        if not self._accepts_verification(hypothesis_check, "hypothesis"): return self._reject("hypothesis", routed_task, hypothesis_check if isinstance(hypothesis_check, VerificationResult) and hypothesis_check.is_well_formed() else VerificationResult(False, "hypothesis", "invalid_hypothesis_verification"))
        if len(hypotheses) != len(plan.steps): return self._reject("hypothesis", routed_task, VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch"))
        timeout = self._deadline_rejection(routed_task, "simulation", deadline_check)
        if timeout: return timeout
        try: simulations = self.simulator.simulate(routed_task, hypotheses); simulation_check = self.simulator.verify(simulations)
        except Exception: return self._reject("simulation", routed_task, VerificationResult(False, "simulation", "simulation_failure"))
        if not self._accepts_verification(simulation_check, "simulation"): return self._reject("simulation", routed_task, simulation_check if isinstance(simulation_check, VerificationResult) and simulation_check.is_well_formed() else VerificationResult(False, "simulation", "invalid_simulation_verification"))
        if tuple(s.hypothesis_id for s in simulations) != tuple(h.hypothesis_id for h in hypotheses): return self._reject("simulation", routed_task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))
        if len(simulations) != len(hypotheses): return self._reject("simulation", routed_task, VerificationResult(False, "simulation", "simulation_hypothesis_mismatch"))
        timeout = self._deadline_rejection(routed_task, "allocation", deadline_check)
        if timeout: return timeout
        agents = self.router.available()
        if not agents: return self._reject("allocation", routed_task, VerificationResult(False, "allocation", "no_agents_available"))
        assignments = []
        if preferred_agent is not None and preferred_agent not in agents:
            return self._reject("allocation", routed_task, VerificationResult(False, "allocation", "preferred_agent_unavailable"))
        ordered_agents = list(agents)
        if preferred_agent is not None:
            ordered_agents.remove(preferred_agent)
            ordered_agents.insert(0, preferred_agent)
        for index, step in enumerate(plan.steps):
            agent_id = ordered_agents[index % len(ordered_agents)]
            route = route_by_id.get(step.step_id)
            if route is None:
                return self._reject("allocation", routed_task, VerificationResult(False, "subtask_routing", "subtask_route_missing"), subtask_routes=subtask_routes)
            try:
                child_constraints = self.subtask_uif_router.constraints_for(routed_task, route)
            except Exception:
                return self._reject("allocation", routed_task, VerificationResult(False, "subtask_routing", "subtask_route_constraints_failure"), subtask_routes=subtask_routes)
            child = TaskSpec(step.step_id, routed_task.task_type, step.objective, routed_task.input, child_constraints, routed_task.verification_requirements, step.risk_class, routed_task.execution_id)
            try:
                selected, decision = self.supervisor.select(child, preferred=agent_id)
            except Exception:
                return self._reject("allocation", routed_task, VerificationResult(False, "allocation", "agent_selection_failure"))
            if not decision.accepted or selected is None:
                return self._reject("allocation", routed_task, VerificationResult(False, "allocation", decision.reason))
            assignments.append((selected, child, step))
        results = []
        for index, (agent, child, step) in enumerate(assignments):
            timeout = self._deadline_rejection(routed_task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            action = ActionSpec("act:" + child.task_id, step.action_type, target=step.objective, parameters={"input": routed_task.input, "constraints": dict(child.constraints), "task_id": child.task_id, "task_type": child.task_type, "verification_requirements": tuple(child.verification_requirements), "risk_class": child.risk_class, "execution_id": routed_task.execution_id}, risk_class=step.risk_class, execution_id=routed_task.execution_id)
            try:
                capability = self.tool_executor is not None and self.tool_executor.capabilities.resolve(step.action_type) is not None
                if capability:
                    operation = lambda: self.tool_executor.execute(action, calls_used=index, execution_id=routed_task.execution_id, principal=getattr(agent, "identity", None))
                    if self.recovery is not None:
                        def guarded(): return operation()
                        capability_result = self.recovery.run_if_normal(guarded, expected_epoch=recovery_epoch)
                    else: capability_result = operation()
                    capability_output, capability_check = capability_result
                    if not capability_check.valid: return self._reject("execution", routed_task, capability_check, results=tuple(results))
                    result = AgentResult(agent.agent_id, child.task_id, "completed", capability_output, VerificationResult(True, "agent_result", "capability_result_verified"), routed_task.execution_id)
                else:
                    run_parameters = inspect.signature(agent.run).parameters
                    accepts_context = "interaction_context" in run_parameters or any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in run_parameters.values())
                    if interaction_context is not None and accepts_context:
                        operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child, interaction_context=interaction_context), calls_used=index, execution_id=routed_task.execution_id)
                    else:
                        operation = lambda: self.action_gate.authorize_and_execute(action, lambda: agent.run(child), calls_used=index, execution_id=routed_task.execution_id)
                    if self.recovery is not None: decision, result = self.recovery.run_if_normal(operation, expected_epoch=recovery_epoch)
                    else: decision, result = operation()
                    if not decision.allowed:
                        check = decision.verification
                        if check.reason == "execution_failure": check = VerificationResult(False, "execution", "execution_failure")
                        return self._reject("execution", routed_task, check, results=tuple(results))
            except Exception:
                return self._reject("execution", routed_task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))
            timeout = self._deadline_rejection(routed_task, "execution", deadline_check)
            if timeout: return dict(timeout, results=tuple(results))
            admission = self.supervisor.admit(child, result, selected_agent_id=agent.agent_id)
            if not admission.valid: return self._reject("verification", routed_task, admission, results=tuple(results))
            if not isinstance(result, AgentResult): return self._reject("verification", routed_task, VerificationResult(False, "agent_result", "malformed_agent_result"), results=tuple(results))
            if result.execution_id != routed_task.execution_id: return self._reject("verification", routed_task, VerificationResult(False, "agent_result", "execution_identity_mismatch"), results=tuple(results))
            results.append(result)
        timeout = self._deadline_rejection(routed_task, "verification", deadline_check)
        if timeout: return dict(timeout, results=tuple(results))
        if self.recovery is not None:
            try: self.recovery.require_normal(expected_epoch=recovery_epoch)
            except PermissionError as exc: return self._reject("verification", routed_task, VerificationResult(False, "recovery", str(exc)), results=tuple(results))
        cross_check = self.cross_checker.verify(routed_task, tuple(results), hypotheses)
        if not cross_check.valid: return self._reject("verification", routed_task, cross_check, results=tuple(results), hypotheses=hypotheses)
        if len({r.task_id for r in results}) == 1:
            consensus = self._verify_consensus(tuple(results))
            if not consensus.valid: return self._reject("verification", routed_task, consensus, results=tuple(results))
        subtask_gate = verify_subtasks(subtask_routes, tuple(results))
        self.audit.record("subtask_uif_aggregate", task_id=routed_task.task_id, execution_id=routed_task.execution_id, evidence=tuple({"subtask_id": item.subtask_id, "agent_id": item.agent_id, "verified": item.verified} for item in subtask_gate.evidence), commit_eligible=subtask_gate.commit_eligible, verification_reason=subtask_gate.verification.reason)
        if not subtask_gate.commit_eligible:
            return self._reject("verification", routed_task, subtask_gate.verification, results=tuple(results), hypotheses=hypotheses, simulations=simulations, subtask_routes=subtask_routes, subtask_verification=subtask_gate)
        evidence = tuple(Evidence(f"{item.agent_id}:{item.subtask_id}", item.agent_id, item.output, 1.0 if item.verified else 0.0) for item in subtask_gate.evidence)
        uif_assessment = DomainAssessment(specialist_route.domain, str(results[-1].output), evidence=evidence, confidence=1.0, uncertainty=0.0, contradictions=(), risk_level="normal", strategy=specialist_route.strategy)
        fabric_result = self.universal_intelligence.assess(routed_task, (uif_assessment,), budget=specialist_route.budget)
        self.audit.record("universal_intelligence_assessed", task_id=routed_task.task_id, execution_id=routed_task.execution_id, domain=specialist_route.domain, evidence_coverage=fabric_result.evidence_coverage, commit_eligible=fabric_result.commit_eligible, verification_reason=fabric_result.verification.reason)
        if not fabric_result.commit_eligible:
            return self._reject("verification", routed_task, VerificationResult(False, "universal_intelligence", "fabric_commit_denied"), results=tuple(results), hypotheses=hypotheses, simulations=simulations, universal_intelligence=fabric_result, subtask_routes=subtask_routes, subtask_verification=subtask_gate)
        timeout = self._deadline_rejection(routed_task, "metacognition", deadline_check)
        if timeout: return dict(timeout, results=tuple(results))
        final_output = results[-1].output
        try: output_check = self.verifier.verify_output(final_output, stage="hypersynth_result")
        except Exception: return self._reject("verification", routed_task, VerificationResult(False, "hypersynth_result", "output_verification_failure"), results=tuple(results))
        if not self._accepts_verification(output_check, "hypersynth_result"): return self._reject("verification", routed_task, output_check if isinstance(output_check, VerificationResult) and output_check.is_well_formed() else VerificationResult(False, "hypersynth_result", "invalid_output_verification"), results=tuple(results))
        metacognitive_check, reflection = self.metacognition.reflect(routed_task, plan, hypotheses, simulations, tuple(results), output_check)
        if not isinstance(metacognitive_check, VerificationResult) or not metacognitive_check.is_well_formed() or not metacognitive_check.valid: return self._reject("metacognition", routed_task, metacognitive_check if isinstance(metacognitive_check, VerificationResult) else VerificationResult(False, "metacognition", "invalid_metacognition_result"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if metacognitive_check.stage != "metacognition": return self._reject("metacognition", routed_task, VerificationResult(False, "metacognition", "metacognition_stage_mismatch"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if self.memory is not None:
            try:
                from .memory import MemoryItem
                memory_key = "task:" + routed_task.execution_id + ":" + routed_task.task_id
                self.memory.put(MemoryItem(memory_key, final_output, kind="working", source=routed_task.task_id, importance=0.5, execution_id=routed_task.execution_id))
                execution_key = "execution:" + routed_task.execution_id + ":final"
                self.memory.put(MemoryItem(execution_key, final_output, kind="working", source=routed_task.task_id, importance=0.7, execution_id=routed_task.execution_id))
            except Exception:
                return self._reject("verification", routed_task, VerificationResult(False, "memory", "memory_persistence_failure"), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        if self.recovery is not None:
            try: self.recovery.require_normal(expected_epoch=recovery_epoch)
            except PermissionError as exc: return self._reject("metacognition", routed_task, VerificationResult(False, "recovery", str(exc)), results=tuple(results), hypotheses=hypotheses, simulations=simulations)
        final_state = self._state("metacognition", routed_task, context, confidence=reflection.confidence)
        return {"status": "completed", "phase": final_state.phase, "state": final_state, "context": context, "plan": plan, "hypotheses": hypotheses, "simulations": simulations, "results": tuple(results), "verification": output_check, "reflection": reflection, "execution_id": routed_task.execution_id, "universal_intelligence": fabric_result, "specialist_route": specialist_route, "subtask_routes": subtask_routes, "subtask_verification": subtask_gate, "audit": self.audit.snapshot()}

    def _decompose(self, task):
        try: subtasks = self.decomposer.decompose(task)
        except Exception: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if not isinstance(subtasks, tuple) or not subtasks: return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_collection"))
        seen = set()
        for subtask in subtasks:
            if not isinstance(subtask, Subtask): return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_type"))
            if not isinstance(subtask.subtask_id, str) or not subtask.subtask_id.strip() or subtask.subtask_id in seen: return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_identity"))
            if not subtask.subtask_id.startswith(task.task_id + ":"): return self._reject("context", task, VerificationResult(False, "decomposition", "subtask_task_identity_mismatch"))
            if not isinstance(subtask.objective, str) or not subtask.objective.strip(): return self._reject("context", task, VerificationResult(False, "decomposition", "invalid_subtask_objective"))
            if not isinstance(subtask.task_type, str) or not subtask.task_type.strip() or subtask.task_type != task.task_type: return self._reject("context", task, VerificationResult(False, "decomposition", "subtask_task_type_mismatch"))
            seen.add(subtask.subtask_id)
        return subtasks

    def _verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not isinstance(results, tuple) or not results: return VerificationResult(False, "consensus", "no_results")
        if any(not isinstance(r, AgentResult) or not r.is_well_formed() for r in results): return VerificationResult(False, "consensus", "malformed_result")
        if any(r.status != "completed" for r in results): return VerificationResult(False, "consensus", "incomplete_result")
        if len({r.agent_id for r in results}) != len(results): return VerificationResult(False, "consensus", "duplicate_agent_result")
        if len({r.task_id for r in results}) != 1: return VerificationResult(False, "consensus", "task_identity_mismatch")
        if any(r.execution_id != results[0].execution_id for r in results): return VerificationResult(False, "consensus", "execution_identity_mismatch")
        if not results[0].execution_id: return VerificationResult(False, "consensus", "missing_execution_identity")
        if any(r.verification is None or not r.verification.is_well_formed() or not r.verification.valid for r in results): return VerificationResult(False, "consensus", "unverified_result")
        if any(r.verification.stage != "agent_result" for r in results): return VerificationResult(False, "consensus", "verification_stage_mismatch")
        outputs = [r.output for r in results]
        if any(output != outputs[0] for output in outputs[1:]): return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
