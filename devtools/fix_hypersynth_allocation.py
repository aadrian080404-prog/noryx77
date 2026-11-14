from pathlib import Path

p = Path("core/hypersynth.py")
text = p.read_text(encoding="utf-8")

start = text.find("        assignments = []")
end = text.find("        results = []", start)

if start < 0 or end < 0:
    raise RuntimeError("HYPERSYNTH allocation block not found")

replacement = """        assignments = []
        if preferred_agent is not None and preferred_agent not in agents:
            return self._reject(
                "allocation",
                task,
                VerificationResult(
                    False,
                    "allocation",
                    "preferred_agent_unavailable",
                ),
            )

        ordered_agents = list(agents)
        if preferred_agent is not None:
            ordered_agents.remove(preferred_agent)
            ordered_agents.insert(0, preferred_agent)

        for index, step in enumerate(plan.steps):
            agent_id = ordered_agents[index % len(ordered_agents)]
            child = TaskSpec(
                step.step_id,
                task.task_type,
                step.objective,
                task.input,
                task.constraints,
                task.verification_requirements,
                step.risk_class,
                task.execution_id,
            )
            try:
                selected, decision = self.supervisor.select(
                    child,
                    preferred=agent_id,
                )
            except Exception:
                return self._reject(
                    "allocation",
                    task,
                    VerificationResult(
                        False,
                        "allocation",
                        "agent_selection_failure",
                    ),
                )
            if not decision.accepted or selected is None:
                return self._reject(
                    "allocation",
                    task,
                    VerificationResult(
                        False,
                        "allocation",
                        decision.reason,
                    ),
                )
            assignments.append((selected, child, step))
"""

p.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
print("HYPERSYNTH ALLOCATION BLOCK REPAIRED")
