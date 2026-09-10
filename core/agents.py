from .contracts import AgentResult, TaskSpec
from .identity import AgentIdentity
from .verification import VerificationEngine
from hashlib import sha256


class Agent:
    agent_id = "base"

    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:
        raise NotImplementedError


class DeterministicAgent(Agent):
    agent_id = "deterministic"

    def __init__(self, verifier: VerificationEngine | None = None, identity: AgentIdentity | None = None):
        self.verifier = verifier or VerificationEngine()
        if identity is not None:
            if not isinstance(identity, AgentIdentity) or not identity.is_well_formed() or identity.agent_id != self.agent_id:
                raise ValueError("invalid_deterministic_agent_identity")
        self.identity = identity

    def _identity_fingerprint(self) -> str:
        identity = self.identity
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            return ""
        return sha256(identity.public_key).hexdigest()

    def run(self, task: TaskSpec, *, interaction_context=None) -> AgentResult:
        check = self.verifier.verify_task(task)
        fingerprint = self._identity_fingerprint()
        if not check.valid:
            return AgentResult(self.agent_id, task.task_id, "rejected", verification=check, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)
        result = AgentResult(self.agent_id, task.task_id, "completed", output=task.objective, execution_id=task.execution_id, agent_key_fingerprint=fingerprint)
        output_check = self.verifier.verify_output(result.output, stage="agent_result")
        return AgentResult(self.agent_id, task.task_id, result.status, result.output, output_check, task.execution_id, fingerprint)
