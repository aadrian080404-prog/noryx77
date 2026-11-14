# Distributed-memory vector-clock dependency closure

Contiguous per-actor counters prevent a peer from skipping an actor's earlier
event, but they do not prove that the *other actors' histories named by a
vector clock* are present.

This change validates the causal closure of every incoming event before any
insert is committed:

- Every referenced actor/counter event must exist locally or in the same batch.
- An actor's previous event is treated as an implicit dependency.
- A dependency's own vector clock must be component-wise contained in the
  dependent event's clock.
- A dependency cannot already include the dependent event's actor counter;
  this rejects cyclic or future-pointing histories.
- Validation traverses transitive dependencies with a hard 100,000-event
  processing ceiling.
- Any missing or inconsistent dependency aborts the entire SQLite transaction.

The complete batch may be delivered in any order. The implementation remains
offline-first and transport-neutral. It does not create global consensus,
prove remote database freshness, or replace signed sender authentication.
