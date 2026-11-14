# Contiguous event acceptance

The distributed memory merge now rejects newly received actor counters that
skip an unseen event. Existing events are checked for exact digest equality,
so duplicate replay remains idempotent while same-counter equivocation remains
rejected. New counters are checked in sorted order against the actor's
persisted high-water mark inside the same SQLite write transaction as merge.

A rejected batch is rolled back atomically. Out-of-order delivery is therefore
retryable: the receiver must obtain missing lower counters before accepting a
later event from that actor.

This protects per-actor log continuity; it is not a proof that every vector
clock dependency from every other actor is present, and it does not provide
global consensus or database snapshot anti-rollback.


## Cross-actor causal dependency completeness

Contiguous counters per actor do not alone prove that a replicated event's
vector-clock dependencies are present. Merge now accepts an event only when
its own actor counter is the next contiguous value and every referenced
counter from other actors is already stored or has been applied earlier in
the same atomic batch. The receiver resolves batches in deterministic causal
order; unresolved dependencies fail the entire transaction. A missing actor
sequence remains a distinct counter-gap error.

This prevents an event from advancing the receiver's causal frontier while
silently omitting history it claims to depend on. It is still not global
consensus, authenticated peer identity, or anti-rollback protection; those
remain separate layers.
