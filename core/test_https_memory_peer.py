import json
import pytest

from core.distributed_memory import DistributedMemoryStore
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.signed_memory_replication import sign_memory_batch
from core.https_memory_peer import (
    _batch_from_bytes, _batch_to_bytes, _certificate_agent_id, make_memory_peer_server,
)


def test_signed_batch_wire_round_trip(tmp_path):
    identity, private = AgentIdentityAuthority.generate("peer-a")
    store = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="peer-a")
    store.write("fact", "verified")
    batch = sign_memory_batch(identity, private, store.export_since({}))
    decoded = _batch_from_bytes(_batch_to_bytes(batch))
    assert decoded == batch
    store.close()


def test_wire_schema_rejects_extra_fields_and_invalid_event(tmp_path):
    with pytest.raises(ValueError, match="schema"):
        _batch_from_bytes(b'{"extra":true}')
    identity, private = AgentIdentityAuthority.generate("peer-a")
    store = DistributedMemoryStore(str(tmp_path / "source.sqlite"), actor_id="peer-a")
    store.write("fact", "verified")
    batch = sign_memory_batch(identity, private, store.export_since({}))
    payload = json.loads(_batch_to_bytes(batch))
    payload["events"][0]["counter"] = True
    with pytest.raises(ValueError):
        _batch_from_bytes(json.dumps(payload).encode())
    store.close()


def test_server_rejects_invalid_bind_and_dependencies(tmp_path):
    store = DistributedMemoryStore(str(tmp_path / "memory.sqlite"), actor_id="peer-b")
    registry = IdentityRegistry()
    with pytest.raises(ValueError, match="port"):
        make_memory_peer_server(store, registry, host="127.0.0.1", port=0,
                                cert_file="cert", key_file="key", client_ca_file="ca",
                                certificate_identity_pins={"a" * 64: "peer-b"})
    store.close()



def test_tls_certificate_is_pinned_to_signed_agent_identity():
    import hashlib

    certificate = b"test-certificate-der"
    fingerprint = hashlib.sha256(certificate).hexdigest()
    pins = {fingerprint: "agent-alpha"}
    assert _certificate_agent_id(certificate, pins, "agent-alpha") == "agent-alpha"
    with pytest.raises(PermissionError, match="certificate_identity_mismatch"):
        _certificate_agent_id(certificate, pins, "agent-beta")
    with pytest.raises(PermissionError, match="certificate_unpinned"):
        _certificate_agent_id(certificate, {}, "agent-alpha")
    with pytest.raises(PermissionError, match="certificate_missing"):
        _certificate_agent_id(b"", pins, "agent-alpha")


def test_tls_server_rejects_missing_certificate_pin_configuration(tmp_path):
    store = DistributedMemoryStore(str(tmp_path / "memory-pins.sqlite"), actor_id="peer-b")
    registry = IdentityRegistry()
    with pytest.raises(ValueError, match="certificate_pins_required"):
        make_memory_peer_server(
            store, registry, host="127.0.0.1", port=12345,
            cert_file="cert", key_file="key", client_ca_file="ca",
            certificate_identity_pins={},
        )
    store.close()


def test_accepted_tls_socket_defers_handshake_out_of_accept_loop(monkeypatch):
    from socketserver import TCPServer
    from core.https_memory_peer import _BoundedThreadingHTTPServer

    class FakeSocket:
        timeout = None
        handshaken = False

        def settimeout(self, value):
            self.timeout = value

        def do_handshake(self):
            self.handshaken = True

        def close(self):
            pass

    fake = FakeSocket()
    monkeypatch.setattr(TCPServer, "get_request", lambda self: (fake, ("127.0.0.1", 1)))
    server = object.__new__(_BoundedThreadingHTTPServer)
    server._request_timeout = 1.25

    request, address = server.get_request()

    assert request is fake
    assert address == ("127.0.0.1", 1)
    assert fake.timeout == 1.25
    assert fake.handshaken is False
