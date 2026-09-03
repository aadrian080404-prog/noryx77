from .contracts import TaskSpec, VerificationResult


class VerificationEngine:
    """Fail-closed verification boundary for NORYX7 pipeline stages."""

    VALID_RISKS = {"normal", "sensitive", "high"}
    VALID_STATUSES = {"initialized", "processing", "completed"}
    VALID_VERDICTS = {"unknown", "success", "failure"}

    def verify_task(self, task: TaskSpec) -> VerificationResult:
        if not isinstance(task, TaskSpec):
            return VerificationResult(False, "contract", "invalid_task_spec")
        if not task.is_well_formed():
            return VerificationResult(False, "contract", "malformed_task_spec")
        if task.risk_class not in self.VALID_RISKS:
            return VerificationResult(False, "policy", "unsupported_risk_class")
        return VerificationResult(True, "contract", "task_ok")

    def verify_output(self, output, *, stage: str = "result") -> VerificationResult:
        if output is None:
            return VerificationResult(False, stage, "null_output")
        if isinstance(output, (str, bytes)) and len(output) == 0:
            return VerificationResult(False, stage, "empty_output")
        return VerificationResult(True, stage, "output_present")

    def verify_state(self, state) -> VerificationResult:
        status = getattr(state, "status", None)
        verdict = getattr(state, "verdict", None)
        if status not in self.VALID_STATUSES:
            return VerificationResult(False, "state", "invalid_status")
        if verdict not in self.VALID_VERDICTS:
            return VerificationResult(False, "state", "invalid_verdict")
        return VerificationResult(True, "state", "state_ok")

    def verify_pipeline(self, task: TaskSpec, output, state=None) -> tuple[VerificationResult, ...]:
        results = [self.verify_task(task), self.verify_output(output)]
        if state is not None:
            results.append(self.verify_state(state))
        return tuple(results)
