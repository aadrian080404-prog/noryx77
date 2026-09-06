"""Native operating contract and fast execution loop for NORYX7 agents.

The Agent Core is deliberately model/provider agnostic. It defines how an agent
perceives input, builds context, plans, requests authorization, acts, observes,
verifies, reflects and responds. Text and voice are transport adapters, not
separate brains, so the same agent remains deterministic about policy and
capabilities regardless of interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Callable, Mapping, Protocol


MAX_TEXT = 64 * 1024
MAX_CONTEXT_ITEMS = 128
MAX_PLAN_STEPS = 64


class AgentPhase(str, Enum):
    IDLE = "idle"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    AUTHORIZING = "authorizing"
    ACTING = "acting"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    RESPONDING = "responding"
    FAILED = "failed"


class InteractionMode(str, Enum):
    TEXT = "text"
    VOICE = "voice"


@dataclass(frozen=True)
class AgentInput:
    content: str
    mode: InteractionMode = InteractionMode.TEXT
    context: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("agent_input_required")
        if len(self.content.encode("utf-8")) > MAX_TEXT:
            raise ValueError("agent_input_too_large")
        if not isinstance(self.mode, InteractionMode):
            raise TypeError("invalid_interaction_mode")
        if not isinstance(self.context, Mapping) or len(self.context) > MAX_CONTEXT_ITEMS:
            raise ValueError("invalid_agent_context")


@dataclass(frozen=True)
class AgentContext:
    objective: str
    input: AgentInput
    facts: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentPlan:
    steps: tuple[str, ...]

    def validate(self) -> None:
        if not self.steps or len(self.steps) > MAX_PLAN_STEPS:
            raise ValueError("invalid_agent_plan")
        if any(not isinstance(step, str) or not step.strip() for step in self.steps):
            raise ValueError("invalid_agent_plan_step")


@dataclass(frozen=True)
class AgentResponse:
    content: str
    mode: InteractionMode
    phase: AgentPhase = AgentPhase.RESPONDING
    verified: bool = False


class AgentBrain(Protocol):
    def understand(self, request: AgentInput) -> AgentContext: ...
    def plan(self, context: AgentContext) -> AgentPlan: ...
    def act(self, context: AgentContext, step: str) -> Any: ...
    def verify(self, context: AgentContext, step: str, result: Any) -> bool: ...
    def reflect(self, context: AgentContext, results: tuple[Any, ...]) -> str: ...
    def respond(self, context: AgentContext, reflection: str, mode: InteractionMode) -> AgentResponse: ...


class AuthorizationHook(Protocol):
    def __call__(self, context: AgentContext, step: str) -> bool: ...


class AgentTransport(Protocol):
    def encode(self, response: AgentResponse) -> Any: ...


class TextTransport:
    def encode(self, response: AgentResponse) -> str:
        if not isinstance(response, AgentResponse):
            raise TypeError("agent_response_required")
        return response.content


class VoiceTransport:
    """Speech boundary only; actual STT/TTS engines are injected by the host."""
    def __init__(self, *, synthesize: Callable[[str], Any], transcribe: Callable[[Any], str] | None = None) -> None:
        if not callable(synthesize):
            raise TypeError("voice_synthesizer_required")
        if transcribe is not None and not callable(transcribe):
            raise TypeError("voice_transcriber_invalid")
        self._synthesize = synthesize
        self._transcribe = transcribe

    def decode(self, audio: Any) -> str:
        if self._transcribe is None:
            raise RuntimeError("voice_transcriber_unavailable")
        text = self._transcribe(audio)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("voice_transcription_invalid")
        return text

    def encode(self, response: AgentResponse) -> Any:
        if not isinstance(response, AgentResponse):
            raise TypeError("agent_response_required")
        return self._synthesize(response.content)


class AgentOperatingManual:
    """Immutable policy surface describing the mandatory agent lifecycle."""
    PHASES = (
        AgentPhase.UNDERSTANDING, AgentPhase.PLANNING, AgentPhase.AUTHORIZING,
        AgentPhase.ACTING, AgentPhase.OBSERVING, AgentPhase.VERIFYING,
        AgentPhase.REFLECTING, AgentPhase.RESPONDING,
    )

    @classmethod
    def validate(cls) -> None:
        if cls.PHASES[0] is not AgentPhase.UNDERSTANDING or cls.PHASES[-1] is not AgentPhase.RESPONDING:
            raise RuntimeError("agent_manual_corrupt")
        if len(set(cls.PHASES)) != len(cls.PHASES):
            raise RuntimeError("agent_manual_duplicate_phase")


class AgentCore:
    """Fast, bounded agent lifecycle with fail-closed authorization/verification."""
    def __init__(self, *, agent_id: str, brain: AgentBrain, authorize: AuthorizationHook | None = None,
                 transport: AgentTransport | None = None, max_steps: int = MAX_PLAN_STEPS) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id_required")
        for name in ("understand", "plan", "act", "verify", "reflect", "respond"):
            if not callable(getattr(brain, name, None)):
                raise TypeError(f"brain_missing_{name}")
        if authorize is not None and not callable(authorize):
            raise TypeError("authorize_must_be_callable")
        if transport is not None and not callable(getattr(transport, "encode", None)):
            raise TypeError("transport_must_expose_encode")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= MAX_PLAN_STEPS:
            raise ValueError("invalid_max_steps")
        AgentOperatingManual.validate()
        self.agent_id = agent_id
        self._brain = brain
        self._authorize = authorize
        self._transport = transport or TextTransport()
        self._max_steps = max_steps
        self._lock = RLock()
        self._phase = AgentPhase.IDLE

    @property
    def phase(self) -> AgentPhase:
        with self._lock:
            return self._phase

    def _set_phase(self, phase: AgentPhase) -> None:
        with self._lock:
            self._phase = phase

    def run(self, request: AgentInput) -> Any:
        request.validate()
        with self._lock:
            if self._phase is not AgentPhase.IDLE:
                raise RuntimeError("agent_busy")
            self._phase = AgentPhase.UNDERSTANDING
        try:
            context = self._brain.understand(request)
            if not isinstance(context, AgentContext):
                raise TypeError("brain_returned_invalid_context")
            self._set_phase(AgentPhase.PLANNING)
            plan = self._brain.plan(context)
            if not isinstance(plan, AgentPlan):
                raise TypeError("brain_returned_invalid_plan")
            plan.validate()
            if len(plan.steps) > self._max_steps:
                raise ValueError("agent_step_budget_exceeded")
            results: list[Any] = []
            for step in plan.steps:
                self._set_phase(AgentPhase.AUTHORIZING)
                if self._authorize is not None and not bool(self._authorize(context, step)):
                    raise PermissionError("agent_action_denied")
                self._set_phase(AgentPhase.ACTING)
                result = self._brain.act(context, step)
                self._set_phase(AgentPhase.OBSERVING)
                observed = result
                self._set_phase(AgentPhase.VERIFYING)
                if not bool(self._brain.verify(context, step, observed)):
                    raise PermissionError("agent_result_verification_failed")
                results.append(observed)
            self._set_phase(AgentPhase.REFLECTING)
            reflection = self._brain.reflect(context, tuple(results))
            if not isinstance(reflection, str) or len(reflection.encode("utf-8")) > MAX_TEXT:
                raise ValueError("agent_reflection_invalid")
            self._set_phase(AgentPhase.RESPONDING)
            response = self._brain.respond(context, reflection, request.mode)
            if not isinstance(response, AgentResponse) or not response.verified:
                raise PermissionError("agent_response_unverified")
            return self._transport.encode(response)
        except Exception:
            self._set_phase(AgentPhase.FAILED)
            raise
        finally:
            with self._lock:
                if self._phase is not AgentPhase.FAILED:
                    self._phase = AgentPhase.IDLE
