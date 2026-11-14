"""Mutual-TLS HTTPS transport for signed distributed-memory batches."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections.abc import Mapping
from hashlib import sha256
from threading import BoundedSemaphore
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .distributed_memory import MAX_MEMORY_VALUE, MemoryEvent, DistributedMemoryStore
from .identity import AgentIdentity, AgentAttestation, IdentityRegistry
from .signed_memory_replication import (
    MAX_SIGNED_BATCH_BYTES,
    SignedMemoryBatch,
    verify_and_merge_memory_batch,
)

_PATH = "/v1/memory/merge"


def _authenticated_peer_agent_id(certificate_der: bytes, fingerprint_to_agent: Mapping[str, str]) -> str:
    """Bind a CA-validated TLS client certificate to one configured agent ID."""
    if not isinstance(certificate_der, bytes) or not certificate_der:
        raise PermissionError("memory_peer_client_certificate_missing")
    fingerprint = sha256(certificate_der).hexdigest()
    agent_id = fingerprint_to_agent.get(fingerprint)
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise PermissionError("memory_peer_certificate_unmapped")
    return agent_id


def _batch_to_bytes(batch: SignedMemoryBatch) -> bytes:
    if not isinstance(batch, SignedMemoryBatch):
        raise TypeError("signed_memory_batch_required")
    identity = batch.attestation.identity
    payload = {
        "identity": {
            "agent_id": identity.agent_id,
            "public_key": identity.public_key.hex(),
            "version": identity.version,
        },
        "statement": batch.attestation.statement.hex(),
        "signature": batch.attestation.signature.hex(),
        "events": [{
            "actor_id": event.actor_id, "counter": event.counter,
            "key": event.key, "value": event.value, "deleted": event.deleted,
            "clock": [[actor, counter] for actor, counter in event.clock],
        } for event in batch.events],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_SIGNED_BATCH_BYTES:
        raise ValueError("signed_memory_batch_bytes_exceeded")
    return raw


def _batch_from_bytes(raw: bytes) -> SignedMemoryBatch:
    if not isinstance(raw, bytes) or len(raw) > MAX_SIGNED_BATCH_BYTES:
        raise ValueError("signed_memory_batch_bytes_exceeded")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"identity", "statement", "signature", "events"}:
        raise ValueError("invalid_signed_memory_batch_schema")
    identity_data = payload["identity"]
    if not isinstance(identity_data, dict) or set(identity_data) != {"agent_id", "public_key", "version"}:
        raise ValueError("invalid_memory_identity_schema")
    if not isinstance(identity_data["agent_id"], str) or not isinstance(identity_data["public_key"], str):
        raise ValueError("invalid_memory_identity_encoding")
    if isinstance(identity_data["version"], bool) or not isinstance(identity_data["version"], int):
        raise ValueError("invalid_memory_identity_version")
    try:
        public_key = bytes.fromhex(identity_data["public_key"])
        statement = bytes.fromhex(payload["statement"])
        signature = bytes.fromhex(payload["signature"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_signed_memory_batch_encoding") from exc
    identity = AgentIdentity(identity_data["agent_id"], public_key, identity_data["version"])
    attestation = AgentAttestation(identity, statement, signature)
    raw_events = payload["events"]
    if not isinstance(raw_events, list) or not 1 <= len(raw_events) <= 256:
        raise ValueError("invalid_signed_memory_event_count")
    events = []
    for item in raw_events:
        if not isinstance(item, dict) or set(item) != {"actor_id", "counter", "key", "value", "deleted", "clock"}:
            raise ValueError("invalid_memory_event_schema")
        clock = item["clock"]
        if not isinstance(clock, list) or len(clock) > 4096:
            raise ValueError("invalid_memory_clock")
        event = MemoryEvent(
            actor_id=item["actor_id"], counter=item["counter"], key=item["key"],
            value=item["value"], deleted=item["deleted"],
            clock=tuple((pair[0], pair[1]) for pair in clock
                        if isinstance(pair, list) and len(pair) == 2),
        )
        if len(event.clock) != len(clock):
            raise ValueError("invalid_memory_clock")
        event.validate()
        events.append(event)
    return SignedMemoryBatch(attestation, tuple(events))


class HTTPSMemoryPeerClient:
    """TLS-verifying client with mandatory client certificate authentication."""

    def __init__(self, base_url: str, *, ca_file: str,
                 client_cert: str, client_key: str, timeout: float = 5.0) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("memory_peer_https_required")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("memory_peer_base_url_invalid")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 60:
            raise ValueError("memory_peer_timeout_invalid")
        self._url = base_url.rstrip("/") + _PATH
        self._timeout = float(timeout)
        self._tls = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
        self._tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self._tls.verify_mode = ssl.CERT_REQUIRED
        self._tls.check_hostname = True
        self._tls.load_cert_chain(client_cert, client_key)

    def merge(self, batch: SignedMemoryBatch) -> int:
        body = _batch_to_bytes(batch)
        request = Request(self._url, data=body, method="POST",
                          headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urlopen(request, context=self._tls, timeout=self._timeout) as response:
                if response.status != 200 or response.headers.get_content_type() != "application/json":
                    raise RuntimeError("memory_peer_response_invalid")
                raw = response.read(1024)
        except (HTTPError, URLError, TimeoutError, ssl.SSLError) as exc:
            raise RuntimeError("memory_peer_transport_failed") from exc
        result = json.loads(raw.decode("utf-8"))
        if not isinstance(result, dict) or set(result) != {"inserted"}:
            raise RuntimeError("memory_peer_response_schema_invalid")
        inserted = result["inserted"]
        if isinstance(inserted, bool) or not isinstance(inserted, int) or inserted < 0:
            raise RuntimeError("memory_peer_insert_count_invalid")
        return inserted


def make_memory_peer_server(store: DistributedMemoryStore, registry: IdentityRegistry, *,
                            host: str, port: int, cert_file: str, key_file: str,
                            client_ca_file: str,
                            peer_certificate_agents: Mapping[str, str] | None = None,
                            request_timeout: float = 5.0,
                            max_concurrent_requests: int = 16) -> ThreadingHTTPServer:
    if not isinstance(store, DistributedMemoryStore) or not isinstance(registry, IdentityRegistry):
        raise TypeError("memory_peer_dependencies_required")
    if not isinstance(host, str) or not host.strip():
        raise ValueError("memory_peer_bind_host_required")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("memory_peer_bind_port_invalid")
    if not isinstance(peer_certificate_agents, Mapping) or not peer_certificate_agents:
        raise ValueError("memory_peer_certificate_mapping_required")
    certificate_agents = dict(peer_certificate_agents)
    for fingerprint, agent_id in certificate_agents.items():
        if (not isinstance(fingerprint, str) or len(fingerprint) != 64
                or any(char not in "0123456789abcdef" for char in fingerprint)
                or not isinstance(agent_id, str) or not agent_id.strip()):
            raise ValueError("memory_peer_certificate_mapping_invalid")
    if isinstance(request_timeout, bool) or not isinstance(request_timeout, (int, float)) or not 0.1 <= request_timeout <= 30:
        raise ValueError("memory_peer_request_timeout_invalid")
    if isinstance(max_concurrent_requests, bool) or not isinstance(max_concurrent_requests, int) or not 1 <= max_concurrent_requests <= 128:
        raise ValueError("memory_peer_concurrency_limit_invalid")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "NORYX7-Memory-Peer"
        sys_version = ""

        def log_message(self, fmt, *args):
            return

        def respond(self, status: int, payload: bytes):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True

        def do_POST(self):
            if self.path != _PATH:
                self.respond(404, b'{"error":"not_found"}')
                return
            if self.headers.get_content_type() != "application/json":
                self.respond(415, b'{"error":"json_required"}')
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self.respond(400, b'{"error":"transfer_encoding_rejected"}')
                return
            length = self.headers.get("Content-Length")
            if length is None or not length.isdigit() or not 1 <= int(length) <= MAX_SIGNED_BATCH_BYTES:
                self.respond(413, b'{"error":"body_size_invalid"}')
                return
            try:
                raw = self.rfile.read(int(length))
                if len(raw) != int(length):
                    raise ValueError("truncated_body")
                peer_agent_id = _authenticated_peer_agent_id(
                    self.connection.getpeercert(binary_form=True), certificate_agents
                )
                batch = _batch_from_bytes(raw)
                if batch.attestation.identity.agent_id != peer_agent_id:
                    raise PermissionError("memory_peer_certificate_identity_mismatch")
                inserted = verify_and_merge_memory_batch(store, batch, registry)
                body = json.dumps({"inserted": inserted}, separators=(",", ":")).encode("utf-8")
                self.respond(200, body)
            except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
                self.respond(400, b'{"error":"invalid_batch"}')
            except PermissionError:
                self.respond(403, b'{"error":"untrusted_sender"}')
            except Exception:
                self.respond(503, b'{"error":"memory_peer_unavailable"}')

    class BoundedMemoryPeerServer(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 32

        def __init__(self, address, handler):
            self._request_slots = BoundedSemaphore(max_concurrent_requests)
            super().__init__(address, handler)

        def get_request(self):
            request, address = super().get_request()
            request.settimeout(float(request_timeout))
            return request, address

        def process_request(self, request, client_address):
            if not self._request_slots.acquire(blocking=False):
                request.close()
                return
            try:
                super().process_request(request, client_address)
            except Exception:
                self._request_slots.release()
                raise

        def process_request_thread(self, request, client_address):
            try:
                super().process_request_thread(request, client_address)
            finally:
                self._request_slots.release()

    server = BoundedMemoryPeerServer((host, port), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(certfile=cert_file, keyfile=key_file)
    tls.load_verify_locations(cafile=client_ca_file)
    tls.verify_mode = ssl.CERT_REQUIRED
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    return server
