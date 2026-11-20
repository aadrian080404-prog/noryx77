from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import hashlib

from core.sqlite_federated_audit import SQLiteExternalAuditAnchor


def test_independent_anchor_clients_allow_only_one_same_version_cas_winner(tmp_path):
    witness_path = tmp_path / "shared-independent-anchor.sqlite3"
    first = SQLiteExternalAuditAnchor(witness_path)
    second = SQLiteExternalAuditAnchor(witness_path)
    genesis = hashlib.sha256(
        b"noryx7/sqlite-federated-audit/genesis/v1"
    ).hexdigest()
    candidates = ("a" * 64, "b" * 64)
    barrier = Barrier(2)

    def advance(anchor, candidate):
        barrier.wait(timeout=5)
        return anchor.compare_and_advance(0, genesis, 1, candidate)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda item: advance(item[0], item[1]),
            ((first, candidates[0]), (second, candidates[1])),
        ))

    assert sorted(outcomes) == [False, True]
    checkpoint = first.read_checkpoint()
    assert checkpoint[0] == 1
    assert checkpoint[1] in candidates
    assert second.read_checkpoint() == checkpoint
