import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from core.journal_integrity import AnchorSnapshot, ZERO_MAC
from core.quorum_witness import QuorumMonotonicAnchor
from core.remote_witness import RemoteMonotonicAnchor, SignedWitnessReceipt
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
            failure_domain=f"failure-domain-{index}",
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
        failure_domain="failure-domain-offline",
    )
    quorum = QuorumMonotonicAnchor({
        "witness-0": anchors[0],
        "witness-1": anchors[1],
        "witness-offline": unavailable,
    })
    assert quorum.read() == AnchorSnapshot(0, ZERO_MAC)

    offline_key_1 = Ed25519PrivateKey.generate()
    offline_key_2 = Ed25519PrivateKey.generate()
    broken = QuorumMonotonicAnchor({
        "witness-0": anchors[0],
        "witness-offline-1": RemoteMonotonicAnchor(
            FailingClient(), witness_id="witness-offline-1",
            trusted_public_key=offline_key_1.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain="failure-domain-offline-1",
        ),
        "witness-offline-2": RemoteMonotonicAnchor(
            FailingClient(), witness_id="witness-offline-2",
            trusted_public_key=offline_key_2.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain="failure-domain-offline-2",
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


def test_quorum_rejects_different_ids_with_same_public_key(tmp_path):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    anchors = []
    authorities = []
    for index in range(3):
        authority = SQLiteWitnessAuthority(
            str(tmp_path / f"duplicate-key-{index}.sqlite"),
            witness_id=f"duplicate-key-{index}",
            signing_key=key,
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"duplicate-key-{index}",
            trusted_public_key=public,
            failure_domain=f"duplicate-domain-{index}",
        ))
    with pytest.raises(ValueError, match="public_keys_must_be_distinct"):
        QuorumMonotonicAnchor({f"duplicate-key-{i}": a for i, a in enumerate(anchors)})
    for authority in authorities:
        authority.close()



def test_quorum_rejects_missing_failure_domains(tmp_path):
    class UnusedClient:
        def read_anchor(self, nonce):
            raise OSError("not used")
        def compare_and_swap_anchor(self, expected, replacement, nonce):
            raise OSError("not used")

    witnesses = {}
    for index in range(3):
        key = Ed25519PrivateKey.generate()
        witness_id = f"missing-domain-{index}"
        witnesses[witness_id] = RemoteMonotonicAnchor(
            UnusedClient(),
            witness_id=witness_id,
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        )
    with pytest.raises(ValueError, match="failure_domain_required"):
        QuorumMonotonicAnchor(witnesses)


def test_quorum_rejects_shared_failure_domain_even_with_distinct_keys(tmp_path):
    anchors, authorities = make_witnesses(tmp_path)
    # Re-wrap the second witness with the same declared domain as the first.
    second_key = Ed25519PrivateKey.generate()
    second_authority = SQLiteWitnessAuthority(
        str(tmp_path / "shared-domain.sqlite"),
        witness_id="shared-domain",
        signing_key=second_key,
    )
    second = RemoteMonotonicAnchor(
        InProcessWitnessClient(second_authority),
        witness_id="shared-domain",
        trusted_public_key=second_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
        failure_domain="failure-domain-0",
    )
    with pytest.raises(ValueError, match="failure_domains_must_be_distinct"):
        QuorumMonotonicAnchor({
            "witness-0": anchors[0],
            "shared-domain": second,
            "witness-2": anchors[2],
        })
    second_authority.close()
    for authority in authorities:
        authority.close()



def test_quorum_normalizes_failure_domain_whitespace_before_uniqueness(tmp_path):
    class UnusedClient:
        def read_anchor(self, nonce):
            raise OSError("not used")
        def compare_and_swap_anchor(self, expected, replacement, nonce):
            raise OSError("not used")

    witnesses = {}
    for index, domain in enumerate(("production-zone", " production-zone ", "backup-zone")):
        key = Ed25519PrivateKey.generate()
        witness_id = f"normalized-domain-{index}"
        witnesses[witness_id] = RemoteMonotonicAnchor(
            UnusedClient(),
            witness_id=witness_id,
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain=domain,
        )
    with pytest.raises(ValueError, match="failure_domains_must_be_distinct"):
        QuorumMonotonicAnchor(witnesses)


def test_concurrent_conflicting_quorum_writers_cannot_both_commit(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    anchors, authorities = make_witnesses(tmp_path)
    quorum = QuorumMonotonicAnchor({
        f"witness-{index}": anchor for index, anchor in enumerate(anchors)
    })
    initial = AnchorSnapshot(0, ZERO_MAC)
    replacements = (
        AnchorSnapshot(1, "a" * 64),
        AnchorSnapshot(1, "b" * 64),
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda replacement: quorum.compare_and_swap(initial, replacement),
                replacements,
            ))
        assert sum(results) == 1
        assert quorum.read() in replacements
    finally:
        for authority in authorities:
            authority.close()

def test_remote_witness_rejects_noncanonical_32_byte_anchor_mac():
    key = Ed25519PrivateKey.generate()

    class MalformedMacClient:
        def read_anchor(self, nonce):
            unsigned = SignedWitnessReceipt(
                "malformed-mac", "read", nonce,
                AnchorSnapshot(0, "aa" * 31 + "  "), True, b"",
            )
            return SignedWitnessReceipt(
                unsigned.witness_id, unsigned.operation, unsigned.nonce,
                unsigned.snapshot, unsigned.accepted,
                key.sign(RemoteMonotonicAnchor._message(unsigned)),
            )

        def compare_and_swap_anchor(self, expected, replacement, nonce):
            raise AssertionError("unexpected_compare_and_swap")

    public_key = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    anchor = RemoteMonotonicAnchor(
        MalformedMacClient(),
        witness_id="malformed-mac",
        trusted_public_key=public_key,
    )
    with pytest.raises(RuntimeError, match="remote_witness_snapshot_invalid"):
        anchor.read()

def test_independent_quorum_coordinators_cannot_both_commit_conflicting_updates(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    anchors, authorities = make_witnesses(tmp_path)
    first = QuorumMonotonicAnchor({
        f"witness-{index}": anchor for index, anchor in enumerate(anchors)
    })
    second = QuorumMonotonicAnchor({
        f"witness-{index}": anchor for index, anchor in enumerate(anchors)
    })
    initial = AnchorSnapshot(0, ZERO_MAC)
    replacements = (
        AnchorSnapshot(1, "c" * 64),
        AnchorSnapshot(1, "d" * 64),
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda item: item[0].compare_and_swap(initial, item[1]),
                ((first, replacements[0]), (second, replacements[1])),
            ))
        assert sum(results) <= 1
        try:
            observed = first.read()
        except RuntimeError as exc:
            assert str(exc) == "witness_quorum_unavailable_or_divergent"
        else:
            assert observed in replacements or observed == initial
    finally:
        for authority in authorities:
            authority.close()



def _multiprocess_quorum_writer(database_paths, private_keys, ready, start, results, replacement_mac):
    """Independent OS process with its own witness connections and coordinator."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from core.journal_integrity import AnchorSnapshot, ZERO_MAC
    from core.quorum_witness import QuorumMonotonicAnchor
    from core.remote_witness import RemoteMonotonicAnchor
    from core.witness_authority import InProcessWitnessClient, SQLiteWitnessAuthority

    authorities = []
    try:
        anchors = []
        for index, (database_path, raw_key) in enumerate(zip(database_paths, private_keys)):
            key = Ed25519PrivateKey.from_private_bytes(raw_key)
            authority = SQLiteWitnessAuthority(
                database_path, witness_id=f"witness-{index}", signing_key=key
            )
            authorities.append(authority)
            anchors.append(RemoteMonotonicAnchor(
                InProcessWitnessClient(authority),
                witness_id=f"witness-{index}",
                trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
                failure_domain=f"failure-domain-{index}",
            ))
        coordinator = QuorumMonotonicAnchor({
            f"witness-{index}": anchor for index, anchor in enumerate(anchors)
        })
        ready.put(True)
        if not start.wait(15):
            results.put(("timeout", False))
            return
        accepted = coordinator.compare_and_swap(
            AnchorSnapshot(0, ZERO_MAC), AnchorSnapshot(1, replacement_mac)
        )
        results.put(("result", accepted))
    except Exception as exc:
        results.put(("error", type(exc).__name__ + ":" + str(exc)))
    finally:
        for authority in authorities:
            authority.close()


def test_independent_process_quorum_coordinators_cannot_both_commit(tmp_path):
    """Exercise witness CAS with two OS processes, not only two Python threads."""
    import multiprocessing
    from cryptography.hazmat.primitives.serialization import PrivateFormat, NoEncryption

    context = multiprocessing.get_context("spawn")
    database_paths = [str(tmp_path / f"process-witness-{index}.sqlite") for index in range(3)]
    private_keys = []
    initial_authorities = []
    for index, database_path in enumerate(database_paths):
        key = Ed25519PrivateKey.generate()
        private_keys.append(key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        ))
        initial_authorities.append(SQLiteWitnessAuthority(
            database_path, witness_id=f"witness-{index}", signing_key=key
        ))
    for authority in initial_authorities:
        authority.close()

    ready = context.Queue()
    start = context.Event()
    results = context.Queue()
    replacements = ("e" * 64, "f" * 64)
    workers = [
        context.Process(
            target=_multiprocess_quorum_writer,
            args=(database_paths, private_keys, ready, start, results, replacement),
        )
        for replacement in replacements
    ]
    for worker in workers:
        worker.start()
    try:
        assert ready.get(timeout=20) is True
        assert ready.get(timeout=20) is True
        start.set()
        for worker in workers:
            worker.join(timeout=25)
        assert all(not worker.is_alive() for worker in workers), "quorum_process_timeout"
        assert [worker.exitcode for worker in workers] == [0, 0]
        outcomes = [results.get(timeout=5) for _ in workers]
        assert all(kind == "result" for kind, _ in outcomes), outcomes
        assert sum(bool(value) for _, value in outcomes) <= 1
    finally:
        start.set()
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        ready.close()
        results.close()

    final_authorities = []
    final_anchors = []
    for index, database_path in enumerate(database_paths):
        key = Ed25519PrivateKey.from_private_bytes(private_keys[index])
        authority = SQLiteWitnessAuthority(
            database_path, witness_id=f"witness-{index}", signing_key=key
        )
        final_authorities.append(authority)
        final_anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"witness-{index}",
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain=f"failure-domain-{index}",
        ))
    try:
        final = QuorumMonotonicAnchor({
            f"witness-{index}": anchor for index, anchor in enumerate(final_anchors)
        })
        try:
            observed = final.read()
        except RuntimeError as exc:
            assert str(exc) == "witness_quorum_unavailable_or_divergent"
        else:
            assert observed in (
                AnchorSnapshot(0, ZERO_MAC),
                AnchorSnapshot(1, replacements[0]),
                AnchorSnapshot(1, replacements[1]),
            )
    finally:
        for authority in final_authorities:
            authority.close()


def test_quorum_fails_closed_when_independent_writers_leave_no_majority(tmp_path):
    anchors = []
    authorities = []
    for index in range(5):
        key = Ed25519PrivateKey.generate()
        authority = SQLiteWitnessAuthority(
            str(tmp_path / f"split-witness-{index}.sqlite"),
            witness_id=f"split-witness-{index}",
            signing_key=key,
        )
        authorities.append(authority)
        anchors.append(RemoteMonotonicAnchor(
            InProcessWitnessClient(authority),
            witness_id=f"split-witness-{index}",
            trusted_public_key=key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
            failure_domain=f"split-domain-{index}",
        ))
    quorum = QuorumMonotonicAnchor({
        f"split-witness-{index}": anchor
        for index, anchor in enumerate(anchors)
    })
    initial = AnchorSnapshot(0, ZERO_MAC)
    update_a = AnchorSnapshot(1, "a" * 64)
    update_b = AnchorSnapshot(1, "b" * 64)
    try:
        # Model a cross-coordinator interleaving: two witnesses accepted A,
        # two accepted B, and one remains at the old value. No value has 3/5.
        assert all(anchor.compare_and_swap(initial, update_a) for anchor in anchors[:2])
        assert all(anchor.compare_and_swap(initial, update_b) for anchor in anchors[2:4])
        with pytest.raises(RuntimeError, match="quorum_unavailable_or_divergent"):
            quorum.read()
        assert not quorum.compare_and_swap(initial, AnchorSnapshot(1, "c" * 64))
    finally:
        for authority in authorities:
            authority.close()
