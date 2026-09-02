from dataclasses import dataclass
from typing import Any

from .audit import AuditLog
from .context import ContextManager
from .contracts import ActionSpec, AgentResult, TaskSpec, VerificationResult
from .decomposition import Subtask, TaskDecomposer
from .planning import Plan, PlanStep, Planner
from .reasoning import CrossChecker, Hypothesis, HypothesisEngine, InternalSimulator, SimulationResult
from .supervisor import AgentSupervisor
from .validation_requirements import VALID_VERIFICATION_REQUIREMENTS


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
        self.context_manager = context_manager or ContextManager(memory=memory)
        if memory is not None and context_manager is not None:
            self.context_manager.attach_memory(memory)
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

    def _independent_task_contract(self, task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec):
            return VerificationResult(False, "contract", "invalid_task_spec")
        if not task.is_well_formed():
            return VerificationResult(False, "contract", "malformed_task_spec")
        if task.risk_class not in {"normal", "sensitive", "high"}:
            return VerificationResult(False, "policy", "unsupported_risk_class")
        if any(requirement not in VALID_VERIFICATION_REQUIREMENTS for requirement in task.verification_requirements):
            return VerificationResult(False, "contract", "unsupported_verification_requirement")
        return VerificationResult(True, "contract", "independent_task_ok")

    def _independent_output_contract(self, output, requirements: tuple[str, ...], *, stage: str) -> VerificationResult:
        if not isinstance(requirements, tuple) or any(not isinstance(requirement, str) or requirement not in VALID_VERIFICATION_REQUIREMENTS for requirement in requirements):
            return VerificationResult(False, stage, "unsupported_verification_requirement")
        if output is None:
            return VerificationResult(False, stage, "null_output")
        if isinstance(output, (str, bytes)) and len(output) == 0:
            return VerificationResult(False, stage, "empty_output")
        if "string" in requirements and not isinstance(output, str):
            return VerificationResult(False, stage, "output_type_mismatch")
        return VerificationResult(True, stage, "independent_output_ok")

    def _independent_simulation_integrity(self, simulations: tuple[SimulationResult, ...], hypotheses: tuple[Hypothesis, ...], task: TaskSpec) -> VerificationResult:
        if not isinstance(simulations, tuple) or not simulations:
            return VerificationResult(False, "simulation", "no_simulations")
        expected_ids = tuple(h.hypothesis_id for h in hypotheses)
        actual_ids = tuple(getattr(item, "hypothesis_id", None) for item in simulations)
        if actual_ids != expected_ids:
            return VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch")
        for item, hypothesis in zip(simulations, hypotheses):
            if not isinstance(item, SimulationResult):
                return VerificationResult(False, "simulation", "invalid_simulation_type")
            if not isinstance(item.feasible, bool):
                return VerificationResult(False, "simulation", "invalid_feasibility_flag")
            if not isinstance(item.reason, str) or not item.reason.strip():
                return VerificationResult(False, "simulation", "invalid_simulation_reason")
            expected_feasible = bool(hypothesis.statement and hypothesis.task_id == task.task_id)
            if item.feasible != expected_feasible:
                return VerificationResult(False, "simulation", "simulation_feasibility_mismatch")
            expected_reason = "feasible" if expected_feasible else "invalid_hypothesis"
            if item.reason != expected_reason:
                return VerificationResult(False, "simulation", "simulation_reason_mismatch")
        return VerificationResult(True, "simulation", "independent_simulation_ok")

    def _checked_verification(self, check, *, stage: str, malformed_reason: str) -> VerificationResult:
        if not isinstance(check, VerificationResult) or not check.is_well_formed():
            return VerificationResult(False, stage, malformed_reason)
        return check

    def _advance_phase(self, current_index, target_phase, task):
        if target_phase not in self.PHASES:
            return VerificationResult(False, "phase", "unknown_phase")
        target_index = self.PHASES.index(target_phase)
        if target_index != current_index + 1:
            return VerificationResult(False, "phase", "phase_order_violation")
        self.audit.record("phase_entered", task_id=task.task_id, phase=target_phase, index=target_index)
        return VerificationResult(True, "phase", "phase_order_ok")

    def _verify_subtasks(self, task: TaskSpec, subtasks) -> VerificationResult:
        if not isinstance(subtasks, tuple) or not subtasks:
            return VerificationResult(False, "context", "invalid_subtask_collection")
        if len(subtasks) > self.max_agents:
            return VerificationResult(False, "context", "subtask_bounds_invalid")
        ids = set()
        prefix = task.task_id + ":"
        for subtask in subtasks:
            if not isinstance(subtask, Subtask): return VerificationResult(False, "context", "invalid_subtask_type")
            if not isinstance(subtask.subtask_id, str) or not subtask.subtask_id.strip() or subtask.subtask_id in ids: return VerificationResult(False, "context", "invalid_subtask_id")
            if not subtask.subtask_id.startswith(prefix): return VerificationResult(False, "context", "subtask_parent_mismatch")
            if not isinstance(subtask.objective, str) or not subtask.objective.strip(): return VerificationResult(False, "context", "invalid_subtask_objective")
            if not isinstance(subtask.task_type, str) or not subtask.task_type.strip() or subtask.task_type != task.task_type: return VerificationResult(False, "context", "subtask_task_type_mismatch")
            ids.add(subtask.subtask_id)
        return VerificationResult(True, "context", "subtasks_ok")

    def _verify_plan_integrity(self, plan: Plan, task: TaskSpec, context=None) -> VerificationResult:
        if not isinstance(plan, Plan) or plan.task_id != task.task_id:
            return VerificationResult(False, "planning", "plan_task_mismatch")
        if not isinstance(plan.steps, tuple) or not plan.steps or len(plan.steps) > min(self.max_steps, self.max_agents):
            return VerificationResult(False, "planning", "plan_bounds_invalid")
        if context is None:
            if plan.context_version is not None or plan.context_source_ids:
                return VerificationResult(False, "planning", "unexpected_context_binding")
        else:
            if plan.context_version != context.version or plan.context_source_ids != context.source_ids:
                return VerificationResult(False, "planning", "plan_context_mismatch")
        ids = set()
        prefix = task.task_id + ":"
        for step in plan.steps:
            if not isinstance(step, PlanStep): return VerificationResult(False, "planning", "plan_step_type_invalid")
            if not isinstance(step.step_id, str) or not step.step_id.strip() or step.step_id in ids or not step.step_id.startswith(prefix): return VerificationResult(False, "planning", "plan_step_id_invalid")
            if not isinstance(step.objective, str) or not step.objective.strip(): return VerificationResult(False, "planning", "plan_step_objective_invalid")
            if step.action_type not in Planner.VALID_ACTION_TYPES or step.risk_class not in Planner.VALID_RISKS: return VerificationResult(False, "planning", "plan_step_policy_invalid")
            if step.risk_class != task.risk_class: return VerificationResult(False, "planning", "plan_step_risk_mismatch")
            ids.add(step.step_id)
        return VerificationResult(True, "planning", "plan_integrity_ok")

    def _verify_hypothesis_integrity(self, hypotheses: tuple[Hypothesis, ...], plan: Plan, task: TaskSpec) -> VerificationResult:
        if not isinstance(hypotheses, tuple) or len(hypotheses) != len(plan.steps) or not hypotheses:
            return VerificationResult(False, "hypothesis", "hypothesis_plan_mismatch")
        ids = set()
        for hypothesis, step in zip(hypotheses, plan.steps):
            if not isinstance(hypothesis, Hypothesis): return VerificationResult(False, "hypothesis", "invalid_hypothesis_type")
            if not isinstance(hypothesis.hypothesis_id, str) or not hypothesis.hypothesis_id.strip() or hypothesis.hypothesis_id in ids: return VerificationResult(False, "hypothesis", "invalid_hypothesis_id")
            if hypothesis.task_id != task.task_id: return VerificationResult(False, "hypothesis", "hypothesis_task_mismatch")
            if not isinstance(hypothesis.statement, str) or not hypothesis.statement.strip(): return VerificationResult(False, "hypothesis", "invalid_hypothesis_statement")
            if hypothesis.statement != step.objective: return VerificationResult(False, "hypothesis", "hypothesis_statement_mismatch")
            if not isinstance(hypothesis.basis, tuple) or len(hypothesis.basis) != 1 or hypothesis.basis[0] != step.step_id: return VerificationResult(False, "hypothesis", "hypothesis_step_mismatch")
            ids.add(hypothesis.hypothesis_id)
        try:
            binding_check = self.hypothesis_engine.verify_against_plan(hypotheses, plan, task)
        except Exception:
            return VerificationResult(False, "hypothesis", "hypothesis_plan_binding_failure")
        return self._checked_verification(binding_check, stage="hypothesis", malformed_reason="malformed_hypothesis_plan_binding")

    def _verify_agent_result(self, child: TaskSpec, agent, result: AgentResult) -> VerificationResult:
        if not isinstance(result, AgentResult): return VerificationResult(False, "agent_result", "invalid_agent_result")
        if not result.is_well_formed(): return VerificationResult(False, "agent_result", "malformed_agent_result")
        if result.agent_id != getattr(agent, "agent_id", None): return VerificationResult(False, "agent_result", "agent_id_mismatch")
        if result.task_id != child.task_id: return VerificationResult(False, "agent_result", "task_id_mismatch")
        if result.status != "completed": return VerificationResult(False, "agent_result", "agent_not_completed")
        independent_output = self._independent_output_contract(result.output, child.verification_requirements, stage="runtime_output")
        if not independent_output.valid: return independent_output
        try: output_check = self.verifier.verify_output(result.output, requirements=child.verification_requirements, stage="runtime_output")
        except Exception: return VerificationResult(False, "agent_result", "verifier_output_failure")
        output_check = self._checked_verification(output_check, stage="runtime_output", malformed_reason="malformed_output_verification")
        if not output_check.valid: return output_check
        if result.verification is None or not result.verification.is_well_formed(): return VerificationResult(False, "agent_result", "malformed_result_verification")
        if not result.verification.valid: return VerificationResult(False, "agent_result", "result_verification_failed")
        if result.verification.stage not in ("result", "agent_result", result.agent_id): return VerificationResult(False, "agent_result", "verification_identity_mismatch")
        return VerificationResult(True, "agent_result", "independent_result_verified")

    def _evidence_confidence(self, evidence: list[str], required: int) -> float:
        if required <= 0: return 0.0
        return min(1.0, max(0.0, len(evidence) / required))

    def run(self, task: TaskSpec):
        self.audit.record("hypersynth_start", task_id=getattr(task, "task_id", None))
        evidence: list[str] = []
        phase_index = 0
        independent_task_check = self._independent_task_contract(task)
        if not independent_task_check.valid: return self._reject("perception", task, independent_task_check)
        try: task_check = self.verifier.verify_task(task)
        except Exception: return self._reject("perception", task, VerificationResult(False, "contract", "verifier_task_failure"))
        task_check = self._checked_verification(task_check, stage="contract", malformed_reason="malformed_task_verification")
        if not task_check.valid: return self._reject("perception", task, task_check)
        evidence.append("task_contract")
        self.audit.record("phase_verified", task_id=task.task_id, phase="perception")

        subtasks = self._decompose(task)
        if isinstance(subtasks, dict): return subtasks
        phase_check = self._advance_phase(phase_index, "context", task)
        if not phase_check.valid: return self._reject("context", task, phase_check)
        phase_index += 1
        subtask_check = self._verify_subtasks(task, subtasks)
        if not subtask_check.valid: return self._reject("context", task, subtask_check)
        try: context = self.context_manager.build(task.task_id, {"input": task.input, "objective": task.objective, "subtasks": tuple(s.subtask_id for s in subtasks)}, source_ids=(task.task_id,))
        except Exception: return self._reject("context", task, VerificationResult(False, "context", "context_build_failure"))
        if context.task_id != task.task_id or not context.source_ids or context.source_ids[0] != task.task_id:
            return self._reject("context", task, VerificationResult(False, "context", "context_identity_mismatch"))
        memory_items = context.values.get("memory", ())
        if not isinstance(memory_items, tuple) or tuple(getattr(item, "memory_id", None) for item in memory_items) != context.source_ids[1:]:
            return self._reject("context", task, VerificationResult(False, "context", "context_memory_provenance_mismatch"))
        evidence.append("context_integrity")
        if memory_items: evidence.append("memory_context_integrity")
        self.audit.record("context_acquired", task_id=task.task_id, version=context.version, memory_items=len(memory_items))

        phase_check = self._advance_phase(phase_index, "planning", task)
        if not phase_check.valid: return self._reject("planning", task, phase_check)
        phase_index += 1
        try:
            plan = self.planner.build(task, context)
            plan_check = self.planner.verify(plan, task, context)
        except Exception:
            plan_check, plan = VerificationResult(False, "planning", "planner_failure"), None
        plan_check = self._checked_verification(plan_check, stage="planning", malformed_reason="malformed_plan_verification")
        if not plan_check.valid: return self._reject("planning", task, plan_check)
        independent_plan_check = self._verify_plan_integrity(plan, task, context)
        if not independent_plan_check.valid: return self._reject("planning", task, independent_plan_check)
        evidence.append("plan_integrity")
        evidence.append("context_planning_binding")
        self.audit.record("plan_verified", task_id=task.task_id, steps=len(plan.steps), context_version=context.version)

        phase_check = self._advance_phase(phase_index, "hypothesis", task)
        if not phase_check.valid: return self._reject("hypothesis", task, phase_check)
        phase_index += 1
        try:
            hypotheses = self.hypothesis_engine.generate(task, plan)
            hypothesis_check = self.hypothesis_engine.verify(hypotheses, task)
        except Exception: return self._reject("hypothesis", task, VerificationResult(False, "hypothesis", "hypothesis_failure"))
        hypothesis_check = self._checked_verification(hypothesis_check, stage="hypothesis", malformed_reason="malformed_hypothesis_verification")
        if not hypothesis_check.valid: return self._reject("hypothesis", task, hypothesis_check)
        independent_hypothesis_check = self._verify_hypothesis_integrity(hypotheses, plan, task)
        if not independent_hypothesis_check.valid: return self._reject("hypothesis", task, independent_hypothesis_check)
        evidence.append("hypothesis_integrity")
        self.audit.record("hypotheses_verified", task_id=task.task_id, count=len(hypotheses))

        phase_check = self._advance_phase(phase_index, "simulation", task)
        if not phase_check.valid: return self._reject("simulation", task, phase_check)
        phase_index += 1
        try:
            simulations = self.simulator.simulate(task, hypotheses)
            simulation_check = self.simulator.verify(simulations)
        except Exception: return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_failure"))
        simulation_check = self._checked_verification(simulation_check, stage="simulation", malformed_reason="malformed_simulation_verification")
        if not simulation_check.valid: return self._reject("simulation", task, simulation_check)
        independent_simulation_check = self._independent_simulation_integrity(simulations, hypotheses, task)
        if not independent_simulation_check.valid: return self._reject("simulation", task, independent_simulation_check)
        expected_hypothesis_ids = tuple(h.hypothesis_id for h in hypotheses)
        actual_simulation_ids = tuple(s.hypothesis_id for s in simulations)
        if actual_simulation_ids != expected_hypothesis_ids: return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_id_mismatch"))
        if len(simulations) != len(hypotheses): return self._reject("simulation", task, VerificationResult(False, "simulation", "simulation_hypothesis_mismatch"))
        evidence.append("simulation_integrity")
        self.audit.record("simulation_verified", task_id=task.task_id, count=len(simulations))

        phase_check = self._advance_phase(phase_index, "allocation", task)
        if not phase_check.valid: return self._reject("allocation", task, phase_check)
        phase_index += 1
        assignments = []
        try: agents = self.router.available()
        except Exception: return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_discovery_failure"))
        if not isinstance(agents, tuple) or not agents: return self._reject("allocation", task, VerificationResult(False, "allocation", "no_agents_available"))
        if any(not isinstance(agent_id, str) or not agent_id.strip() for agent_id in agents): return self._reject("allocation", task, VerificationResult(False, "allocation", "invalid_agent_identity"))
        if len(set(agents)) != len(agents): return self._reject("allocation", task, VerificationResult(False, "allocation", "duplicate_agent_identity"))
        for index, step in enumerate(plan.steps):
            child = TaskSpec(step.step_id, task.task_type, step.objective, task.input, task.constraints, task.verification_requirements, step.risk_class)
            continuity_check = self.verifier.verify_task_continuity(task, child)
            continuity_check = self._checked_verification(continuity_check, stage="continuity", malformed_reason="malformed_continuity_verification")
            if not continuity_check.valid: return self._reject("allocation", task, continuity_check)
            selected = None
            selected_agent_id = None
            selection_failure = None
            for offset in range(len(agents)):
                agent_id = agents[(index + offset) % len(agents)]
                try:
                    candidate, decision = self.supervisor.select(child, preferred=agent_id)
                except Exception:
                    selection_failure = VerificationResult(False, "allocation", "agent_selection_failure")
                    continue
                if decision.accepted and candidate is not None:
                    if getattr(candidate, "agent_id", None) != agent_id:
                        return self._reject("allocation", task, VerificationResult(False, "allocation", "agent_selection_identity_mismatch"))
                    selected = candidate
                    selected_agent_id = agent_id
                    break
                selection_failure = VerificationResult(False, "allocation", decision.reason)
            if selected is None:
                return self._reject("allocation", task, selection_failure or VerificationResult(False, "allocation", "no_eligible_agent"))
            assignments.append((selected, child, step))
        if len(assignments) != len(plan.steps): return self._reject("allocation", task, VerificationResult(False, "allocation", "assignment_count_mismatch"))
        evidence.append("allocation_integrity")

        phase_check = self._advance_phase(phase_index, "execution", task)
        if not phase_check.valid: return self._reject("execution", task, phase_check)
        phase_index += 1
        results = []
        for index, (agent, child, step) in enumerate(assignments):
            action = ActionSpec("act:" + child.task_id, step.action_type, risk_class=step.risk_class)
            if self.action_gate is not None:
                decision = self.action_gate.authorize(action, calls_used=index)
                self.audit.record("action_gate", task_id=child.task_id, allowed=decision.allowed, reason=decision.reason)
                if not decision.allowed: return self._reject("execution", task, decision.verification, results=tuple(results))
            runtime_registration_check = self.supervisor.validate_selected(child, agent)
            if not runtime_registration_check.valid:
                return self._reject("execution", task, runtime_registration_check, results=tuple(results))
            self.audit.record("agent_runtime_revalidated", task_id=child.task_id, agent_id=getattr(agent, "agent_id", None), accepted=True)
            try: result = agent.run(child)
            except Exception: return self._reject("execution", task, VerificationResult(False, "execution", "agent_execution_failure"), results=tuple(results))
            results.append(result)
        if len(results) != len(assignments): return self._reject("execution", task, VerificationResult(False, "execution", "result_count_mismatch"), results=tuple(results))
        evidence.append("execution_integrity")

        phase_check = self._advance_phase(phase_index, "verification", task)
        if not phase_check.valid: return self._reject("verification", task, phase_check, results=tuple(results))
        phase_index += 1
        for index, (agent, child, _step) in enumerate(assignments):
            continuity_check = self.verifier.verify_task_continuity(task, child)
            continuity_check = self._checked_verification(continuity_check, stage="continuity", malformed_reason="malformed_continuity_verification")
            if not continuity_check.valid: return self._reject("verification", task, continuity_check, results=tuple(results))
            check = self._verify_agent_result(child, agent, results[index])
            if not check.valid: return self._reject("verification", task, check, results=tuple(results))
        cross_check = self.cross_checker.verify(task, tuple(results), hypotheses)
        cross_check = self._checked_verification(cross_check, stage="cross_check", malformed_reason="malformed_cross_check")
        if not cross_check.valid: return self._reject("verification", task, cross_check, results=tuple(results), hypotheses=hypotheses)
        if len({r.task_id for r in results}) == 1:
            consensus = self._verify_consensus(tuple(results))
            if not consensus.valid: return self._reject("verification", task, consensus, results=tuple(results))
        final_output = results[-1].output
        independent_output = self._independent_output_contract(final_output, task.verification_requirements, stage="hypersynth_result")
        if not independent_output.valid: return self._reject("verification", task, independent_output, results=tuple(results))
        try: output_check = self.verifier.verify_output(final_output, requirements=task.verification_requirements, stage="hypersynth_result")
        except Exception: return self._reject("verification", task, VerificationResult(False, "hypersynth_result", "verifier_output_failure"), results=tuple(results))
        output_check = self._checked_verification(output_check, stage="hypersynth_result", malformed_reason="malformed_output_verification")
        if not output_check.valid: return self._reject("verification", task, output_check, results=tuple(results))
        evidence.append("result_integrity")
        evidence.append("cross_check")
        self.audit.record("agent_results_independently_verified", task_id=task.task_id, count=len(results))

        phase_check = self._advance_phase(phase_index, "metacognition", task)
        if not phase_check.valid: return self._reject("metacognition", task, phase_check, results=tuple(results))
        confidence = self._evidence_confidence(evidence, 9)
        reflection = {"result_verified": True, "agents_used": tuple(r.agent_id for r in results), "steps_executed": len(results), "hypotheses_verified": len(hypotheses), "simulations_verified": len(simulations), "evidence_count": len(evidence), "evidence_required": 9, "confidence": confidence}
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
        try: subtasks = self.decomposer.decompose(task)
        except Exception: return self._reject("context", task, VerificationResult(False, "decomposition", "decomposition_failure"))
        if not subtasks: return self._reject("context", task, VerificationResult(False, "decomposition", "no_subtasks"))
        return subtasks

    def _verify_consensus(self, results: tuple[AgentResult, ...]) -> VerificationResult:
        if not results: return VerificationResult(False, "consensus", "no_results")
        if any(r.status != "completed" for r in results): return VerificationResult(False, "consensus", "incomplete_result")
        if len({r.agent_id for r in results}) != len(results): return VerificationResult(False, "consensus", "duplicate_agent_result")
        if any(r.verification is None or not r.verification.valid for r in results): return VerificationResult(False, "consensus", "unverified_result")
        outputs = {repr(r.output) for r in results}
        if len(outputs) > 1: return VerificationResult(False, "consensus", "agent_disagreement")
        return VerificationResult(True, "consensus", "consensus_ok")
