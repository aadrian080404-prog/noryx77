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



def test_bootstrap_rejects_non_utf8_surrogate_identifiers_before_witness_or_signing(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class RecordingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.calls = 0

        def read_epoch(self, namespace):
            self.calls += 1
            return super().read_epoch(namespace)

    witness = RecordingWitness()
    provider = TestKeyProvider(private_key)
    base = dict(
        identity_registry=registry,
        replay_guard=replay,
        key_provider=provider,
        key_id="kms://agent/key-1",
        agent_identity=identity,
        witness=witness,
        witness_namespace="noryx7/trust",
        local_epoch=4,
        principal_id="principal-1",
        principal_agent_binding_verifier=lambda principal, agent: True,
    )
    try:
        for override, expected in (
            ({"witness_namespace": "bad\ud800"}, "invalid_witness_namespace_encoding"),
            ({"principal_id": "bad\ud800"}, "invalid_principal_id_encoding"),
            ({"key_id": "bad\ud800"}, "invalid_key_id_encoding"),
        ):
            try:
                build_durable_trust_runtime(**{**base, **override})
            except ValueError as exc:
                assert str(exc) == expected
            else:
                raise AssertionError(f"invalid identifier encoding accepted: {expected}")
        assert witness.calls == 0
    finally:
        replay.close()
        registry.close()



def test_bootstrap_rejects_non_utf8_agent_id_before_identity_check_or_witness(tmp_path):
    from dataclasses import replace

    identity, private_key, registry, replay = _setup(tmp_path)

    class RecordingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.calls = 0

        def read_epoch(self, namespace):
            self.calls += 1
            return super().read_epoch(namespace)

    witness = RecordingWitness()
    invalid_identity = replace(identity, agent_id="bad\ud800")
    try:
        try:
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=TestKeyProvider(private_key),
                key_id="kms://agent/key-1",
                agent_identity=invalid_identity,
                witness=witness,
                witness_namespace="noryx7/trust",
                local_epoch=4,
                principal_id="principal-1",
                principal_agent_binding_verifier=lambda principal, agent: True,
            )
        except ValueError as exc:
            assert str(exc) == "invalid_agent_identity_encoding"
        else:
            raise AssertionError("invalid agent ID encoding accepted")
        assert witness.calls == 0
    finally:
        replay.close()
        registry.close()



def test_bootstrap_uses_live_durable_principal_agent_binding_registry(tmp_path):
    from core.principal_identity import PrincipalIdentityAuthority
    from core.sqlite_principal_identity import SQLitePrincipalIdentityRegistry
    from core.sqlite_principal_agent_binding import SQLitePrincipalAgentBindingRegistry

    identity, private_key, agent_registry, replay = _setup(tmp_path)
    principal, _ = PrincipalIdentityAuthority.generate("bootstrap-owner")
    principal_registry = SQLitePrincipalIdentityRegistry(tmp_path / "principal.sqlite")
    principal_registry.register(principal)
    bindings = SQLitePrincipalAgentBindingRegistry(
        tmp_path / "bindings.sqlite",
        principal_registry=principal_registry,
        agent_registry=agent_registry,
    )
    bindings.bind(principal.principal_id, identity.agent_id)

    base = dict(
        identity_registry=agent_registry,
        replay_guard=replay,
        key_provider=TestKeyProvider(private_key),
        key_id="kms://agent/key-1",
        agent_identity=identity,
        witness=TestWitness(4),
        witness_namespace="noryx7/trust",
        local_epoch=4,
        principal_id=principal.principal_id,
        principal_agent_binding_registry=bindings,
    )
    try:
        runtime = build_durable_trust_runtime(**base)
        assert runtime.agent_identity.agent_id == identity.agent_id
        bindings.revoke_binding(principal.principal_id, identity.agent_id)
        try:
            build_durable_trust_runtime(**base)
        except PermissionError as exc:
            assert str(exc) == "principal_agent_binding_not_active"
        else:
            raise AssertionError("revoked live binding must block bootstrap")
    finally:
        replay.close()
        agent_registry.close()
        principal_registry.close()


def test_bootstrap_rejects_ambiguous_binding_sources_before_witness(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)
    class RecordingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.calls = 0
        def read_epoch(self, namespace):
            self.calls += 1
            return super().read_epoch(namespace)

    witness = RecordingWitness()
    try:
        try:
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=TestKeyProvider(private_key),
                key_id="kms://agent/key-1",
                agent_identity=identity,
                witness=witness,
                witness_namespace="noryx7/trust",
                local_epoch=4,
                principal_id="principal-1",
                principal_agent_binding_verifier=lambda *_: True,
                principal_agent_binding_registry=object(),
            )
        except TypeError as exc:
            assert str(exc) == "ambiguous_principal_agent_binding_source"
        else:
            raise AssertionError("ambiguous binding sources accepted")
        assert witness.calls == 0
    finally:
        replay.close()
        registry.close()



def test_bootstrap_rejects_non_durable_binding_registry_before_witness(tmp_path):
    identity, private_key, registry, replay = _setup(tmp_path)

    class RecordingWitness(TestWitness):
        def __init__(self):
            super().__init__(4)
            self.calls = 0

        def read_epoch(self, namespace):
            self.calls += 1
            return super().read_epoch(namespace)

    witness = RecordingWitness()
    try:
        try:
            build_durable_trust_runtime(
                identity_registry=registry,
                replay_guard=replay,
                key_provider=TestKeyProvider(private_key),
                key_id="kms://agent/key-1",
                agent_identity=identity,
                witness=witness,
                witness_namespace="noryx7/trust",
                local_epoch=4,
                principal_id="principal-1",
                principal_agent_binding_registry=object(),
            )
        except TypeError as exc:
            assert str(exc) == "durable_principal_agent_binding_registry_required"
        else:
            raise AssertionError("non-durable binding registry accepted")
        assert witness.calls == 0
    finally:
        replay.close()
        registry.close()
