# Authenticated Authorization Replay Guard

Status: implementation candidate in PR #18; CI pending.

## What is implemented

`AuthenticatedAuthorizationReplayGuard` extends the existing bounded SQLite replay guard.

- Requires an externally provisioned key of at least 32 bytes and a non-empty key ID.
- Persists keyed HMAC-SHA256 token fingerprints rather than raw nonce tokens.
- Authenticates each row's token fingerprint, expiry and key ID with a domain-separated MAC.
- Uses the base guard's SQLite WAL, FULL synchronous mode, busy timeout and restrictive file permissions.
- Verifies every stored authenticated row at startup and verifies rows before use or expiry reclamation.
- Fails closed on malformed/tampered rows, wrong keys, mismatched key IDs and legacy unkeyed replay state.
- Exposes `integrity_protected` so callers can distinguish authenticated state from ordinary durable SQLite.

`AuthorizationAuthority(..., require_authenticated_replay=True)` makes the high-assurance configuration explicit and rejects an ordinary unkeyed replay guard at construction. The default remains compatibility mode and does not claim authenticated integrity.

## Example configuration

The key must come from a secret manager, KMS/HSM-backed provider or another protected provisioning channel. Do not hard-code it, store it beside the database, commit it, or derive it from public configuration.

```python
from core.authorization_replay import AuthenticatedAuthorizationReplayGuard
from core.actions import AuthorizationAuthority

guard = AuthenticatedAuthorizationReplayGuard(
    integrity_key=secret_manager.read_bytes("noryx7/replay-integrity-key"),
    key_id="replay-integrity-2026-01",
    path="/var/lib/noryx7/authorization-replay.sqlite3",
)
authority = AuthorizationAuthority(
    secret=authorization_secret,
    replay_guard=guard,
    require_authenticated_replay=True,
)
```

## Security boundary and residual work

HMAC authenticates rows but cannot detect deletion or rollback of the complete SQLite database. A production anti-rollback guarantee still needs an external monotonic witness outside the database rollback domain (for example, a remote quorum witness or hardware-backed monotonic counter), plus a defined crash/recovery protocol.

Key rotation and recovery are not automated. The current implementation binds the database metadata to one key ID and fails closed on a different key ID. A future rotation protocol must authenticate the transition and preserve replay protection without silently discarding outstanding nonces.

Legacy unkeyed replay records are not migrated automatically. They must be explicitly expired, quarantined or migrated under a separately reviewed policy.

This is not a claim that all NORYX7 runtime paths currently use this guard. Each privileged runtime deployment must explicitly provision the key and set `require_authenticated_replay=True`.
