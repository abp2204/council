# ADR 0004: Split AI providers — Groq for runtime, Claude for evaluation and ingestion

## Status
Accepted

## Context
COUNCIL uses AI in three distinct contexts with different requirements:

1. **Opposing Role** (runtime, per-turn) — low latency is critical; the user is waiting mid-argument. Character consistency and dialogue quality matter, but deep reasoning does not. Runs on every user turn.
2. **Evaluator** (post-session, once) — latency is acceptable. Requires nuanced legal reasoning: reconstruct the deviation delta, surface non-obvious insights, produce a structured 3-axis scorecard with specific evidence. Runs once per session.
3. **Ingestion pipeline** (operator, batch) — no latency pressure. Extracts structured Profile and Historical Record from raw transcript text. Runs once per case at authoring time.

The question was whether to use one AI provider for all three contexts or split across providers optimized for each job.

## Decision
Use two providers:
- **Groq** (llama-3.3-70b-versatile) for the Opposing Role and STT (Whisper). Groq's inference speed is the primary reason — sub-second latency on dialogue turns is achievable. Cost is near-zero at early scale.
- **Claude Sonnet** (claude-sonnet-4-6) for the Evaluator and ingestion pipeline. Complex legal reasoning, structured output reliability, and insight quality are the deciding factors. The Evaluator is the product's core value delivery; open-source models produce generic commentary that feels hollow.

## Consequences
- Two API keys to manage (GROQ_API_KEY, ANTHROPIC_API_KEY).
- Opposing Role and Evaluator have different system prompt styles and output contracts — both are already separated by ADR 0001.
- Groq Whisper handles STT on the same provider as the Opposing Role, keeping the per-turn round-trip on one network path.
- Ingestion pipeline (transcript_ingestion.py) uses Claude Sonnet, not Opus — the extraction task does not require Opus-level reasoning depth.
- If Groq's quality degrades or pricing changes, the Opposing Role can be migrated to Claude Haiku without touching the Evaluator. The split keeps providers substitutable.
