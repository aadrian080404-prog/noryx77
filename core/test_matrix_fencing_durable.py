from concurrent.futures import ThreadPoolExecutor

import pytest

from .matrix_fencing_durable import SQLiteFencedResource


def test_fencing_epoch_and_operations_survive_reopen(tmp_path):
    database = str(tmp_path / "fence.sqlite")
    first = SQLiteFencedResource(database)
    assert first.snapshot("account-A") == (0, 0)
    first.activate("account-A", 7)
    applied = first.apply("account-A", 7, "op-1", b"debit:10")

    reopened = SQLiteFencedResource(database)
    assert reopened.snapshot("account-A") == (7, 1)
    assert reopened.apply("account-A", 7, "op-1", b"debit:10") == applied
    with pytest.raises(PermissionError, match="fencing_token_not_monotonic"):
        reopened.activate("account-A", 7)


def test_stale_generation_cannot_write_after_restart(tmp_path):
    database = str(tmp_path / "fence.sqlite")
    SQLiteFencedResource(database).activate("resource", 10)
    SQLiteFencedResource(database).activate("resource", 11)
    reopened = SQLiteFencedResource(database)
    with pytest.raises(PermissionError, match="stale_or_unactivated_fencing_token"):
        reopened.apply("resource", 10, "stale-op", b"payload")
    assert reopened.apply("resource", 11, "current-op", b"payload").version == 1


def test_idempotency_is_resource_scoped_and_payload_bound(tmp_path):
    store = SQLiteFencedResource(str(tmp_path / "fence.sqlite"))
    store.activate("A", 1)
    store.activate("B", 1)
    original = store.apply("A", 1, "same-id", b"same")
    assert store.apply("A", 1, "same-id", b"same") == original
    assert store.apply("B", 1, "same-id", b"same").version == 1
    with pytest.raises(PermissionError, match="idempotency_key_payload_conflict"):
        store.apply("A", 1, "same-id", b"different")


def test_stale_generation_cannot_replay_an_old_idempotency_receipt(tmp_path):
    store = SQLiteFencedResource(str(tmp_path / "fence.sqlite"))
    store.activate("R", 1)
    result = store.apply("R", 1, "op", b"payload")
    store.activate("R", 2)
    with pytest.raises(PermissionError, match="stale_or_unactivated_fencing_token"):
        store.apply("R", 1, "op", b"payload")
    assert store.snapshot("R") == (2, 1)
    assert result.version == 1


def test_current_generation_can_retry_idempotently_without_replaying_side_effect(tmp_path):
    store = SQLiteFencedResource(str(tmp_path / "fence.sqlite"))
    store.activate("R", 1)
    result = store.apply("R", 1, "op", b"payload")
    assert store.apply("R", 1, "op", b"payload") == result
    assert store.snapshot("R") == (1, 1)


def test_concurrent_writes_are_serialized_and_versions_are_unique(tmp_path):
    store = SQLiteFencedResource(str(tmp_path / "fence.sqlite"), timeout=10)
    store.activate("R", 3)

    def apply(index):
        return SQLiteFencedResource(str(tmp_path / "fence.sqlite"), timeout=10).apply(
            "R", 3, f"op-{index}", str(index).encode()
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(apply, range(40)))
    assert sorted(result.version for result in results) == list(range(1, 41))
    assert store.snapshot("R") == (3, 40)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_timeout_must_be_finite_and_positive(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout_must_be_finite_and_positive"):
        SQLiteFencedResource(str(tmp_path / "bad.sqlite"), timeout=timeout)
