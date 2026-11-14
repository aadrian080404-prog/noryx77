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
