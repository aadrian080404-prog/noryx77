# Encrypted Persistent Memory Store

Status: implementation candidate in PR #20; CI pending.

## Implemented

`SQLiteEncryptedMemoryStore` provides an optional encrypted single-host persistence adapter compatible with the existing `MemoryStore` API.

- AES-256-GCM encrypts the canonical JSON payload.
- Each row uses a fresh 96-bit nonce and associated data binding the memory ID and key ID.
- The encryption key is injected by the caller and is never stored in SQLite.
- Startup authenticates and decrypts every row before exposing the store.
- Wrong keys, key IDs, altered ciphertext, invalid payloads and capacity overflow fail closed.
- Raw memory payload content is not stored as plaintext; the memory ID remains a visible indexed key.
- SQLite uses WAL, FULL synchronous mode, busy timeout, trusted-schema disabled and secure-delete enabled.
- A shared reentrant lock serializes the connection's transactions with in-memory state changes and reads.

## Usage

```python
from core.sqlite_memory import SQLiteEncryptedMemoryStore
from core.memory import MemoryItem

memory = SQLiteEncryptedMemoryStore(
    "/var/lib/noryx7/memory.sqlite3",
    encryption_key=secret_manager.read_bytes("noryx7/memory-encryption-key"),
    key_id="memory-key-2026-01",
)
memory.put(MemoryItem("m-1", {"fact": "verified"}, kind="long_term"))
```

The key must come from an external secret manager or KMS/HSM-backed provider. Do not hard-code it, place it beside the database, or commit it.

## Limits

- This is a single-host SQLite store, not a distributed L0-L5 memory fabric.
- AES-GCM detects ciphertext modification but cannot detect deletion or rollback of complete rows/database snapshots.
- Key rotation, recovery, external anti-rollback witness, multi-device replication, conflict resolution and distributed consistency are not implemented.
- Metadata and memory IDs are visible; only the serialized item payload is encrypted.
- This PR does not automatically replace existing in-memory MemoryStore instances.
