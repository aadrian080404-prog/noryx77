import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from core.journal_integrity import AnchorSnapshot, ZERO_MAC
from core.quorum_witness import QuorumMonotonicAnchor
from core.remote_witness import RemoteMonotonicAnchor
from core.witness_authority import InProcessWitnessClient, SQLiteWitnessAuthority


def make_witnesses(tmp_path):
    anchors = []
    authorities = []
    for index in range(3):
        key = Ed25519PrivateKey.generate()
        authority = SQLiteWitnessAuthority(
            str(tmp_path / f"witness-{index}.sqlite"),
            witness_id=f"witness-{index}",
            signing_key=key,
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"witness-{index}",
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        ))
    return anchors, authorities


def test_quorum_anchor_requires_majority_and_advances_atomically(tmp_path):
    anchors, authorities = make_witnesses(tmp_path)
    quorum = QuorumMonotonicAnchor({f"witness-{i}": anchor for i, anchor in enumerate(anchors)})
    initial = AnchorSnapshot(0, ZERO_MAC)
    next_head = AnchorSnapshot(1, "a" * 64)
    assert quorum.read() == initial
    assert quorum.compare_and_swap(initial, next_head)
    assert quorum.read() == next_head
    assert not quorum.compare_and_swap(initial, AnchorSnapshot(2, "b" * 64))
    for authority in authorities:
        authority.close()


def test_quorum_anchor_fails_closed_without_majority(tmp_path):
    anchors, authorities = make_witnesses(tmp_path)

    class FailingClient:
        def read_anchor(self, nonce):
            raise OSError("offline")
        def compare_and_swap_anchor(self, expected, replacement, nonce):
            raise OSError("offline")

    failing_key = Ed25519PrivateKey.generate()
    unavailable = RemoteMonotonicAnchor(
        FailingClient(),
        witness_id="witness-offline",
        trusted_public_key=failing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
    )
    quorum = QuorumMonotonicAnchor({
        "witness-0": anchors[0],
        "witness-1": anchors[1],
        "witness-offline": unavailable,
    })
    assert quorum.read() == AnchorSnapshot(0, ZERO_MAC)

    broken = QuorumMonotonicAnchor({
        "witness-0": anchors[0],
        "witness-offline-1": RemoteMonotonicAnchor(
            FailingClient(), witness_id="witness-offline-1",
            trusted_public_key=failing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        ),
        "witness-offline-2": RemoteMonotonicAnchor(
            FailingClient(), witness_id="witness-offline-2",
            trusted_public_key=failing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        ),
    })
    with pytest.raises(RuntimeError, match="quorum_unavailable"):
        broken.read()
    for authority in authorities:
        authority.close()

def test_quorum_anchor_requires_odd_three_or_more_witnesses(tmp_path):
    anchors, authorities = make_witnesses(tmp_path)
    with pytest.raises(ValueError, match="odd_witness_count"):
        QuorumMonotonicAnchor({"witness-0": anchors[0], "witness-1": anchors[1]})
    for authority in authorities:
        authority.close()


def test_quorum_rejects_distinct_ids_reusing_same_public_key(tmp_path):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    anchors = []
    authorities = []
    for index in range(3):
        authority = SQLiteWitnessAuthority(
            str(tmp_path / f"shared-key-{index}.sqlite"),
            witness_id=f"shared-key-{index}",
            signing_key=key,
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"shared-key-{index}",
            trusted_public_key=public,
        ))
    with pytest.raises(ValueError, match="public_keys_must_be_distinct"):
        QuorumMonotonicAnchor({
            f"shared-key-{i}": anchor for i, anchor in enumerate(anchors)
        })
    for authority in authorities:
        authority.close()
