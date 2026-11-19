from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.durable_trust_bootstrap import build_durable_trust_runtime
from core.identity import AgentIdentityAuthority
from core.sqlite_agent_identity_registry import SQLiteAgentIdentityRegistry
from core.sqlite_authorization_replay import SQLiteAuthorizationReplayGuard


class TestKeyProvider:
    def __init__(self, private_key):
        self._private_key = private_key

    def public_key(self, key_id):
        return self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    def sign(self, key_id, message):
        return self._private_key.sign(message)


class TestWitness:
    def __init__(self, epoch=4):
        self.epoch = epoch

    def read_epoch(self, namespace):
        return self.epoch

    def advance_epoch(self, namespace, expected_epoch, next_epoch):
        if self.epoch != expected_epoch or next_epoch != expected_epoch + 1:
            return False
        self.epoch = next_epoch
        return True


def _setup(tmp_path):
    identity, private_key = AgentIdentityAuthority.generate("durable-bootstrap-agent")
    registry = SQLiteAgentIdentityRegistry(tmp_path / "identity.sqlite")
    registry.register(identity)
    replay = SQLiteAuthorizationReplayGuard(tmp_path / "replay.sqlite", max_tokens=64)
    return identity, private_key, registry, replay


def test_bootstrap_builds_chain_only_with_all_durable_dependencies(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    runtime = build_durable_trust_runtime(
        identity_registry=registry,
        replay_guard=replay,
        key_provider=TestKeyProvider(private_key),
        key_id="kms://agent/key-1",
        agent_identity=identity,
        witness=TestWitness(4),
        witness_namespace="noryx7/trust",
        local_epoch=4,
        principal_id="principal-1",
        principal_agent_binding_verifier=lambda principal, agent: (
            principal == "principal-1" and agent == identity.agent_id
        ),
    )
    assert runtime.trust_chain.registry is registry
    assert runtime.trust_chain.replay_guard is replay
    assert runtime.epoch == 4
    replay.close()
    registry.close()


def test_bootstrap_rejects_missing_or_inactive_principal_binding(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    try:
        build_durable_trust_runtime(
            identity_registry=registry,
            replay_guard=replay,
            key_provider=TestKeyProvider(private_key),
            key_id="kms://agent/key-1",
            agent_identity=identity,
            witness=TestWitness(4),
            witness_namespace="noryx7/trust",
            local_epoch=4,
            principal_id="principal-1",
            principal_agent_binding_verifier=lambda *_: False,
        )
    except PermissionError as exc:
        assert str(exc) == "principal_agent_binding_not_active"
    else:
        raise AssertionError("inactive binding must block bootstrap")
    replay.close()
    registry.close()


def test_bootstrap_rejects_witness_mismatch_before_chain_construction(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    try:
        build_durable_trust_runtime(
            identity_registry=registry,
            replay_guard=replay,
            key_provider=TestKeyProvider(private_key),
            key_id="kms://agent/key-1",
            agent_identity=identity,
            witness=TestWitness(5),
            witness_namespace="noryx7/trust",
            local_epoch=4,
            principal_id="principal-1",
            principal_agent_binding_verifier=lambda *_: True,
        )
    except PermissionError as exc:
        assert str(exc) == "monotonic_epoch_mismatch"
    else:
        raise AssertionError("witness mismatch must block bootstrap")
    replay.close()
    registry.close()


def test_bootstrap_rejects_wrong_key_provider(tmp_path):
    identity, _private_key, registry, replay = _setup(tmp_path)
    wrong_provider = TestKeyProvider(Ed25519PrivateKey.generate())
    try:
        build_durable_trust_runtime(
            identity_registry=registry,
            replay_guard=replay,
            key_provider=wrong_provider,
            key_id="kms://wrong/key",
            agent_identity=identity,
            witness=TestWitness(4),
            witness_namespace="noryx7/trust",
            local_epoch=4,
            principal_id="principal-1",
            principal_agent_binding_verifier=lambda *_: True,
        )
    except PermissionError as exc:
        assert str(exc) == "signing_key_identity_mismatch"
    else:
        raise AssertionError("wrong key must block bootstrap")
    replay.close()
    registry.close()


def test_bootstrap_rejects_ephemeral_replay_guard(tmp_path):
    identity, private_key, registry, _replay = _setup(tmp_path)
    from core.authorization_replay import AuthorizationReplayGuard

    try:
        build_durable_trust_runtime(
            identity_registry=registry,
            replay_guard=AuthorizationReplayGuard(),
            key_provider=TestKeyProvider(private_key),
            key_id="kms://agent/key-1",
            agent_identity=identity,
            witness=TestWitness(4),
            witness_namespace="noryx7/trust",
            local_epoch=4,
            principal_id="principal-1",
            principal_agent_binding_verifier=lambda *_: True,
        )
    except TypeError as exc:
        assert str(exc) == "durable_replay_guard_required"
    else:
        raise AssertionError("ephemeral replay guard must be rejected")
    registry.close()
