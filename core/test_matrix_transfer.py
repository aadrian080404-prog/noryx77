import pytest

from .matrix_transfer import DurableTransferCoordinator, TransferRequest


class FakeParticipant:
    def __init__(self, participant_id, fail_commit=False):
        self.participant_id = participant_id
        self.fail_commit = fail_commit
        self.prepared = {}
        self.committed = set()
        self.aborted = set()

    def prepare(self, transfer_id, asset_id, amount_minor, request_digest):
        previous = self.prepared.get(transfer_id)
        record = (asset_id, amount_minor, request_digest)
        if previous is not None and previous != record:
            raise PermissionError("participant_prepare_conflict")
        self.prepared[transfer_id] = record

    def commit(self, transfer_id, request_digest):
        if self.fail_commit:
            raise RuntimeError("participant_commit_unavailable")
        if transfer_id not in self.prepared or self.prepared[transfer_id][2] != request_digest:
            raise PermissionError("participant_not_prepared")
        self.committed.add(transfer_id)

    def abort(self, transfer_id, request_digest):
        if transfer_id in self.committed:
            raise PermissionError("cannot_abort_committed_transfer")
        self.aborted.add(transfer_id)


def _request():
    return TransferRequest("tx-1", "wallet-a", "wallet-b", "EUR-cent", 1250)


def _participants(fail_destination=False):
    return FakeParticipant("wallet-a"), FakeParticipant("wallet-b", fail_commit=fail_destination)


def test_two_participant_transfer_commits_only_after_both_confirm(tmp_path):
    coordinator = DurableTransferCoordinator(tmp_path / "transfer.db")
    source, destination = _participants()
    status = coordinator.execute(_request(), source, destination)
    assert status.state == "COMMITTED"
    assert status.source_prepared and status.destination_prepared
    assert status.source_committed and status.destination_committed


def test_transfer_retries_are_idempotent_and_conflicts_rejected(tmp_path):
    coordinator = DurableTransferCoordinator(tmp_path / "transfer.db")
    source, destination = _participants()
    first = coordinator.execute(_request(), source, destination)
    replay = coordinator.execute(_request(), source, destination)
    assert first == replay
    conflicting = TransferRequest("tx-1", "wallet-a", "wallet-b", "EUR-cent", 1251)
    with pytest.raises(PermissionError, match="transfer_idempotency_conflict"):
        coordinator.execute(conflicting, source, destination)


def test_partial_commit_enters_in_doubt_and_resume_finishes_without_redebit(tmp_path):
    coordinator = DurableTransferCoordinator(tmp_path / "transfer.db")
    source, destination = _participants(fail_destination=True)
    with pytest.raises(RuntimeError, match="participant_commit_unavailable"):
        coordinator.execute(_request(), source, destination)
    status = coordinator.status("tx-1")
    assert status.state == "IN_DOUBT"
    assert status.source_committed
    assert not status.destination_committed
    destination.fail_commit = False
    recovered = coordinator.resume("tx-1", source, destination)
    assert recovered.state == "COMMITTED"
    assert source.committed == {"tx-1"}
    assert destination.committed == {"tx-1"}


def test_resume_rejects_wrong_participant_binding(tmp_path):
    coordinator = DurableTransferCoordinator(tmp_path / "transfer.db")
    source, destination = _participants()
    with pytest.raises(PermissionError, match="transfer_participant_binding_mismatch"):
        coordinator.resume("missing", source, destination)
