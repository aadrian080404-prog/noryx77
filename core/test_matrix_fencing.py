import pytest

from .matrix_fencing import FencedResource


def test_resource_requires_epoch_activation_before_writes():
    resource = FencedResource()
    with pytest.raises(PermissionError):
        resource.apply(1, "op-1", b"payload")
    resource.activate(1)
    assert resource.apply(1, "op-1", b"payload").version == 1


def test_resource_rejects_stale_holder_after_new_epoch_activation():
    resource = FencedResource()
    resource.activate(10)
    resource.apply(10, "first", b"a")
    resource.activate(11)
    with pytest.raises(PermissionError, match="stale_or_unactivated_fencing_token"):
        resource.apply(10, "stale", b"b")
    assert resource.apply(11, "new", b"c").version == 2


def test_fencing_epochs_are_strictly_monotonic():
    resource = FencedResource()
    resource.activate(5)
    with pytest.raises(PermissionError):
        resource.activate(5)
    with pytest.raises(PermissionError):
        resource.activate(4)


def test_idempotent_retry_returns_original_result_and_conflicts_are_denied():
    resource = FencedResource()
    resource.activate(2)
    first = resource.apply(2, "transfer-1", b"amount=10")
    retry = resource.apply(2, "transfer-1", b"amount=10")
    assert retry == first
    assert resource.version == 1
    with pytest.raises(PermissionError, match="idempotency_key_payload_conflict"):
        resource.apply(2, "transfer-1", b"amount=100")


def test_old_idempotent_retry_does_not_repeat_side_effect_after_new_epoch():
    resource = FencedResource()
    resource.activate(1)
    first = resource.apply(1, "job-1", b"work")
    resource.activate(2)
    assert resource.apply(1, "job-1", b"work") == first
    with pytest.raises(PermissionError):
        resource.apply(1, "job-2", b"new work")
