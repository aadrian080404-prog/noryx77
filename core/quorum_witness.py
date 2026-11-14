"""Majority-backed monotonic anchor over independent signed witnesses."""
from __future__ import annotations

from collections import Counter
from typing import Mapping

from .journal_integrity import AnchorSnapshot, MonotonicAnchor, ZERO_MAC
from .remote_witness import RemoteMonotonicAnchor


class QuorumMonotonicAnchor:
    """Fail-closed majority anchor over an odd set of independent witnesses.

    Each child must independently verify nonce-bound Ed25519 receipts. An odd
    witness count ensures that a partial write smaller than a majority leaves
    a strict majority at the previous value. A split or unavailable quorum
    causes failure rather than guessing which history is authoritative.
    """

    def __init__(self, witnesses: Mapping[str, RemoteMonotonicAnchor]) -> None:
        if not isinstance(witnesses, Mapping):
            raise TypeError("witness_mapping_required")
        selected = dict(witnesses)
        if len(selected) < 3 or len(selected) % 2 == 0:
            raise ValueError("odd_witness_count_at_least_three_required")
        fingerprints: set[str] = set()
        failure_domains: set[str] = set()
        for witness_id, witness in selected.items():
            if not isinstance(witness_id, str) or not witness_id.strip():
                raise ValueError("witness_id_required")
            if not isinstance(witness, RemoteMonotonicAnchor):
                raise TypeError("remote_monotonic_anchor_required")
            if witness.witness_id != witness_id:
                raise ValueError("witness_mapping_identity_mismatch")
            fingerprint = witness.public_key_fingerprint
            if fingerprint in fingerprints:
                raise ValueError("witness_public_keys_must_be_distinct")
            fingerprints.add(fingerprint)
            domain = witness.failure_domain
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError("witness_failure_domain_required")
            if domain in failure_domains:
                raise ValueError("witness_failure_domains_must_be_distinct")
            failure_domains.add(domain)
        self._witnesses = dict(sorted(selected.items()))
        self.quorum = len(self._witnesses) // 2 + 1

    def read(self) -> AnchorSnapshot:
        observed: list[AnchorSnapshot] = []
        for witness in self._witnesses.values():
            try:
                snapshot = witness.read()
            except Exception:
                continue
            if isinstance(snapshot, AnchorSnapshot):
                observed.append(snapshot)
        counts = Counter(observed)
        winners = [snapshot for snapshot, count in counts.items() if count >= self.quorum]
        if len(winners) != 1:
            raise RuntimeError("witness_quorum_unavailable_or_divergent")
        return winners[0]

    def compare_and_swap(
        self, expected: AnchorSnapshot, replacement: AnchorSnapshot
    ) -> bool:
        if not isinstance(expected, AnchorSnapshot) or not isinstance(replacement, AnchorSnapshot):
            return False
        if replacement.sequence != expected.sequence + 1:
            return False
        try:
            current = self.read()
        except Exception:
            return False
        if current != expected:
            return False

        accepted = 0
        for witness in self._witnesses.values():
            try:
                if witness.compare_and_swap(expected, replacement):
                    accepted += 1
                    continue
                # A concurrent identical writer may have committed the same
                # transition before this witness processed our CAS.
                if witness.read() == replacement:
                    accepted += 1
            except Exception:
                continue
        return accepted >= self.quorum
