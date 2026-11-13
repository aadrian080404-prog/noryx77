# Tiered Memory Router

`core.TieredMemoryRouter` routes `MemoryItem.kind` to explicitly injected stores:

- `working` → volatile working store
- `local`, `long_term`, `suspended` → durable local store
- `edge` → explicitly injected edge backend
- `cloud` → explicitly injected cloud backend

The durable local store is required by default. Missing edge/cloud backends fail closed; items are never silently redirected to another tier. Reads and lists detect duplicate memory IDs across stores. Execution-scoped filtering is preserved by each backend.

## Limits

This is a local routing layer, not a distributed L0–L5 replication fabric. It does not implement remote transport, replication, conflict resolution, consensus, cache coherence, node discovery or cross-device synchronization. Edge/cloud durability and availability are delegated to the injected backend implementations. The router's `durable` property only confirms the local durable store.
