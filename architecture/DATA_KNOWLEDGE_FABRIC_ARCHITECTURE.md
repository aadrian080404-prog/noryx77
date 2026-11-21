# NORYX7 — Data Ingestion and Knowledge Fabric Architecture

**Status:** proposed architecture; implementation and verification deferred  
**Parent:** Global Architecture Closure Program  
**Consumers:** NEXUS, HYPERSYNTH, Memory, FRL, MIRROR WORLD and domain fabrics

## 1. Mission

Provide a governed path from external information to reusable, provenance-preserving knowledge. The fabric must preserve the distinction between source material, normalized data, extracted claims, derived conclusions and verified knowledge.

It is not a universal truth engine. Source provenance, freshness and reputation are evidence about origin and quality, not automatic proof of correctness.

## 2. Data classes and lifecycle

Data is classified before ingestion:
- public source material;
- licensed or contract-restricted material;
- user-provided personal content;
- organization-confidential information;
- regulated/high-impact data;
- secrets and credentials (never admitted as ordinary knowledge);
- synthetic/simulated data.

Lifecycle:
`DISCOVERED → AUTHORIZED → INGESTED → QUARANTINED / ACCEPTED → NORMALIZED → EXTRACTED → REVIEWED → INDEXED → EXPIRED / DELETED`

Each transition records policy, actor, timestamp, source and reason.

## 3. Logical pipeline

```text
SOURCE REGISTRY / CONNECTORS
           |
           v
AUTHORIZATION + RIGHTS + PURPOSE
           |
           v
INGESTION GATE + MALWARE / FORMAT CHECK
           |
           v
NORMALIZATION + ENTITY RESOLUTION
           |
           v
CLAIM / FACT / EVENT EXTRACTION
           |
           v
PROVENANCE + FRESHNESS + CONFLICT GRAPH
           |
           v
NEXUS KNOWLEDGE REPRESENTATION
           |
      +----+-----+
      |          |
      v          v
MEMORY INDEX   DOMAIN KNOWLEDGE
      |          |
      +----+-----+
           |
           v
RETRIEVAL / EVIDENCE PACK / EXPIRY
```

## 4. Components

### Source Registry
Defines source identity, owner, connector, rights, permitted purpose, update cadence, authentication mode, rate limits and revocation path. Connectors are replaceable and cannot inherit broad credentials.

### Authorization and Rights Gate
Checks consent, license, contractual scope, jurisdiction, purpose limitation and data classification before acquisition and again before reuse/export.

### Ingestion Gateway
Validates size, format, encoding, archive depth, content type, malware status, parser limits and provenance. Untrusted documents are parsed in isolated workers.

### Normalization and Entity Resolution
Converts source-specific data into typed records while retaining the original source reference and transformation lineage. Entity matches carry confidence and disambiguation evidence; ambiguous matches remain unresolved.

### Claim and Event Extractor
Extracts atomic claims, events, measurements, quotations and relations. Every extracted item points to source spans or immutable artifact locations. Extraction confidence is not a truth score.

### Provenance and Conflict Graph
Tracks source, claim, author, time, transformations, corroboration, contradiction, dependencies and retractions. Conflicting claims remain visible and time-scoped.

### Freshness and Change Monitor
Tracks publication time, observation time, ingestion time, validity interval and source update status. Time-sensitive facts expire or require refresh under domain policy.

### Knowledge Pack Builder
Creates signed, versioned offline packs with content manifest, licenses, schema versions, freshness metadata, dependency list and revocation/expiry policy.

### Retrieval and Evidence Composer
Returns bounded evidence bundles with source diversity, freshness, relevance, contradictions, missing coverage and citations. Retrieval must not silently omit material contradictions.

## 5. NEXUS and epistemic mapping

Knowledge objects are typed and versioned. The minimum epistemic distinctions are:
- OBSERVED — directly captured observation;
- EXTRACTED — machine-extracted representation from a source;
- DERIVED — inference from explicit premises;
- PROVEN — formally checked proposition under a named theory/checker;
- SIMULATED — output of a named model/run;
- HYPOTHESIS — proposed but not established;
- DISPUTED — material unresolved conflict;
- UNKNOWN — unavailable or insufficient evidence;
- UNDECIDABLE — only when undecidability relative to a specified formal theory has been established.

A source document can be observed while a claim extracted from it remains unverified. The system must not conflate “the source says X” with “X is true”.

## 6. Memory boundary

The knowledge fabric owns source lineage and reusable evidence objects. Memory owns scoped retrieval, continuity and retention. A memory record references evidence artifacts and does not become authoritative merely because it has been retrieved repeatedly.

Promotion, summarization, deduplication and compaction preserve provenance and must retain links to original sources. Deletion and legal hold propagate according to policy without silently leaving uncontrolled copies.

## 7. Privacy, security and governance

- Purpose limitation and least-privilege connector credentials.
- Tenant/principal/agent/execution scope.
- Encryption and key separation.
- Sensitive-data detection and redaction.
- Data minimization and retention limits.
- Source license and attribution tracking.
- Poisoning, prompt injection and malicious document handling.
- Connector revocation and credential rotation.
- Audit of ingest, transform, query, export, expiry and deletion.
- No hidden collection or reuse outside declared purpose.

## 8. Failure semantics

Unknown rights or provenance blocks ingestion. Parser errors quarantine the artifact. Entity ambiguity remains unresolved. Source conflict is represented, not averaged. Expired evidence is marked stale. Connector revocation blocks new acquisition and governed reuse. Integrity mismatch rejects the artifact. Resource exhaustion stops the worker with a partial/incomplete status.

## 9. Integration boundaries (future)

- NEXUS owns semantic identity and claim relations.
- Memory owns scoped continuity and retrieval.
- HYPERSYNTH requests evidence and tracks sufficiency.
- FRL verifies formal claims, not source authenticity or empirical truth.
- MIRROR WORLD consumes authorized datasets as model inputs with explicit lineage.
- Domain fabrics add domain-specific admissibility and freshness rules.
- Audit records policy decisions and data lifecycle events.

## 10. Architecture acceptance criteria

Ready for implementation only when connector contracts, data classes, rights/consent rules, provenance lineage, conflict handling, freshness, entity resolution, retention/deletion, offline pack versioning, failure semantics and cross-plane ownership are all specified. This document does not certify existing ingestion or knowledge code.
