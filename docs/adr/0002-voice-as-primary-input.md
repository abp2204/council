# ADR 0002: Voice is the primary input modality

## Status
Accepted

## Context
Users make Moves by submitting arguments during a Session. The product supports both voice and typed text input. A decision was needed on which to treat as the primary modality — the one recommended to users and optimized for in the UX.

## Decision
Voice is the primary input modality. Text is a supported fallback, but the product actively recommends voice. The UX defaults to voice input.

## Consequences
- Mirrors real courtroom advocacy — lawyers argue out loud, not in writing. Voice input makes the simulation feel authentic in a way typing cannot.
- Requires speech-to-text infrastructure (transcription before each Move is evaluated).
- Latency from transcription adds to each turn's round-trip time — must be optimized.
- Accessibility fallback (text) must be kept first-class despite not being the primary path.
- The Evaluator scores spoken argument quality, which may differ from written quality — scoring prompts must account for the oral register.
