from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

from .agent_core import AgentInput, AgentResponse, InteractionMode
from .contracts import TaskSpec


class SpeechRecognizer(Protocol):
    def transcribe(self) -> str: ...


class SpeechSynthesizer(Protocol):
    def speak(self, text: str) -> None: ...


class CommandSpeechRecognizer:
    """STT adapter for a local command such as Termux:API."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.command = tuple(
            command
            or shlex.split(
                os.environ.get("NORYX7_STT_COMMAND", "termux-speech-to-text")
            )
        )
        if not self.command:
            raise ValueError("stt_command_required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("invalid_stt_timeout")
        self.timeout_seconds = float(timeout_seconds)

    def transcribe(self) -> str:
        try:
            completed = subprocess.run(
                self.command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("stt_command_not_found") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("stt_timeout") from exc
        except OSError as exc:
            raise RuntimeError("stt_execution_failed") from exc

        if completed.returncode != 0:
            raise RuntimeError("stt_failed")

        transcript = completed.stdout.strip()
        if not transcript:
            raise RuntimeError("stt_empty_transcript")
        return transcript


class CommandSpeechSynthesizer:
    """TTS adapter for a local command such as Termux:API."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.command = tuple(
            command
            or shlex.split(
                os.environ.get("NORYX7_TTS_COMMAND", "termux-tts-speak")
            )
        )
        if not self.command:
            raise ValueError("tts_command_required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
        ):
            raise ValueError("invalid_tts_timeout")
        self.timeout_seconds = float(timeout_seconds)

    def speak(self, text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("tts_text_required")

        try:
            completed = subprocess.run(
                [*self.command, text],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("tts_command_not_found") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("tts_timeout") from exc
        except OSError as exc:
            raise RuntimeError("tts_execution_failed") from exc

        if completed.returncode != 0:
            raise RuntimeError("tts_failed")


class SpeechVoiceTransport:
    """Verified AgentResponse -> speech output boundary."""

    def __init__(self, synthesizer: SpeechSynthesizer) -> None:
        if not hasattr(synthesizer, "speak") or not callable(synthesizer.speak):
            raise TypeError("speech_synthesizer_required")
        self.synthesizer = synthesizer

    def deliver(self, response: AgentResponse) -> AgentResponse:
        if not isinstance(response, AgentResponse):
            raise TypeError("agent_response_required")
        if response.mode is not InteractionMode.VOICE:
            raise ValueError("voice_transport_requires_voice_response")
        if not response.verified:
            raise PermissionError("voice_response_unverified")

        self.synthesizer.speak(response.content)
        return response


@dataclass(frozen=True)
class VoiceInteractionResult:
    execution_id: str
    transcript: str
    response: AgentResponse
    runtime_result: Mapping[str, object]


class VoiceGateway:
    """Canonical voice ingress/egress boundary around NORYXRuntime."""

    SYSTEM_CLIENT_ID = "noryx7-voice"

    def __init__(
        self,
        runtime,
        recognizer: SpeechRecognizer,
        synthesizer: SpeechSynthesizer,
    ) -> None:
        if runtime is None or not hasattr(runtime, "run_hypersynth"):
            raise TypeError("noryx_runtime_required")
        if not hasattr(recognizer, "transcribe") or not callable(recognizer.transcribe):
            raise TypeError("speech_recognizer_required")
        if not hasattr(synthesizer, "speak") or not callable(synthesizer.speak):
            raise TypeError("speech_synthesizer_required")

        self.runtime = runtime
        self.recognizer = recognizer
        self.synthesizer = synthesizer
        self.transport = SpeechVoiceTransport(synthesizer)

    def _record_lifecycle(self, *, execution_id: str, phase: str, metadata: Mapping[str, object]) -> None:
        system_fabric = getattr(self.runtime, "system_fabric", None)
        if system_fabric is not None:
            system_fabric.record_execution(
                execution_id=execution_id,
                client_id=self.SYSTEM_CLIENT_ID,
                phase=phase,
                metadata=dict(metadata),
            )
        audit = getattr(self.runtime, "audit", None)
        if audit is not None and callable(getattr(audit, "record", None)):
            audit.record(
                f"voice_{phase}",
                execution_id=execution_id,
                phase=phase,
            )

    def listen(self) -> AgentInput:
        transcript = self.recognizer.transcribe()
        return AgentInput(content=transcript, mode=InteractionMode.VOICE)

    def run(
        self,
        *,
        task_type: str = "voice_interaction",
        objective: str = "Respond to the user's spoken request.",
        execution_id: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> VoiceInteractionResult:
        request = self.listen()
        execution_id = execution_id or uuid4().hex

        constraints: dict[str, object] = {
            "interaction_mode": InteractionMode.VOICE.value,
            "voice_input": True,
        }
        if context:
            constraints["interaction_context"] = dict(context)

        task = TaskSpec(
            task_id=f"voice:{execution_id}",
            task_type=task_type,
            objective=objective,
            input=request.content,
            constraints=constraints,
            execution_id=execution_id,
        )

        self._record_lifecycle(
            execution_id=execution_id,
            phase="received",
            metadata={"task_id": task.task_id, "task_type": task.task_type},
        )
        runtime_result = self.runtime.run_hypersynth(task)
        if not isinstance(runtime_result, dict):
            self._record_lifecycle(
                execution_id=execution_id,
                phase="rejected",
                metadata={"task_id": task.task_id, "reason": "voice_runtime_result_invalid"},
            )
            raise RuntimeError("voice_runtime_result_invalid")

        if runtime_result.get("status") != "completed":
            reason = str(runtime_result.get("reason", "voice_runtime_rejected"))
            self._record_lifecycle(
                execution_id=execution_id,
                phase="rejected",
                metadata={"task_id": task.task_id, "reason": reason},
            )
            raise PermissionError(reason)

        final_answer = runtime_result.get("result")
        if not isinstance(final_answer, str) or not final_answer.strip():
            self._record_lifecycle(
                execution_id=execution_id,
                phase="rejected",
                metadata={"task_id": task.task_id, "reason": "voice_runtime_output_invalid"},
            )
            raise RuntimeError("voice_runtime_output_invalid")

        response = AgentResponse(
            content=final_answer,
            mode=InteractionMode.VOICE,
            verified=True,
        )
        response = self.transport.deliver(response)
        self._record_lifecycle(
            execution_id=execution_id,
            phase="completed",
            metadata={"task_id": task.task_id, "verified": True},
        )

        return VoiceInteractionResult(
            execution_id=execution_id,
            transcript=request.content,
            response=response,
            runtime_result=runtime_result,
        )
