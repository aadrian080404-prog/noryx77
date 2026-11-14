from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "core" / "hypersynth.py"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")

    source = replace_once(
        source,
        "from .universal_intelligence import DomainAssessment, Evidence, UniversalIntelligenceFabric\n",
        "from .universal_intelligence import DomainAssessment, Evidence, UniversalIntelligenceFabric\nfrom .subtask_uif import SubtaskRouteSet, SubtaskUIFRouter\n",
        "import",
    )

    source = replace_once(
        source,
        "tool_executor=None, universal_intelligence=None):",
        "tool_executor=None, universal_intelligence=None, subtask_uif_router=None):",
        "constructor",
    )

    source = replace_once(
        source,
        "        self.universal_intelligence = universal_intelligence or UniversalIntelligenceFabric()\n        if not isinstance(self.universal_intelligence, UniversalIntelligenceFabric): raise TypeError(\"invalid_universal_intelligence_fabric\")\n",
        "        self.universal_intelligence = universal_intelligence or UniversalIntelligenceFabric()\n        if not isinstance(self.universal_intelligence, UniversalIntelligenceFabric): raise TypeError(\"invalid_universal_intelligence_fabric\")\n        self.subtask_uif_router = subtask_uif_router or SubtaskUIFRouter(self.universal_intelligence)\n        if not isinstance(self.subtask_uif_router, SubtaskUIFRouter): raise TypeError(\"invalid_subtask_uif_router\")\n",
        "router initialization",
    )

    source = replace_once(
        source,
        "        subtasks = self._decompose(routed_task)\n        if isinstance(subtasks, dict): return subtasks\n",
        "        subtasks = self._decompose(routed_task)\n        if isinstance(subtasks, dict): return subtasks\n        try: subtask_routes = self.subtask_uif_router.route(routed_task, subtasks)\n        except Exception: return self._reject(\"context\", routed_task, VerificationResult(False, \"subtask_routing\", \"subtask_route_failure\"))\n        if not isinstance(subtask_routes, SubtaskRouteSet) or not subtask_routes.verification.valid:\n            check = subtask_routes.verification if isinstance(subtask_routes, SubtaskRouteSet) else VerificationResult(False, \"subtask_routing\", \"invalid_subtask_routes\")\n            return self._reject(\"context\", routed_task, check)\n        self.audit.record(\"subtask_uif_routes\", task_id=routed_task.task_id, execution_id=routed_task.execution_id, routes=tuple((item.subtask_id, item.route.domain, item.route.strategy, item.route.budget) for item in subtask_routes.routes))\n",
        "route integration",
    )

    source = replace_once(
        source,
        "            child = TaskSpec(step.step_id, routed_task.task_type, step.objective, routed_task.input, routed_task.constraints, routed_task.verification_requirements, step.risk_class, routed_task.execution_id)\n",
        "            route = subtask_routes.route_for(step.step_id)\n            if route is None:\n                return self._reject(\"allocation\", routed_task, VerificationResult(False, \"subtask_routing\", \"subtask_route_missing\"))\n            try: child_constraints = self.subtask_uif_router.constraints_for(routed_task, route)\n            except Exception: return self._reject(\"allocation\", routed_task, VerificationResult(False, \"subtask_routing\", \"subtask_route_constraints_failure\"))\n            child = TaskSpec(step.step_id, routed_task.task_type, step.objective, routed_task.input, child_constraints, routed_task.verification_requirements, step.risk_class, routed_task.execution_id)\n",
        "child route binding",
    )

    source = replace_once(
        source,
        "        evidence = tuple(Evidence(f\"{r.agent_id}:{r.task_id}\", r.agent_id, str(r.output), 1.0 if r.verification and r.verification.valid else 0.0) for r in results)\n",
        "        subtask_aggregate = self.subtask_uif_router.aggregate_verification(routed_task, subtask_routes, tuple(results))\n        self.audit.record(\"subtask_uif_aggregate\", task_id=routed_task.task_id, execution_id=routed_task.execution_id, valid=subtask_aggregate.valid, reason=subtask_aggregate.reason)\n        if not subtask_aggregate.valid:\n            return self._reject(\"verification\", routed_task, subtask_aggregate, results=tuple(results), hypotheses=hypotheses, simulations=simulations, subtask_routes=subtask_routes)\n        evidence = tuple(Evidence(f\"{r.agent_id}:{r.task_id}\", r.agent_id, str(r.output), 1.0 if r.verification and r.verification.valid else 0.0) for r in results)\n",
        "aggregate gate",
    )

    TARGET.write_text(source, encoding="utf-8")
    subprocess.run(["git", "add", "core/hypersynth.py", "core/subtask_uif.py", "devtools/integrate_subtask_uif.py"], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", "integrate per-subtask UIF routing into HYPERSYNTH"], cwd=ROOT, check=True)
    subprocess.run(["git", "-c", "remote.origin.url=https://github.com/adrianatlas03-coder/noryx7-.git", "push", "origin", "HEAD:frontier-hardening-2026-09-07"], cwd=ROOT, check=True)
    print("SUBTASK UIF HYPERSYNTH INTEGRATION: PATCHED AND PUSHED")


if __name__ == "__main__":
    main()
