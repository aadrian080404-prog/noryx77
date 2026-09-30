from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.actions import AuthorizationAuthority
from core.identity import AgentIdentity
from core.tools import ToolExecutor
from core.verification import VerificationEngine
from noryx7_runtime.engine import RuntimeEngine


@dataclass(frozen=True)
class CanonicalSystemFabric:
    """Single shared execution substrate for JARVIS and NORYX7.

    The fabric is an ownership/identity boundary: every component that can
    execute work is explicitly bound to the same runtime, tool executor,
    verifier, authorization authority, principal, and policy.
    """

    runtime_engine: RuntimeEngine
    tool_executor: ToolExecutor
    verifier: VerificationEngine
    authorization: AuthorizationAuthority
    principal: AgentIdentity
    policy: Any

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_engine, RuntimeEngine):
            raise TypeError("runtime_engine_required")
        if not isinstance(self.tool_executor, ToolExecutor):
            raise TypeError("tool_executor_required")
        if not isinstance(self.verifier, VerificationEngine):
            raise TypeError("verifier_required")
        if not isinstance(self.authorization, AuthorizationAuthority):
            raise TypeError("authorization_required")
        if not isinstance(self.principal, AgentIdentity):
            raise TypeError("principal_required")
        if self.policy is None or not callable(getattr(self.policy, "authorize", None)):
            raise TypeError("policy_required")

    def assert_consistent(self, *, runtime_engine: RuntimeEngine,
                          tool_executor: ToolExecutor,
                          verifier: VerificationEngine,
                          authorization: AuthorizationAuthority,
                          principal: AgentIdentity,
                          policy: Any) -> None:
        if (
            self.runtime_engine is not runtime_engine
            or self.tool_executor is not tool_executor
            or self.verifier is not verifier
            or self.authorization is not authorization
            or self.principal is not principal
            or self.policy is not policy
        ):
            raise RuntimeError("canonical_fabric_identity_mismatch")
