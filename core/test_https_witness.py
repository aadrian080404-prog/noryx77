import json
import ssl

import pytest

from core.https_witness import (
    HTTPSWitnessClient,
    _decode_receipt,
    _decode_snapshot,
    _encode_receipt,
    make_witness_server,
)
from core.journal_integrity import AnchorSnapshot
from core.remote_witness import SignedWitnessReceipt


def test_receipt_round_trip_is_strict():
    receipt = SignedWitnessReceipt("w1", "read", b"n" * 32,
                                   AnchorSnapshot(0, "0" * 64), True, b"s" * 64)
    assert _decode_receipt(_encode_receipt(receipt)) == receipt


def test_receipt_rejects_extra_fields_and_bad_lengths():
    with pytest.raises(ValueError, match="schema"):
        _decode_receipt(json.dumps({"extra": True}).encode())
    bad = {
        "witness_id": "w1", "operation": "read", "nonce": "00",
        "snapshot": {"sequence": 0, "mac": "0" * 64},
        "accepted": True, "signature": "00",
    }
    with pytest.raises(ValueError, match="encoding"):
        _decode_receipt(json.dumps(bad).encode())


def test_snapshot_rejects_boolean_sequence_and_non_hex_mac():
    with pytest.raises(ValueError, match="sequence"):
        _decode_snapshot({"sequence": True, "mac": "0" * 64})
    with pytest.raises(ValueError, match="mac"):
        _decode_snapshot({"sequence": 0, "mac": "z" * 64})


def test_client_requires_https_and_verified_certificate_paths():
    with pytest.raises(ValueError, match="https"):
        HTTPSWitnessClient("http://localhost", ca_file="ca.pem",
                           client_cert="client.pem", client_key="client.key")
    with pytest.raises(ValueError, match="path"):
        HTTPSWitnessClient("https://localhost/unsafe", ca_file="ca.pem",
                           client_cert="client.pem", client_key="client.key")


def test_server_requires_valid_authority_and_port():
    with pytest.raises(ValueError, match="port"):
        make_witness_server(object(), host="127.0.0.1", port=0,
                            cert_file="cert", key_file="key", client_ca_file="ca")
