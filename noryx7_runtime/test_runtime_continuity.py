import hashlib
import secrets

import pytest

from .attestation import Ed25519AttestationSigner, attestation_digest, signed_attestation
from .contracts import Attestation
from .model_fabric import ModelFabric, ModelRequest
from .state import StateJournal


class FakeModel:
    def __init__(self, name: str):
        self.name = name
        self.capabilities = frozenset({"text"})
        self.cost_per_call = 1.0
        self.expected_latency_ms = 1.0

    def generate(self, prompt: str, *, tools=()):
        return f"{self.name}:{prompt}:{','.join(tools)}"


def make_attestation(signer, *, runtime_id="runtime-a", execution_id="exec-1", step_id="step-1", previous="0" * 64):
    return signed_attestation(
        Attestation(
            execution_id=execution_id,
            principal_id="principal-1",
            step_id=step_id,
            agent_id="agent-1",
            agent_key_fingerprint=hashlib.sha256(signer.public_key_bytes).hexdigest(),
            action_digest="a" * 64,
            output_digest="b" * 64,
            verified=True,
            detail="verified",
            previous_attestation_digest=previous,
            runtime_id=runtime_id,
        ),
        signer,
    )


def test_valid_chain_is_bound_to_its_runtime():
    signer = Ed25519AttestationSigner.generate()
    source = StateJournal(verifier=signer, runtime_id="runtime-a")
    first = make_attestation(signer, runtime_id="runtime-a")
    source.append(first)

    target = StateJournal(verifier=signer, runtime_id="runtime-b")
    with pytest.raises(PermissionError, match="runtime identity mismatch"):
        target.append(first)


def test_runtime_binding_cannot_be_swapped_without_resigning():
    signer = Ed25519AttestationSigner.generate()
    journal = StateJournal(verifier=signer, runtime_id="runtime-a")
    original = make_attestation(signer, runtime_id="runtime-a")
    forged = Attestation(
        execution_id=original.execution_id,
        principal_id=original.principal_id,
        step_id=original.step_id,
        agent_id=original.agent_id,
        agent_key_fingerprint=original.agent_key_fingerprint,
        action_digest=original.action_digest,
        output_digest=original.output_digest,
        verified=original.verified,
        detail=original.detail,
        signature=original.signature,
        previous_attestation_digest=original.previous_attestation_digest,
        runtime_id="runtime-b",
    )
    with pytest.raises(PermissionError, match="invalid attestation signature"):
        journal.append(forged)


def test_runtime_id_is_part_of_chain_digest():
    signer = Ed25519AttestationSigner.generate()
    a = make_attestation(signer, runtime_id="runtime-a")
    b = make_attestation(signer, runtime_id="runtime-b")
    assert attestation_digest(a) != attestation_digest(b)


def test_model_fabric_rejects_cross_runtime_request():
    fabric = ModelFabric([FakeModel("a")], runtime_id="runtime-a", binding_key=secrets.token_bytes(32))
    with pytest.raises(PermissionError, match="runtime identity mismatch"):
        fabric.route(ModelRequest("hello", runtime_id="runtime-b"))


def test_model_fabric_result_is_bound_to_request_and_runtime():
    key = secrets.token_bytes(32)
    fabric = ModelFabric([FakeModel("a")], runtime_id="runtime-a", binding_key=key)
    request = ModelRequest("hello", runtime_id="runtime-a")
    result = fabric.execute(request)
    assert fabric.verify_result(request, result)

    forged = type(result)(
        result.output,
        result.candidates,
        result.selected_model,
        result.confidence,
        result.degraded,
        "runtime-b",
        result.request_digest,
        result.result_mac,
    )
    assert fabric.verify_result(request, forged) is False


def test_model_fabric_detects_output_tampering():
    key = secrets.token_bytes(32)
    fabric = ModelFabric([FakeModel("a")], runtime_id="runtime-a", binding_key=key)
    request = ModelRequest("hello", runtime_id="runtime-a")
    result = fabric.execute(request)
    forged = type(result)(
        "attacker-output",
        result.candidates,
        result.selected_model,
        result.confidence,
        result.degraded,
        result.runtime_id,
        result.request_digest,
        result.result_mac,
    )
    assert fabric.verify_result(request, forged) is False
