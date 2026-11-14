# JARVIS

Standalone assistant component. This directory is intentionally isolated from NORYX7/HYPERSYNTH internals.

## Architecture

- `core/` domain contracts, orchestration and policy boundaries
- `providers/` model/provider adapters
- `memory/` bounded memory interfaces
- `tools/` capability/tool adapters
- `security/` authorization, audit and secrets boundaries
- `api/` local service boundary
- `tests/` regression tests

JARVIS must never execute an external action directly from model output. Plans are proposed, policy authorizes, capabilities execute, and audit records the result.
