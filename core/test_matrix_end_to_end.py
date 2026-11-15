"""Cross-component integration test for the local Matrix trust and execution path.

The test composes durable admission/grants/reservations, supervisor dispatch,
resource-side fencing, authenticated inbox handoff and recoverable transfer.
All adapters are local deterministic test doubles; this is not a distributed
deployment or production actuator/payment integration.
"""
import pytest

from .matrix_budget import DeviceConditions, DeviceContributionPolicy
from .matrix_core import (
    ContributionGrant, NodeProfile, ResourceEnvelope, ResourceVector, WorkloadRequest,
)
from .matrix_fencing_durable import SQLiteFencedResource
from .matrix_grants import DurableGrantRegistry
from .matrix_inbox import DurableInbox, sign_message
from .matrix_key_policy import DurableKeyPolicyRegistry
from .matrix_membership_durable import AdmissionEvidence, DurableMembershipRegistry
from .matrix_reservations import DurableReservationBook
from .matrix_supervisor import MatrixSupervisor
from .matrix_transfer import DurableTransferCoordinator, TransferRequest


class FencedExecutor:
    """Test target that atomically fences its resource before accepting writes."""

    def __init__(self, fence):
        self.fence = fence
        self.started = []
        self.stopped = []

    def start(self, request, generation):
        self.fence.activate(request.task_id, generation)
        self.fence.apply(request.task_id, generation, "start", b"workload-start")
        self.started.append((request.task_id, generation))

    def stop(self, task_id, generation):
        # The test adapter receives the authoritative next generation from the
        # grant-revocation contract (old generation + one) and fences the target.
        self.fence.activate(task_id, generation + 1)
        self.stopped.append((task_id, generation))


class Participant:
    def __init__(self, participant_id):
        self.participant_id = participant_id
        self.prepared = set()
        self.committed = set()

    def prepare(self, transfer_id, asset_id, amount_minor, request_digest):
        self.prepared.add((transfer_id, request_digest, asset_id, amount_minor))

    def commit(self, transfer_id, request_digest):
        assert any(item[0] == transfer_id and item[1] == request_digest for item in self.prepared)
        self.committed.add((transfer_id, request_digest))

    def abort(self, transfer_id, request_digest):
        self.prepared.discard((transfer_id, request_digest, "", 0))


