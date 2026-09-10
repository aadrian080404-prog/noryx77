# WAVE 11 — MULTIMODAL & VOICE FABRIC

Dependency: Wave 10 CLOSED.

## Goal
Connect text, voice, live vision and multimodal inputs/outputs to the same canonical session → identity → understanding → HYPERSYNTH → authorization → runtime → verification → audit path.

## Must verify
- audio input contract and bounded transcription boundary;
- TTS output boundary and provenance;
- live vision ingestion, normalization and authorization;
- modality-specific identity/session binding;
- cross-modal task IDs and execution IDs remain stable;
- no microphone/camera capability can bypass ActionGate/policy;
- malformed/untrusted media fails closed;
- hosted web exposes only genuinely configured capabilities.

## Closure tests
Text + voice + vision equivalent task; forged modality identity; oversized/malformed payload; provider unavailable; recovery during multimodal execution; provenance across the entire path.
