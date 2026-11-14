# Runtime High-Risk Authorization — Authenticated Replay Mode

Status: implementation candidate in PR #23; CI pending.

The runtime already requires a durable replay guard for high-risk actions. It now has an explicit stricter mode:

`RuntimeEngine(..., require_authenticated_replay_guard=True)`

At construction, this mode rejects a missing guard, an in-memory guard, or a file-backed guard that does not advertise authenticated integrity. The same condition is checked immediately before high-risk authorization is consumed.

Use `AuthenticatedAuthorizationReplayGuard` with an externally provisioned key and stable key ID. Do not store the key with the SQLite database or hard-code it.

Compatibility mode remains the default so existing development and integration tests do not silently change their security assumptions. Therefore this PR does not claim every current RuntimeEngine instance is using authenticated replay protection; production configuration must opt in.

HMAC detects record tampering but not whole-database deletion or rollback. A production deployment still needs an external monotonic witness. The runtime's in-memory step journal also remains non-durable until a persistent runtime journal is implemented and configured.