def test_end_to_end_local_admission_message_transfer_and_revocation(tmp_path):
    grant = ContributionGrant(
        "grant-node", True, 1, ResourceVector(1500, 2_000_000),
        frozenset({"compute"}), False,
    )
    node = NodeProfile(
        "node-1", "rack-a", True, True,
        ResourceEnvelope(
            ResourceVector(4000, 4_000_000), ResourceVector(),
            ResourceVector(500, 500_000),
        ),
        grant,
    )

    membership = DurableMembershipRegistry(tmp_path / "membership.db")
    evidence = AdmissionEvidence(
        "node-1", "owner-1", "rack-a", "sha256:measurement", 1,
        "nonce-1", frozenset({"compute"}),
    )
    membership.admit(evidence, b"proof", lambda _e, proof: proof == b"proof")

    grants = DurableGrantRegistry(tmp_path / "grants.db")
    grants.put("node-1", "owner-1", grant)
    reservations = DurableReservationBook(tmp_path / "reservations.db", node)
    fence = SQLiteFencedResource(str(tmp_path / "resource-fence.db"))
    executor = FencedExecutor(fence)
    policy = DeviceContributionPolicy(True, 30, 42, 4, 1000, 10, ((0, 1000),))
    supervisor = MatrixSupervisor(
        node, "owner-1", membership, grants, reservations, policy, executor,
    )

    request = WorkloadRequest(
        "task-1", "compute", ResourceVector(500, 500_000), generation=1,
    )
    receipt = supervisor.dispatch(
        request, DeviceConditions(90, 35, 2, 100, 100),
        telemetry_captured_at=100, now=100, max_telemetry_age=2,
        estimated_duration_hours=0.25,
    )
    assert receipt.grant_generation == 1
    assert executor.started == [("task-1", 1)]
    assert fence.snapshot("task-1") == (1, 1)

    # Authenticated network handoff: accept, read, acknowledge, then replay.
    network_key = b"N" * 32
    key_policy = DurableKeyPolicyRegistry(
        str(tmp_path / "key-policy.db"),
        authorize=lambda action, owner, purpose, key_id, generation: (
            owner == "owner-1" and purpose == "NETWORK_HMAC"
        ),
        key_resolver=lambda key_id: network_key if key_id == "network-key-1" else b"",
    )
    key_policy.register("network-key-1", "owner-1", "NETWORK_HMAC", 1)
    inbox = DurableInbox(
        str(tmp_path / "inbox.db"), "node-1", {},
        trusted_senders={"network-key-1": "coordinator-1"},
        trusted_key_resolver=lambda key_id, sender_id: key_policy.resolve(
            key_id, "owner-1", "NETWORK_HMAC"
        ) if sender_id == "coordinator-1" else (_ for _ in ()).throw(
            PermissionError("message_sender_key_binding_mismatch")
        ),
    )
    payload = b'{"task_id":"task-1","action":"prepare-transfer"}'
    signature = sign_message(
        "coordinator-1", "node-1", "message-1", "network-key-1",
        500, payload, network_key,
    )
    accepted = inbox.accept(
        "coordinator-1", "node-1", "message-1", "network-key-1",
        500, payload, signature, now=100,
    )
    assert accepted.state == "PENDING"
    pending = inbox.read_pending("message-1", now=101)
    assert pending is not None and pending[1] == payload
    inbox.mark_delivered("message-1", now=102)
    replay = inbox.accept(
        "coordinator-1", "node-1", "message-1", "network-key-1",
        500, payload, signature, now=103,
    )
    assert replay.state == "DELIVERED"

    # A second message accepted under the same key becomes unreadable after
    # durable key revocation; inbox revalidates policy at payload release.
    revoked_payload = b'{"task_id":"task-1","action":"sensitive-follow-up"}'
    revoked_signature = sign_message(
        "coordinator-1", "node-1", "message-2", "network-key-1",
        500, revoked_payload, network_key,
    )
    inbox.accept(
        "coordinator-1", "node-1", "message-2", "network-key-1",
        500, revoked_payload, revoked_signature, now=104,
    )
    key_policy.revoke("network-key-1", "owner-1", generation=2)
    with pytest.raises(PermissionError, match="key_revoked"):
        inbox.read_pending("message-2", now=105)

    # Financial protocol journal reaches COMMITTED only after both participants.
    source, destination = Participant("wallet-A"), Participant("wallet-B")
    transfers = DurableTransferCoordinator(tmp_path / "transfers.db")
    transfer = transfers.execute(
        TransferRequest("transfer-1", "wallet-A", "wallet-B", "EUR", 1250),
        source, destination,
    )
    assert transfer.state == "COMMITTED"
    assert transfer.source_committed and transfer.destination_committed

    # Owner revocation clears local reservation and asks target to fence old work.
    revoked = supervisor.revoke(expected_generation=1)
    assert revoked.grant_generation == 2
    assert revoked.cancelled_task_ids == ("task-1",)
    assert revoked.stop_failures == ()
    assert reservations.list() == ()
    assert executor.stopped == [("task-1", 1)]
    assert fence.snapshot("task-1") == (2, 1)
    with pytest.raises(PermissionError, match="stale_or_unactivated_fencing_token"):
        fence.apply("task-1", 1, "late-write", b"must-not-apply")
    with pytest.raises(PermissionError):
        supervisor.dispatch(
            WorkloadRequest("task-2", "compute", ResourceVector(100, 100_000), 2),
            DeviceConditions(90, 35, 2, 100, 100),
            telemetry_captured_at=104, now=104, max_telemetry_age=2,
            estimated_duration_hours=0.1,
        )
