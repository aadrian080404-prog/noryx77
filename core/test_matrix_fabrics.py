import pytest

from .matrix_membership import AdmissionEvidence, MemberState, MembershipRegistry
from .matrix_scheduler import propose_placement
from .matrix_data import ObjectManifest
from .matrix_twin import DeterministicTwin
from .matrix_core import (
    ContributionGrant, LocalReservationBook, NodeProfile, ResourceEnvelope, ResourceVector, WorkloadRequest
)


def node(node_id, domain, cpu_used=0):
    grant = ContributionGrant(
        "g-" + node_id, True, 1, ResourceVector(cpu_milli=3000),
        frozenset({"verification"}), False,
    )
    return NodeProfile(
        node_id, domain, True, True,
        ResourceEnvelope(
            ResourceVector(cpu_milli=4000),
            ResourceVector(cpu_milli=cpu_used),
            ResourceVector(cpu_milli=500),
        ),
        grant,
    )


def request(task="t"):
    return WorkloadRequest(task, "verification", ResourceVector(cpu_milli=500), 1)


def test_membership_requires_external_attestation_and_replay_safe_nonce():
    registry = MembershipRegistry()
    ev = AdmissionEvidence("n1", "owner", "rack-a", "sha256:abc", 1, "nonce-1",
                           frozenset({"compute"}))
    with pytest.raises(PermissionError):
        registry.admit(ev, b"proof", lambda _e, _p: False)
    assert registry.get("n1") is None
    assert registry.admit(ev, b"proof", lambda _e, _p: True).state is MemberState.ACTIVE
    with pytest.raises(PermissionError, match="admission_nonce_replayed"):
        registry.admit(ev, b"proof", lambda _e, _p: True)


def test_membership_epoch_and_revocation_are_monotonic():
    registry = MembershipRegistry()
    ev = AdmissionEvidence("n1", "owner", "rack-a", "m", 2, "nonce-a", frozenset())
    registry.admit(ev, b"x", lambda *_: True)
    with pytest.raises(ValueError):
        registry.revoke("n1", 2)
    revoked = registry.revoke("n1", 3)
    assert revoked.state is MemberState.REVOKED
    assert revoked.capabilities == frozenset()


def test_scheduler_is_deterministic_and_returns_proposal_not_reservation():
    a, b = node("a", "rack-a", 1000), node("b", "rack-b", 0)
    proposal = propose_placement([a, b], request())
    assert proposal.node_id == "b"
    assert proposal == propose_placement([b, a], request())
    assert b.envelope.committed.cpu_milli == 0


def test_scheduler_rejects_nodes_outside_user_grant():
    denied = node("a", "rack-a")
    grant = ContributionGrant("g-a", False, 1, ResourceVector(cpu_milli=3000),
                              frozenset({"verification"}), False)
    denied = NodeProfile(denied.node_id, denied.failure_domain, True, True,
                         denied.envelope, grant)
    assert propose_placement([denied], request()) is None


def test_content_manifest_detects_corruption_and_chunk_reordering():
    chunks = (b"alpha", b"beta")
    manifest = ObjectManifest.from_chunks(chunks)
    assert manifest.verify_chunks(chunks)
    assert not manifest.verify_chunks((b"alpha", b"evil"))
    assert not manifest.verify_chunks((b"beta", b"alpha"))


def test_twin_orders_same_time_events_stably_and_replays_trace():
    twin = DeterministicTwin()
    seen = []
    def handler(event, sim):
        seen.append((sim.now, event.kind, event.payload))
    twin.schedule(5, "node_down", "n1")
    twin.schedule(5, "packet_drop", "link-a")
    twin.schedule(7, "node_up", "n1")
    events = twin.run({k: handler for k in ("node_down", "packet_drop", "node_up")})
    assert [e.kind for e in events] == ["node_down", "packet_drop", "node_up"]
    assert seen[0] == (5, "node_down", "n1")
    assert twin.now == 7 and twin.pending == 0


def test_twin_enforces_event_budget_and_rejects_time_travel():
    twin = DeterministicTwin()
    twin.schedule(1, "tick")
    twin.schedule(2, "tick")
    assert len(twin.run({"tick": lambda *_: None}, max_events=1)) == 1
    assert twin.pending == 1
    with pytest.raises(ValueError):
        twin.schedule(0, "past")


def test_membership_rejects_reused_nonce_even_with_newer_epoch():
    registry = MembershipRegistry()
    first = AdmissionEvidence("n1", "owner", "rack-a", "m", 1, "same", frozenset())
    registry.admit(first, b"proof", lambda *_: True)
    replay = AdmissionEvidence("n1", "owner", "rack-a", "m", 2, "same", frozenset())
    with pytest.raises(PermissionError, match="admission_nonce_replayed"):
        registry.admit(replay, b"proof", lambda *_: True)


def test_local_reservations_are_atomic_under_concurrent_calls():
    from concurrent.futures import ThreadPoolExecutor

    book = LocalReservationBook(node("shared", "rack-x"))
    def attempt(i):
        try:
            book.reserve(WorkloadRequest(
                f"parallel-{i}", "verification", ResourceVector(cpu_milli=500), 1
            ))
            return True
        except PermissionError:
            return False

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(attempt, range(20)))
    assert sum(results) == 6
    assert book.node.envelope.committed.cpu_milli == 3000
