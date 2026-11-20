from concurrent.futures import ThreadPoolExecutor
import hashlib

from core.sqlite_federated_audit import SQLiteExternalAuditAnchor


def test_external_anchor_compare_and_advance_is_single_winner_across_clients(tmp_path):
    path = tmp_path / "shared-witness.sqlite"
    first = SQLiteExternalAuditAnchor(path)
    second = SQLiteExternalAuditAnchor(path)
    genesis = hashlib.sha256(
        b"noryx7/sqlite-federated-audit/genesis/v1"
    ).hexdigest()
    next_digest = hashlib.sha256(b"next-checkpoint").hexdigest()

    def advance(anchor):
        return anchor.compare_and_advance(0, genesis, 1, next_digest)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(advance, (first, second)))

    assert sorted(outcomes) == [False, True]
    assert first.read_checkpoint() == (1, next_digest)
    assert second.read_checkpoint() == (1, next_digest)
