import pytest

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


def test_bootstrap_rejects_invalid_epoch_types_and_uint64_overflow(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    base = dict(
        identity_registry=registry,
        replay_guard=replay,
        key_provider=TestKeyProvider(private_key),
        key_id="kms://agent/key-1",
        agent_identity=identity,
        witness=TestWitness(4),
        witness_namespace="noryx7/trust",
        principal_id="principal-1",
        principal_agent_binding_verifier=lambda principal, agent: True,
    )
    try:
        for invalid_epoch in (True, False, -1, "4", 1.5, 1 << 64):
            try:
                build_durable_trust_runtime(**base, local_epoch=invalid_epoch)
            except ValueError as exc:
                assert str(exc) == "invalid_local_witness_epoch"
            else:
                raise AssertionError(f"invalid epoch accepted: {invalid_epoch!r}")
    finally:
        replay.close()
        registry.close()


def test_bootstrap_rejects_overlong_namespace_principal_and_key_handle(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    base = dict(
        identity_registry=registry,
        replay_guard=replay,
        key_provider=TestKeyProvider(private_key),
        key_id="kms://agent/key-1",
        agent_identity=identity,
        witness=TestWitness(4),
        witness_namespace="noryx7/trust",
        local_epoch=4,
        principal_id="principal-1",
        principal_agent_binding_verifier=lambda principal, agent: True,
    )
    try:
        for override, expected in (
            ({"witness_namespace": "x" * 513}, "witness_namespace_too_long"),
            ({"principal_id": "p" * 257}, "principal_id_too_long"),
            ({"key_id": "k" * 513}, "key_id_too_long"),
        ):
            values = {**base, **override}
            try:
                build_durable_trust_runtime(**values)
            except ValueError as exc:
                assert str(exc) == expected
            else:
                raise AssertionError(f"overlong identifier accepted: {expected}")
    finally:
        replay.close()
        registry.close()


def test_invalid_epoch_is_rejected_before_witness_key_or_binding_calls(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class CountingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.read_calls = 0

        def read_epoch(self, namespace):
            self.read_calls += 1
            return super().read_epoch(namespace)

    class CountingKeyProvider(TestKeyProvider):
        def __init__(self, key):
            super().__init__(key)
            self.sign_calls = 0

        def sign(self, key_id, message):
            self.sign_calls += 1
            return super().sign(key_id, message)

    witness = CountingWitness()
    key_provider = CountingKeyProvider(private_key)
    binding_calls = []
    try:
        with pytest.raises(ValueError, match="invalid_local_witness_epoch"):
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=key_provider,
                key_id="kms://agent/key-1",
                agent_identity=identity,
                witness=witness,
                witness_namespace="noryx7/trust",
                local_epoch=True,
                principal_id="principal-1",
                principal_agent_binding_verifier=lambda *args: binding_calls.append(args) or True,
            )
        assert witness.read_calls == 0
        assert key_provider.sign_calls == 0
        assert binding_calls == []
    finally:
        replay.close()
        registry.close()


def test_invalid_key_handle_is_rejected_before_witness_and_binding_calls(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class CountingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.read_calls = 0

        def read_epoch(self, namespace):
            self.read_calls += 1
            return super().read_epoch(namespace)

    witness = CountingWitness()
    binding_calls = []
    try:
        with pytest.raises(ValueError, match="key_id_too_long"):
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=TestKeyProvider(private_key),
                key_id="k" * 513,
                agent_identity=identity,
                witness=witness,
                witness_namespace="noryx7/trust",
                local_epoch=4,
                principal_id="principal-1",
                principal_agent_binding_verifier=lambda *args: binding_calls.append(args) or True,
            )
        assert witness.read_calls == 0
        assert binding_calls == []
    finally:
        replay.close()
        registry.close()



def test_invalid_key_handle_is_rejected_before_signing_challenge(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class CountingKeyProvider(TestKeyProvider):
        def __init__(self, key):
            super().__init__(key)
            self.sign_calls = 0

        def sign(self, key_id, message):
            self.sign_calls += 1
            return super().sign(key_id, message)

    key_provider = CountingKeyProvider(private_key)
    try:
        with pytest.raises(ValueError, match="key_id_too_long"):
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=key_provider,
                key_id="k" * 513,
                agent_identity=identity,
                witness=TestWitness(4),
                witness_namespace="noryx7/trust",
                local_epoch=4,
                principal_id="principal-1",
                principal_agent_binding_verifier=lambda *_: True,
            )
        assert key_provider.sign_calls == 0
    finally:
        replay.close()
        registry.close()



def test_malformed_utf8_identifiers_are_rejected_before_trust_side_effects(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class CountingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.read_calls = 0

        def read_epoch(self, namespace):
            self.read_calls += 1
            return super().read_epoch(namespace)

    class CountingKeyProvider(TestKeyProvider):
        def __init__(self, key):
            super().__init__(key)
            self.sign_calls = 0

        def sign(self, key_id, message):
            self.sign_calls += 1
            return super().sign(key_id, message)

    witness = CountingWitness()
    provider = CountingKeyProvider(private_key)
    binding_calls = []
    invalid = (
        ({"witness_namespace": "\ud800"}, "witness_namespace_invalid_encoding"),
        ({"principal_id": "\ud800"}, "principal_id_invalid_encoding"),
        ({"key_id": "\ud800"}, "key_id_invalid_encoding"),
    )
    try:
        for override, expected in invalid:
            with pytest.raises(ValueError, match=expected):
                build_durable_trust_runtime(
                    identity_registry=registry,
                    replay_guard=replay,
                    key_provider=provider,
                    key_id=override.get("key_id", "kms://agent/key-1"),
                    agent_identity=identity,
                    witness=witness,
                    witness_namespace=override.get("witness_namespace", "noryx7/trust"),
                    local_epoch=4,
                    principal_id=override.get("principal_id", "principal-1"),
                    principal_agent_binding_verifier=lambda *args: binding_calls.append(args) or True,
                )
        assert witness.read_calls == 0
        assert provider.sign_calls == 0
        assert binding_calls == []
    finally:
        replay.close()
        registry.close()
