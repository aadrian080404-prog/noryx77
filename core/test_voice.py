from unittest.mock import Mock

import pytest

from .agent_core import AgentInput, AgentResponse, InteractionMode
from .voice import (
    CommandSpeechRecognizer,
    CommandSpeechSynthesizer,
    SpeechVoiceTransport,
    VoiceGateway,
)


def test_recognizer_returns_transcript():
    recognizer = CommandSpeechRecognizer(
        command=("python", "-c", "print('ciao noryx7')")
    )
    assert recognizer.transcribe() == "ciao noryx7"


def test_synthesizer_invokes_command():
    synthesizer = CommandSpeechSynthesizer(
        command=(
            "python",
            "-c",
            "import sys; assert sys.argv[1] == 'ciao noryx7'",
        )
    )
    synthesizer.speak("ciao noryx7")


def test_voice_transport_speaks_verified_voice_response():
    synthesizer = Mock()
    transport = SpeechVoiceTransport(synthesizer)
    response = AgentResponse(
        content="ciao",
        mode=InteractionMode.VOICE,
        verified=True,
    )

    assert transport.deliver(response) is response
    synthesizer.speak.assert_called_once_with("ciao")


def test_voice_transport_rejects_unverified_response():
    synthesizer = Mock()
    transport = SpeechVoiceTransport(synthesizer)
    response = AgentResponse(
        content="ciao",
        mode=InteractionMode.VOICE,
        verified=False,
    )

    with pytest.raises(PermissionError):
        transport.deliver(response)
    synthesizer.speak.assert_not_called()


def test_voice_gateway_listen_creates_voice_input():
    recognizer = Mock()
    recognizer.transcribe.return_value = "dimmi ciao"
    gateway = VoiceGateway(Mock(), recognizer, Mock())

    request = gateway.listen()

    assert isinstance(request, AgentInput)
    assert request.content == "dimmi ciao"
    assert request.mode is InteractionMode.VOICE


def test_voice_gateway_full_path_reaches_runtime_then_tts():
    runtime = Mock()
    recognizer = Mock()
    synthesizer = Mock()
    recognizer.transcribe.return_value = "quanto fa due più due"
    runtime.run_hypersynth.return_value = {
        "status": "completed",
        "execution_id": "voice-test-001",
        "result": "Quattro.",
    }

    gateway = VoiceGateway(runtime, recognizer, synthesizer)
    result = gateway.run(execution_id="voice-test-001")

    assert result.transcript == "quanto fa due più due"
    assert result.response.content == "Quattro."
    assert result.response.mode is InteractionMode.VOICE
    assert result.response.verified is True

    task = runtime.run_hypersynth.call_args.args[0]
    assert task.execution_id == "voice-test-001"
    assert task.input == "quanto fa due più due"
    assert task.constraints["interaction_mode"] == "voice"
    assert task.constraints["voice_input"] is True
    synthesizer.speak.assert_called_once_with("Quattro.")


def test_rejected_runtime_never_reaches_tts():
    runtime = Mock()
    recognizer = Mock()
    synthesizer = Mock()
    recognizer.transcribe.return_value = "esegui qualcosa"
    runtime.run_hypersynth.return_value = {
        "status": "rejected",
        "reason": "authorization_denied",
    }

    gateway = VoiceGateway(runtime, recognizer, synthesizer)

    with pytest.raises(PermissionError):
        gateway.run(execution_id="voice-test-denied")

    synthesizer.speak.assert_not_called()
