"""Canonical operating contract for NORYX7 agents.

The agent core is deliberately model-agnostic: cognition providers, speech
adapters, browser adapters and tools plug into this contract without becoming
security authorities.  The core owns lifecycle, bounded interaction state,
verification gates and fail-closed action dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol, Sequence

from .identity import AgentIdentity

MAX_AGENT_ID = 256
MAX_TEXT = 32_768
MAX_TURNS = 256
MAX_PLAN_STEPS = 128
MAX_METADATA = 64


class AgentPhase(str, Enum):
    READY = "ready"
    PERCEIVING = "perceiving"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    AUTHORIZING = "authorizing"
    ACTING = "acting"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    RESPONDING = "responding"
    PAUSED = "paused"
    FAILED = "failed"


class InputModality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    EVENT = "event"
    TOOL = "tool"
    BROWSER = "browser"


class OutputModality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    ACTION = "action"
    TOOL = "tool"
    BROWSER = "browser"
    CLARIFICATION = "clarification"


@dataclass(frozen=True)
class AgentInput:
    modality: InputModality
    payload: Any
    session_id: str
    principal_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.modality, InputModality):
            raise TypeError("invalid_input_modality")
        for value, error in ((self.session_id, "invalid_session_id"), (self.principal_id, "invalid_principal_id")):
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_AGENT_ID:
                raise ValueError(error)
        if not isinstance(self.metadata, Mapping) or len(self.metadata) > MAX_METADATA:
            raise ValueError("invalid_input_metadata")
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.metadata.items()):
            raise ValueError("invalid_input_metadata")


@dataclass(frozen=True)
class AgentPlan:
    objective: str
    steps: tuple[str, ...]
    risk: str = "normal"

    def __post_init__(self) -> None:
        if not isinstance(self.objective, str) or not self.objective.strip() or len(self.objective) > MAX_TEXT:
            raise ValueError("invalid_plan_objective")
        if not isinstance(self.steps, tuple) or not 1 <= len(self.steps) <= MAX_PLAN_STEPS:
            raise ValueError("invalid_plan_steps")
        if any(not isinstance(step, str) or not step.strip() or len(step) > MAX_TEXT for step in self.steps):
            raise ValueError("invalid_plan_step")
        if not isinstance(self.risk, str) or not self.risk.strip():
            raise ValueError("invalid_plan_risk")


@dataclass(frozen=True)
class AgentResponse:
    agent_id: str
    session_id: str
    principal_id: str
    text: str
    modality: OutputModality = OutputModality.TEXT
    verified: bool = False
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or len(self.text) > MAX_TEXT:
            raise ValueError("invalid_agent_response")
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("invalid_agent_id")
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise ValueError("invalid_session_id")
        if not isinstance(self.principal_id, str) or not self.principal_id.strip():
            raise ValueError("invalid_principal_id")
        if not isinstance(self.modality, OutputModality):
            raise TypeError("invalid_output_modality")
        if not isinstance(self.verified, bool):
            raise TypeError("verified must be bool")


class CognitionProvider(Protocol):
    def understand(self, agent_input: AgentInput) -> Mapping[str, Any]: ...
    def plan(self, understanding: Mapping[str, Any]) -> AgentPlan: ...
    def respond(self, understanding: Mapping[str, Any], result: Any) -> str: ...


class ActionAuthorizer(Protocol):
    def authorize(self, agent_id: str, principal_id: str, action: str) -> bool: ...


class ActionExecutor(Protocol):
    def execute(self, agent_id: str, principal_id: str, action: str) -> Any: ...


class ResultVerifier(Protocol):
    def verify(self, value: Any, *, stage: str) -> bool: ...


class SpeechAdapter(Protocol):
    def transcribe(self, audio: Any) -> str: ...
    def synthesize(self, text: str) -> Any: ...


class AgentMemory(Protocol):
    def recall(self, principal_id: str, session_id: str, query: str) -> Sequence[Any]: ...
    def remember(self, principal_id: str, session_id: str, value: Any) -> None: ...


class AgentCore:
    """Fast, bounded lifecycle engine for a single trusted agent.

    Expensive cognition is injected.  Security decisions and action execution
    remain outside the cognition provider and must pass explicit authorization
    and verification boundaries.
    """

    _TRANSITIONS = {
        AgentPhase.READY: {AgentPhase.PERCEIVING, AgentPhase.PAUSED, AgentPhase.FAILED},
        AgentPhase.PERCEIVING: {AgentPhase.UNDERSTANDING, AgentPhase.FAILED},
        AgentPhase.UNDERSTANDING: {AgentPhase.PLANNING, AgentPhase.RESPONDING, AgentPhase.FAILED},
        AgentPhase.PLANNING: {AgentPhase.AUTHORIZING, AgentPhase.RESPONDING, AgentPhase.FAILED},
        AgentPhase.AUTHORIZING: {AgentPhase.ACTING, AgentPhase.FAILED},
        AgentPhase.ACTING: {AgentPhase.VERIFYING, AgentPhase.FAILED},
        AgentPhase.VERIFYING: {AgentPhase.REFLECTING, AgentPhase.FAILED},
        AgentPhase.REFLECTING: {AgentPhase.RESPONDING, AgentPhase.FAILED},
        AgentPhase.RESPONDING: {AgentPhase.READY, AgentPhase.FAILED},
        AgentPhase.PAUSED: {AgentPhase.READY},
        AgentPhase.FAILED: {AgentPhase.READY, AgentPhase.PAUSED},
    }

    def __init__(self, *, identity: AgentIdentity, cognition: CognitionProvider,
                 authorizer: ActionAuthorizer | None = None, executor: ActionExecutor | None = None,
                 verifier: ResultVerifier | None = None, speech: SpeechAdapter | None = None,
                 memory: AgentMemory | None = None, max_turns: int = MAX_TURNS) -> None:
        if not isinstance(identity, AgentIdentity) or not identity.is_well_formed():
            raise ValueError("trusted_agent_identity_required")
        if not callable(getattr(cognition, "understand", None)) or not callable(getattr(cognition, "plan", None)) or not callable(getattr(cognition, "respond", None)):
            raise TypeError("cognition_provider_required")
        if (authorizer is None) != (executor is None):
            raise ValueError("authorizer_and_executor_must_be_configured_together")
        if verifier is not None and not callable(getattr(verifier, "verify", None)):
            raise TypeError("verifier_must_expose_verify")
        if speech is not None and (not callable(getattr(speech, "transcribe", None)) or not callable(getattr(speech, "synthesize", None))):
            raise TypeError("speech_adapter_required")
        if memory is not None and (not callable(getattr(memory, "recall", None)) or not callable(getattr(memory, "remember", None))):
            raise TypeError("memory_adapter_required")
        if isinstance(max_turns, bool) or not isinstance(max_turns, int) or not 1 <= max_turns <= MAX_TURNS:
            raise ValueError("invalid_max_turns")
        self.identity = identity
        self.cognition = cognition
        self.authorizer = authorizer
        self.executor = executor
        self.verifier = verifier
        self.speech = speech
        self.memory = memory
        self._max_turns = max_turns
        self._turns = 0
        self._phase = AgentPhase.READY
        self._lock = RLock()

    @property
    def agent_id(self) -> str:
        return self.identity.agent_id

    @property
    def phase(self) -> AgentPhase:
        with self._lock:
            return self._phase

    @property
    def turns(self) -> int:
        with self._lock:
            return self._turns

    def _transition(self, target: AgentPhase) -> None:
        if target not in self._TRANSITIONS[self._phase]:
            raise RuntimeError(f"invalid_agent_transition:{self._phase.value}->{target.value}")
        self._phase = target

    def pause(self) -> None:
        with self._lock:
            if self._phase not in (AgentPhase.READY, AgentPhase.FAILED):
                raise RuntimeError("agent_busy")
            self._phase = AgentPhase.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._phase is not AgentPhase.PAUSED:
                raise RuntimeError("agent_not_paused")
            self._phase = AgentPhase.READY

    def _normalize_input(self, value: AgentInput) -> AgentInput:
        if value.modality is not InputModality.VOICE:
            return value
        if self.speech is None:
            raise PermissionError("voice_input_unavailable")
        text = self.speech.transcribe(value.payload)
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise ValueError("invalid_transcription")
        return AgentInput(InputModality.TEXT, text, value.session_id, value.principal_id, value.metadata)

    def process(self, value: AgentInput) -> AgentResponse:
        with self._lock:
            if self._phase is AgentPhase.PAUSED:
                raise PermissionError("agent_paused")
            if self._phase is not AgentPhase.READY:
                raise RuntimeError("agent_busy")
            if self._turns >= self._max_turns:
                raise RuntimeError("agent_turn_budget_exceeded")
            self._turns += 1
            self._transition(AgentPhase.PERCEIVING)
        try:
            normalized = self._normalize_input(value)
            with self._lock:
                self._transition(AgentPhase.UNDERSTANDING)
            understanding = self.cognition.understand(normalized)
            if not isinstance(understanding, Mapping):
                raise ValueError("invalid_understanding")
            if self.memory is not None:
                recalled = self.memory.recall(normalized.principal_id, normalized.session_id, str(understanding.get("query", "")))
                understanding = dict(understanding)
                understanding["memory"] = tuple(recalled)
            with self._lock:
                self._transition(AgentPhase.PLANNING)
            plan = self.cognition.plan(understanding)
            if not isinstance(plan, AgentPlan):
                raise ValueError("invalid_agent_plan")
            result: Any = understanding
            action_steps = tuple(step for step in plan.steps if step.startswith("action:"))
            if action_steps:
                if self.authorizer is None or self.executor is None:
                    raise PermissionError("action_boundary_unavailable")
                with self._lock:
                    self._transition(AgentPhase.AUTHORIZING)
                for action in action_steps:
                    action_name = action.removeprefix("action:").strip()
                    if not action_name or not self.authorizer.authorize(self.agent_id, normalized.principal_id, action_name):
                        raise PermissionError("agent_action_denied")
                with self._lock:
                    self._transition(AgentPhase.ACTING)
                for action in action_steps:
                    result = self.executor.execute(self.agent_id, normalized.principal_id, action.removeprefix("action:").strip())
            with self._lock:
                self._transition(AgentPhase.VERIFYING)
            if self.verifier is not None and not self.verifier.verify(result, stage="agent_result"):
                raise PermissionError("agent_result_unverified")
            with self._lock:
                self._transition(AgentPhase.REFLECTING)
            if self.memory is not None:
                self.memory.remember(normalized.principal_id, normalized.session_id, result)
            with self._lock:
                self._transition(AgentPhase.RESPONDING)
            text = self.cognition.respond(understanding, result)
            response = AgentResponse(self.agent_id, normalized.session_id, normalized.principal_id, text, OutputModality.TEXT, True)
            with self._lock:
                self._transition(AgentPhase.READY)
            return response
        except Exception:
            with self._lock:
                self._phase = AgentPhase.FAILED
            raise

    def speak(self, response: AgentResponse) -> Any:
        if self.speech is None:
            raise PermissionError("voice_output_unavailable")
        if not isinstance(response, AgentResponse) or response.agent_id != self.agent_id or not response.verified:
            raise PermissionError("unverified_agent_response")
        return self.speech.synthesize(response.text)
