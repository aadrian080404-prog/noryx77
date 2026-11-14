import concurrent.futures

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.journal_integrity import AnchorSnapshot, ZERO_MAC
from core.remote_witness import RemoteMonotonicAnchor
from core.witness_authority import InProcessWitnessClient, SQLiteWitnessAuthority


def make_authority(path, private_key):
    return SQLiteWitnessAuthority(
        str(path), witness_id="witness-test", signing_key=private_key
    )


def make_anchor(authority, private_key):
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return RemoteMonotonicAnchor(
        InProcessWitnessClient(authority),
        witness_id="witness-test",
        trusted_public_key=public_key,
    )


def test_authority_works_with_signed_remote_anchor_and_survives_restart(tmp_path):
    path = tmp_path / "witness.sqlite"
    private_key = Ed25519PrivateKey.generate()
    authority = make_authority(path, private_key)
    anchor = make_anchor(authority, private_key)

    initial = anchor.read()
    assert initial == AnchorSnapshot(0, ZERO_MAC)
    next_head = AnchorSnapshot(1, "a" * 64)
    assert anchor.compare_and_swap(initial, next_head) is True
    assert anchor.read() == next_head
    authority.close()

    restarted = make_authority(path, private_key)
    assert make_anchor(restarted, private_key).read() == next_head
    restarted.close()


def test_compare_and_swap_rejects_stale_expected_head(tmp_path):
    authority = make_authority(tmp_path / "witness.sqlite", Ed25519PrivateKey.generate())
    current = authority.read_anchor(b"n" * 32).snapshot
    first = AnchorSnapshot(1, "a" * 64)
    second = AnchorSnapshot(1, "b" * 64)

    accepted = authority.compare_and_swap_anchor(current, first, b"x" * 32)
    rejected = authority.compare_and_swap_anchor(current, second, b"y" * 32)

    assert accepted.accepted is True
    assert accepted.snapshot == first
    assert rejected.accepted is False
    assert rejected.snapshot == first
    authority.close()


def test_concurrent_compare_and_swap_has_exactly_one_winner(tmp_path):
    path = tmp_path / "witness.sqlite"
    private_key = Ed25519PrivateKey.generate()
    first = make_authority(path, private_key)
    second = make_authority(path, private_key)
    expected = AnchorSnapshot(0, ZERO_MAC)
    replacement = AnchorSnapshot(1, "c" * 64)

    def attempt(authority, nonce):
        return authority.compare_and_swap_anchor(expected, replacement, nonce).accepted

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda item: attempt(item[0], item[1]),
            [(first, b"1" * 32), (second, b"2" * 32)],
        ))

    assert sorted(outcomes) == [False, True]
    assert first.read_anchor(b"3" * 32).snapshot == replacement
    first.close()
    second.close()


@pytest.mark.parametrize("nonce", [b"", b"x" * 31, b"x" * 33, "x" * 32, None])
def test_nonce_must_be_exactly_32_bytes(tmp_path, nonce):
    authority = make_authority(tmp_path / "witness.sqlite", Ed25519PrivateKey.generate())
    with pytest.raises(ValueError, match="witness_request_nonce_must_be_32_bytes"):
        authority.read_anchor(nonce)
    authority.close()


def test_invalid_anchor_transition_is_rejected(tmp_path):
    authority = make_authority(tmp_path / "witness.sqlite", Ed25519PrivateKey.generate())
    with pytest.raises(ValueError, match="witness_anchor_transition_invalid"):
        authority.compare_and_swap_anchor(
            AnchorSnapshot(0, ZERO_MAC), AnchorSnapshot(2, "d" * 64), b"z" * 32
        )
    authority.close()
