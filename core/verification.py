from .contracts import AgentResult, TaskSpec, VerificationResult


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

    def verify_agent_results(self, results, *, expected_agent_id: str, expected_execution_id: str,
                             expected_task_ids: tuple[str, ...]) -> tuple[VerificationResult, ...]:
        """Verify the complete result set before any state commit."""
        if not isinstance(results, (list, tuple)) or not results:
            return (VerificationResult(False, "runtime_results", "empty_result_set"),)
        if not isinstance(expected_agent_id, str) or not expected_agent_id.strip():
            return (VerificationResult(False, "runtime_results", "invalid_expected_agent"),)
        if not isinstance(expected_execution_id, str) or not expected_execution_id.strip():
            return (VerificationResult(False, "runtime_results", "invalid_expected_execution"),)
        if not isinstance(expected_task_ids, tuple) or not expected_task_ids:
            return (VerificationResult(False, "runtime_results", "invalid_expected_task_ids"),)
        if len(results) != len(expected_task_ids):
            return (VerificationResult(False, "runtime_results", "result_count_mismatch"),)

        checks = []
        seen = set()
        for result, expected_task_id in zip(results, expected_task_ids):
            if not isinstance(result, AgentResult) or not result.is_well_formed():
                checks.append(VerificationResult(False, "runtime_results", "malformed_agent_result"))
                continue
            if result.agent_id != expected_agent_id:
                checks.append(VerificationResult(False, "runtime_results", "agent_identity_mismatch"))
                continue
            if result.task_id != expected_task_id or result.task_id in seen:
                checks.append(VerificationResult(False, "runtime_results", "task_identity_mismatch"))
                continue
            seen.add(result.task_id)
            if result.execution_id != expected_execution_id:
                checks.append(VerificationResult(False, "runtime_results", "execution_identity_mismatch"))
                continue
            if result.status != "completed":
                checks.append(VerificationResult(False, "runtime_results", "invalid_result_status"))
                continue
            verification = result.verification
            if (not isinstance(verification, VerificationResult)
                    or not verification.is_well_formed()
                    or not verification.valid
                    or verification.stage != "agent_result"):
                checks.append(VerificationResult(False, "runtime_results", "unverified_agent_result"))
                continue
            output_check = self.verify_output(result.output, stage="runtime_result")
            if not output_check.valid:
                checks.append(output_check)
                continue
            checks.append(VerificationResult(True, "runtime_results", "agent_result_ok"))

        if len(seen) != len(expected_task_ids):
            checks.append(VerificationResult(False, "runtime_results", "incomplete_result_set"))
        return tuple(checks)

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
