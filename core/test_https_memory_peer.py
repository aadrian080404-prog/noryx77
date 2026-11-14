import json
import pytest

from core.distributed_memory import DistributedMemoryStore
from core.identity import AgentIdentityAuthority, IdentityRegistry
from core.signed_memory_replication import sign_memory_batch
from core.https_memory_peer import _batch_from_bytes, _batch_to_bytes, make_memory_peer_server


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
                                cert_file="cert", key_file="key", client_ca_file="ca")
    store.close()
