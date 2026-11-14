# NORYX7 — User Understanding Fabric

## Purpose

NORYX7 may prepare for a first interaction by studying content the user explicitly makes available to the system. The goal is useful familiarity: understand preferred topics, communication style, response format, workflow habits and recurring interests so the first interaction can already feel coherent.

This is **not** covert surveillance. The fabric is consent-bound, data-minimizing and scoped to interaction usefulness.

## Canonical flow

`CONSENT → CONTENT ACCESS → NORMALIZE → EXTRACT SIGNALS → SCORE CONFIDENCE → BUILD PROFILE → ADAPT FIRST INTERACTION`

Raw user content is not retained by this layer. Signals carry bounded provenance references so that the system can explain where a preference came from without storing the original text in the profile.

## Allowed signal families

- topic interests;
- preferred answer format;
- communication tone;
- preferred verbosity;
- workflow patterns such as planning, research, comparison, execution and verification.

## Explicit exclusions

The pre-interaction profile must not infer or classify sensitive personal traits. In particular, it does not create sensitive profiles about health, religion, race/ethnicity, sexuality, political affiliation, financial status or similarly sensitive characteristics merely from content exposure.

Sensitive information that a user explicitly provides for a task remains task context and must not automatically become a persistent personalization signal.

## Consent modes

- `DENIED`: no user-understanding processing.
- `PRE_INTERACTION`: one bounded analysis pass before the first interaction.
- `CONTINUOUS`: future explicit content may update the interaction profile under the same safeguards.

The engine must fail closed when consent is denied or missing.

## Swiss-clock behavior

The engine is intentionally bounded:

- maximum content items;
- maximum content size;
- maximum extracted signals;
- deterministic extraction and profile identity;
- confidence attached to every signal;
- provenance attached to every signal;
- no raw-content persistence;
- no security or authorization decisions derived from the profile.

The profile is a **cognitive personalization input**, never an authority input.

## Interaction with NORYX7 cognition

The resulting profile may influence:

`RETRIEVAL → EXPLANATION DENSITY → TONE → FORMAT → EXPLORATION/VERIFICATION BALANCE`

It may not influence:

`IDENTITY → AUTHENTICATION → AUTHORIZATION → CRYPTOGRAPHY → SECURITY POLICY → AUDIT → LOCKDOWN → RECOVERY → PRIVILEGE`

Personality and user-understanding metadata therefore remain separate from the security trust chain.

## First-interaction strategy

Before the user speaks directly to the assistant, NORYX7 can construct a small interaction hypothesis:

1. identify recurring non-sensitive interests;
2. identify preferred communication format;
3. identify likely desired response density;
4. identify workflow orientation;
5. attach confidence and evidence references;
6. use only high-confidence, interaction-relevant signals;
7. remain ready to revise the hypothesis when the user contradicts it.

The system should not pretend to know the user. It should use the profile as a probabilistic starting point and let verified user feedback correct it.

## Trust boundary

User-understanding output is untrusted cognitive metadata. It cannot directly execute tools, change permissions, alter device state, unlock the system, or modify security policy.

## Verification targets

Future verification must cover:

- consent bypass;
- raw-content retention;
- sensitive-trait inference leakage;
- provenance integrity;
- profile poisoning;
- conflicting preferences;
- stale preferences;
- profile swapping between users;
- deterministic reconstruction;
- bounded resource use;
- continuous-update abuse;
- deletion/forgetting semantics;
- isolation from authorization and security decisions;
- adversarial content designed to manipulate personalization;
- regression and million-case generated evaluation.
