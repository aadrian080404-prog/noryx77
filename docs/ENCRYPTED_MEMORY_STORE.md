# NORYX7 Encrypted Memory Store

Status: implementation candidate in PR #15; CI not yet verified.

## Implemented

`core.SQLiteEncryptedMemoryStore` extends the existing bounded `MemoryStore` interface with optional SQLite persistence. Memory item payloads are JSON-serialized and encrypted with AES-256-GCM. The encrypted payload includes the memory ID, content, kind, source, importance and execution ID. The memory ID and key ID are also bound as authenticated associated data.

The encryption key is injected by the caller and is not stored in the database. The store requires an absolute non-symlink path, a 256-bit key and a stable key ID. SQLite is configured with WAL, FULL synchronous commits, a busy timeout, trusted-schema restrictions and secure-delete. On POSIX, the database file is set to mode 0600.

Startup decrypts and authenticates every row before making the store available. Wrong keys, key-ID mismatches, altered ciphertext, malformed payloads and capacity mismatches fail closed. Execution-scoped get/list semantics and bounded item count are inherited from MemoryStore.

## Explicit limitations

- This is a single-host SQLite backend, not a distributed L0–L5 memory fabric.
- No replica protocol, conflict resolution, cross-device synchronization or disaster-recovery workflow is implemented.
- Whole-database rollback and deletion of valid rows are not detected; an external monotonic witness is not integrated.
- Key rotation, re-encryption migration, backup/recovery and production KMS/HSM adapters are not implemented.
- Only JSON-serializable content is supported by this persistent backend. The original in-memory MemoryStore remains more permissive.
- Metadata required to locate records (memory ID and key ID) remains visible; item content and other item metadata are encrypted.
- The new store is optional and must be explicitly instantiated; existing runtime defaults remain in-memory.

The implementation improves confidentiality at rest for one local memory store. It does not establish distributed memory, complete privacy guarantees or production readiness.
