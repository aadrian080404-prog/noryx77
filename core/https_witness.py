"""Mutual-TLS HTTPS transport for the NORYX7 remote witness contract.

The SQLiteWitnessAuthority remains the service-side monotonic state machine.
This module supplies a strict HTTPS/mTLS envelope without managing private
signing keys or weakening certificate verification.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading
from typing import Callable
from urllib.error import URLError, HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .journal_integrity import AnchorSnapshot
from .remote_witness import SignedWitnessReceipt


MAX_BODY = 16 * 1024
_READ_PATH = "/v1/anchor/read"
_CAS_PATH = "/v1/anchor/cas"


def _snapshot_json(snapshot: AnchorSnapshot) -> dict[str, object]:
    return {"sequence": snapshot.sequence, "mac": snapshot.mac}


def _decode_snapshot(value: object) -> AnchorSnapshot:
    if not isinstance(value, dict) or set(value) != {"sequence", "mac"}:
        raise ValueError("invalid_witness_snapshot")
    sequence, mac = value["sequence"], value["mac"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("invalid_witness_sequence")
    if not isinstance(mac, str) or len(mac) != 64:
        raise ValueError("invalid_witness_mac")
    try:
        if len(bytes.fromhex(mac)) != 32:
            raise ValueError("invalid_witness_mac")
    except ValueError as exc:
        raise ValueError("invalid_witness_mac") from exc
    return AnchorSnapshot(sequence, mac)


def _encode_receipt(receipt: SignedWitnessReceipt) -> bytes:
    payload = {
        "witness_id": receipt.witness_id,
        "operation": receipt.operation,
        "nonce": receipt.nonce.hex(),
        "snapshot": _snapshot_json(receipt.snapshot),
        "accepted": receipt.accepted,
        "signature": receipt.signature.hex(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _decode_receipt(raw: bytes) -> SignedWitnessReceipt:
    if not isinstance(raw, bytes) or len(raw) > MAX_BODY:
        raise ValueError("witness_response_too_large")
    value = json.loads(raw.decode("utf-8"))
    expected = {"witness_id", "operation", "nonce", "snapshot", "accepted", "signature"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("invalid_witness_receipt_schema")
    if not isinstance(value["witness_id"], str) or not isinstance(value["operation"], str):
        raise ValueError("invalid_witness_receipt_identity")
    if not isinstance(value["nonce"], str) or not isinstance(value["signature"], str):
        raise ValueError("invalid_witness_receipt_encoding")
    if not isinstance(value["accepted"], bool):
        raise ValueError("invalid_witness_receipt_acceptance")
    try:
        nonce, signature = bytes.fromhex(value["nonce"]), bytes.fromhex(value["signature"])
    except ValueError as exc:
        raise ValueError("invalid_witness_receipt_encoding") from exc
    if len(nonce) != 32 or len(signature) != 64:
        raise ValueError("invalid_witness_receipt_encoding")
    return SignedWitnessReceipt(
        witness_id=value["witness_id"], operation=value["operation"],
        nonce=nonce, snapshot=_decode_snapshot(value["snapshot"]),
        accepted=value["accepted"], signature=signature,
    )


class HTTPSWitnessClient:
    """HTTPS client with mandatory server verification and client certificate."""

    def __init__(self, base_url: str, *, ca_file: str, client_cert: str,
                 client_key: str, timeout: float = 5.0) -> None:
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("witness_https_url_required")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("witness_base_url_must_not_include_path")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 60:
            raise ValueError("invalid_witness_timeout")
        self._base = base_url.rstrip("/")
        self._timeout = float(timeout)
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        context.load_cert_chain(certfile=client_cert, keyfile=client_key)
        self._context = context

    def _post(self, path: str, payload: dict[str, object]) -> SignedWitnessReceipt:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(body) > MAX_BODY:
            raise ValueError("witness_request_too_large")
        request = Request(
            self._base + path, data=body, method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urlopen(request, context=self._context, timeout=self._timeout) as response:
                if response.status != 200:
                    raise RuntimeError("witness_http_status_invalid")
                if response.headers.get_content_type() != "application/json":
                    raise RuntimeError("witness_content_type_invalid")
                raw = response.read(MAX_BODY + 1)
        except (HTTPError, URLError, TimeoutError, ssl.SSLError) as exc:
            raise RuntimeError("witness_https_transport_failed") from exc
        return _decode_receipt(raw)

    def read_anchor(self, nonce: bytes) -> SignedWitnessReceipt:
        if not isinstance(nonce, bytes) or len(nonce) != 32:
            raise ValueError("witness_request_nonce_must_be_32_bytes")
        return self._post(_READ_PATH, {"nonce": nonce.hex()})

    def compare_and_swap_anchor(self, expected: AnchorSnapshot,
                                replacement: AnchorSnapshot,
                                nonce: bytes) -> SignedWitnessReceipt:
        if not isinstance(nonce, bytes) or len(nonce) != 32:
            raise ValueError("witness_request_nonce_must_be_32_bytes")
        return self._post(_CAS_PATH, {
            "nonce": nonce.hex(), "expected": _snapshot_json(expected),
            "replacement": _snapshot_json(replacement),
        })


def make_witness_server(authority, *, host: str, port: int, cert_file: str,
                        key_file: str, client_ca_file: str) -> ThreadingHTTPServer:
    """Create (but do not start) a TLS server requiring client certificates."""
    if not isinstance(host, str) or not host.strip():
        raise ValueError("witness_bind_host_required")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("witness_bind_port_invalid")
    if not callable(getattr(authority, "read_anchor", None)) or not callable(
        getattr(authority, "compare_and_swap_anchor", None)
    ):
        raise TypeError("witness_authority_contract_required")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "NORYX7-Witness"
        sys_version = ""

        def log_message(self, fmt, *args):
            # Avoid logging request bodies, peer identifiers or receipt material.
            return

        def _respond(self, status: int, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True

        def do_POST(self):
            if self.path not in (_READ_PATH, _CAS_PATH):
                self._respond(404, b'{"error":"not_found"}')
                return
            if self.headers.get_content_type() != "application/json":
                self._respond(415, b'{"error":"content_type_required"}')
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self._respond(400, b'{"error":"transfer_encoding_rejected"}')
                return
            length = self.headers.get("Content-Length")
            if length is None or not length.isdigit() or int(length) > MAX_BODY:
                self._respond(413, b'{"error":"body_size_invalid"}')
                return
            try:
                raw = self.rfile.read(int(length))
                if len(raw) != int(length):
                    raise ValueError("truncated_request")
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict) or not isinstance(payload.get("nonce"), str):
                    raise ValueError("invalid_request_schema")
                nonce = bytes.fromhex(payload["nonce"])
                if len(nonce) != 32:
                    raise ValueError("invalid_nonce")
                if self.path == _READ_PATH:
                    if set(payload) != {"nonce"}:
                        raise ValueError("invalid_read_schema")
                    receipt = authority.read_anchor(nonce)
                else:
                    if set(payload) != {"nonce", "expected", "replacement"}:
                        raise ValueError("invalid_cas_schema")
                    receipt = authority.compare_and_swap_anchor(
                        _decode_snapshot(payload["expected"]),
                        _decode_snapshot(payload["replacement"]), nonce,
                    )
                self._respond(200, _encode_receipt(receipt))
            except (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
                self._respond(400, b'{"error":"invalid_request"}')
            except Exception:
                self._respond(503, b'{"error":"witness_unavailable"}')

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.request_queue_size = 32
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(certfile=cert_file, keyfile=key_file)
    tls.load_verify_locations(cafile=client_ca_file)
    tls.verify_mode = ssl.CERT_REQUIRED
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    return server
