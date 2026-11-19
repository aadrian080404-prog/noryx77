# Durable Authorization Replay Guard v1

The SQLite replay guard implements the same single-use token contract as the
in-memory guard. It stores only 32-byte authorization digests, never the
underlying authorization payload or secret.

Consumption is an atomic SQLite write transaction. A primary-key constraint
ensures two independent connections sharing the same database cannot consume
the same token successfully. The token set survives process restart.

The guard is bounded. When its configured capacity is reached, new tokens are
rejected. Tokens are not automatically expired or deleted: safe reclamation
requires an independently trusted monotonic epoch or external witness and is
not implemented here.

This protects one shared SQLite database. It is not distributed consensus
across independent databases or hosts. The TrustChain adapter can use either
the in-memory or SQLite implementation through the ReplayGuard protocol.
