# Quorum monotonic witness

`QuorumMonotonicAnchor` combines independently configured
`RemoteMonotonicAnchor` clients using a strict majority. It requires an odd
number of at least three witnesses, validates the mapping between configured
IDs and authenticated witness IDs, and only returns a snapshot observed by a
majority.

Updates first require a majority read matching the expected snapshot. The
component then sends compare-and-swap to each witness and counts either a
positive CAS receipt or an authenticated readback of the exact replacement.
A transition succeeds only after a majority confirms it. If fewer than a
majority confirm, the method returns false and callers must not treat the
journal update as externally anchored.

A partial write smaller than a majority leaves a strict majority at the old
head for odd cluster sizes. A partial write that advances a majority is
discoverable as the new head on the next read, even if the caller lost the
response. Divergent or unavailable majorities fail closed.

This component does not make witnesses independent by itself. Production
must use separate trust domains, hosts, credentials, administrators and
rollback-resistant storage. Three processes on one host or three SQLite
files on one disk are not three independent witnesses. It also does not
replace TLS, certificate pinning, key rotation, monitoring, or disaster
recovery procedures.

## Declared failure domains

Every witness admitted to a quorum must now declare a non-empty
`failure_domain`. The quorum rejects duplicate domain labels in addition to
duplicate public keys. This prevents accidental configurations that count
multiple witness identities from the same declared administrative or
infrastructure domain as separate quorum members.

The label is an operator assertion, not remote proof of independence. It
cannot establish separate ownership, cloud accounts, power/network paths,
administrators, hardware roots, or anti-rollback guarantees. Deployment
reviews must verify those properties out of band; distinct labels alone do
not make a quorum Byzantine-fault tolerant.

## Concurrent coordinator limitation

Each `QuorumMonotonicAnchor` serializes compare-and-swap calls made through that
same object. This is only an in-process coordinator lock; it is not a
cross-process lease, leader election protocol, or consensus algorithm. The
witness-level compare-and-swap intersection prevents two conflicting values
from both obtaining a majority, but concurrent independent coordinators can
still split updates so that no value has a majority (particularly with larger
odd clusters). Reads then fail closed until operators reconcile the witness
set. Production deployments that require continued availability under
concurrent writers need a shared consensus/lease protocol or a single fenced
writer, not merely this quorum wrapper.


The coordinator validates every witness snapshot before counting it toward a
majority: sequence values must be non-negative integers (not booleans), and
MACs must be canonical lowercase 32-byte hexadecimal strings. Malformed
snapshots do not contribute to quorum, including read-backs after a competing
compare-and-swap. This is defense in depth at the quorum boundary; each remote
witness must still authenticate its own signed receipt.
