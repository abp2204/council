# ADR 0003: Deviation from the historical path is implicit, not a mode

## Status
Accepted

## Context
Cases are grounded in real historical proceedings with a known Historical Record — what the real lawyer actually argued. Users can follow that path or argue differently. The question was whether "going off-script" should be an explicit product mode (a toggle, a prompt, a separate "free play" option) or simply what happens naturally when the user argues differently.

## Decision
Deviation is implicit. There is no mode toggle, no explicit branch points, and no "free play" vs. "historical" mode. The AI Opposing Role always responds to what the user actually says, regardless of whether it matches the Historical Record. The Historical Record is a reference used by the Evaluator at the end — not a constraint on the simulation during play.

## Consequences
- Users are never interrupted mid-argument by prompts asking whether they want to deviate. The simulation flows naturally.
- The "creativity" scoring dimension gains meaning: the Evaluator can reward users who found better arguments than the historical lawyer used.
- Eliminates the content authoring cost of marking explicit branch points in every Case.
- The Opposing Role must be fully generative — it cannot rely on scripted responses keyed to the historical path, since the user may say anything.
- The Evaluator's job is more complex: it must reconstruct the deviation delta (where the user diverged and with what consequence) from the Session transcript alone.
