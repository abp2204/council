# ADR 0001: Evaluator is a separate AI role from the Opposing Role

## Status
Accepted

## Context
During a Session, the AI inhabits an Opposing Role (e.g., Justice Kennedy asking hard questions). At the end of the Session, the user receives a Score across three dimensions: legal soundness, strategic effectiveness, and creativity.

The question was whether one AI handles both jobs — playing the Opposing Role during the Case and delivering the Score at the end — or whether these are two distinct roles.

## Decision
The Evaluator is a separate AI role from the Opposing Role. The Opposing Role never scores; the Evaluator never speaks during the Case. After the Session ends, the Evaluator reads the full Session transcript cold and produces the scorecard.

## Consequences
- The Opposing Role stays fully in character throughout the Case — no immersion-breaking "stepping out of character" to deliver feedback.
- The Evaluator has full context (the complete Session transcript) when scoring, producing better evaluations than incremental per-turn scoring would.
- The Evaluator only runs once per Session (at the end), not on every turn — lower latency and cost during play.
- Requires maintaining two distinct system prompts and AI contexts per Case type.
