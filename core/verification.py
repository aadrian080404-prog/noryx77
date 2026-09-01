from .contracts import TaskSpec, VerificationResult

class VerificationEngine:
    """Fail-closed verification boundary for future NORYX7 components."""

    VALID_RISKS = {"normal", "sensitive", "high"}

    def verify_task(self, task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec):
            return VerificationResult(False, "contract", "invalid_task_spec")
        if not task.task_id or not task.task_type or not task.objective:
            return VerificationResult(False, "contract", "missing_required_task_fields")
        if task.risk_class not in self.VALID_RISKS:
            return VerificationResult(False, "policy", "unsupported_risk_class")
        return VerificationResult(True, "contract", "task_ok")

    def verify_output(self, output, *, stage: str = "result") -> VerificationResult:
        if output is None:
            return VerificationResult(False, stage, "null_output")
        return VerificationResult(True, stage, "output_present")

    def verify_state(self, state) -> VerificationResult:
        status = getattr(state, "status", None)
        verdict = getattr(state, "verdict", None)
        if status not in {"initialized", "processing", "completed"}:
            return VerificationResult(False, "state", "invalid_status")
        if verdict not in {"unknown", "success", "failure"}:
            return VerificationResult(False, "state", "invalid_verdict")
        return VerificationResult(True, "state", "state_ok")

    def verify_pipeline(self, task: TaskSpec, output, state=None) -> tuple[VerificationResult, ...]:
        results = [self.verify_task(task), self.verify_output(output)]
        if state is not None:
            results.append(self.verify_state(state))
        return tuple(results)
