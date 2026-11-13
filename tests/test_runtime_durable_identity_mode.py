import pytest

from core.durable_identity import DurableIdentityRegistry
from core.identity import IdentityRegistry
from noryx7_runtime.engine import RuntimeEngine


KEY = b"identity-runtime-mode-test-key-material-at-least-32-bytes"


def test_strict_identity_mode_rejects_missing_registry():
    with pytest.raises(ValueError, match="durable_identity_registry_required"):
        RuntimeEngine(require_durable_identity_registry=True)


def test_strict_identity_mode_rejects_memory_only_registry():
    with pytest.raises(ValueError, match="durable_identity_registry_required"):
        RuntimeEngine(
            identity_registry=IdentityRegistry(),
            require_durable_identity_registry=True,
        )


def test_strict_identity_mode_accepts_durable_registry(tmp_path):
    registry = DurableIdentityRegistry(
        str(tmp_path / "identity.sqlite"),
        integrity_key=KEY,
        key_id="identity-v1",
    )
    engine = RuntimeEngine(
        identity_registry=registry,
        require_durable_identity_registry=True,
    )
    assert engine.runtime_id
    registry.close()


def test_strict_identity_mode_rejects_closed_registry(tmp_path):
    registry = DurableIdentityRegistry(
        str(tmp_path / "identity.sqlite"),
        integrity_key=KEY,
        key_id="identity-v1",
    )
    registry.close()
    with pytest.raises(ValueError, match="durable_identity_registry_required"):
        RuntimeEngine(
            identity_registry=registry,
            require_durable_identity_registry=True,
        )


def test_strict_identity_mode_requires_boolean():
    with pytest.raises(TypeError, match="require_durable_identity_registry"):
        RuntimeEngine(require_durable_identity_registry="true")
