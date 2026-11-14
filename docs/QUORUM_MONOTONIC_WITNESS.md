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
