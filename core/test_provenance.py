import hashlib

import pytest

from .provenance import ProvenanceContext, canonical_digest, seal_provenance, verify_provenance


def context(**overrides):
    values = dict(
        runtime_id="runtime-a",
        execution_id="exec-a",
        principal_id="principal-a",
        memory_digest=canonical_digest({"memory": [1, 2]}),
        route_digest=canonical_digest({"agent": "agent-a", "policy": "normal"}),
        request_digest=canonical_digest({"task": "t1"}),
    )
    values.update(overrides)
    return ProvenanceContext(**values)


def test_provenance_is_deterministic():
    assert context().digest() == context().digest()


@pytest.mark.parametrize("field", ["runtime_id", "execution_id", "principal_id", "memory_digest", "route_digest", "request_digest"])
def test_provenance_detects_context_substitution(field):
    original = context()
    replacement = context(**{field: "runtime-b" if field == "runtime_id" else ("exec-b" if field == "execution_id" else ("principal-b" if field == "principal_id" else "f" * 64))})
    assert original.digest() != replacement.digest()


def test_seal_detects_context_tampering_and_wrong_key():
    key = hashlib.sha256(b"noryx7-provenance-test").digest()
    original = context()
    seal = seal_provenance(original, key)
    assert verify_provenance(original, seal, key)
    assert not verify_provenance(context(result_digest="a" * 64), seal, key)
    assert not verify_provenance(original, seal, hashlib.sha256(b"wrong").digest())


def test_result_binding_changes_context_digest():
    original = context()
    bound = original.bind_result({"answer": 42})
    assert original.result_digest == ""
    assert bound.result_digest == canonical_digest({"answer": 42})
    assert original.digest() != bound.digest()


def test_model_binding_is_part_of_provenance_digest():
    original = context()
    request_digest = canonical_digest({"request": "model"})
    bound = original.bind_model(request_digest, {"output": "answer", "selected_model": "reasoner"})
    assert bound.model_request_digest == request_digest
    assert bound.model_result_digest == canonical_digest({"output": "answer", "selected_model": "reasoner"})
    assert original.digest() != bound.digest()


def test_model_binding_tampering_breaks_seal():
    key = hashlib.sha256(b"noryx7-provenance-test").digest()
    request_digest = canonical_digest({"request": "model"})
    original = context().bind_model(request_digest, {"output": "answer"})
    seal = seal_provenance(original, key)
    assert verify_provenance(original, seal, key)
    assert not verify_provenance(context().bind_model(request_digest, {"output": "tampered"}), seal, key)
    assert not verify_provenance(context().bind_model(canonical_digest({"request": "other"}), {"output": "answer"}), seal, key)


def test_invalid_model_request_digest_cannot_be_bound():
    with pytest.raises(ValueError, match="invalid model request digest"):
        context().bind_model("bad", {"output": "answer"})


def test_invalid_context_cannot_be_sealed():
    key = hashlib.sha256(b"noryx7-provenance-test").digest()
    with pytest.raises(ValueError, match="invalid provenance context"):
        seal_provenance(context(memory_digest="bad"), key)
