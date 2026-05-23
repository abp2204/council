# COUNCIL — Domain Glossary

## Case
A single bounded legal proceeding drawn from one source transcript — e.g., one oral argument, one cross-examination, one closing argument. It is the atomic unit of the product: the thing a user "plays." Cases can later be chained into multi-proceeding arcs, but the Case itself has a defined start state, a set of available arguments, and a known historical outcome.

## Move
The user's input for a single turn within a Case. A Move is free-form — spoken (preferred) or typed. Voice is the recommended input modality; text is the fallback.

## Score
A multi-dimensional evaluation of the user's performance in a Case, across three axes: legal soundness, strategic effectiveness, and creativity. Delivered as an end-of-session scorecard: three aggregate dimension scores plus 3-5 highlighted key moments (best Move, worst Move, biggest Deviation point). During the Case, quality is signaled implicitly through the Opposing Role's in-character reactions — not numerical scores.

## Opposing Role
The character the AI inhabits during a Case. Determined by the proceeding type, not fixed to "opposing counsel." Examples: Judge (oral argument), Witness (cross-examination), Opposing Counsel (motion hearing). A Case has exactly one Opposing Role, backed by a Profile.

## Profile
A behavioral fingerprint of a named historical legal participant (lawyer, judge, or witness), derived from transcript ingestion. Captures argumentation patterns, objection tendencies, question cadence, and rhetorical habits. Always tied to a specific named person in MVP. Archetypes (composite Profiles synthesized across multiple persons) are a valid future extension using the same schema.

## Transcript
The source material for a Case and its Profiles. In MVP: federal appellate oral arguments, primarily SCOTUS. Chosen for public availability, clean structure, named high-profile participants, and dramatic lawyer-judge dialogue. A single Transcript produces two parallel extractions: one Historical Record (the arguing lawyer's turns) and one or more Profiles (one per named participant on the opposing side).

## Session
One complete play-through of a Case by a user. A Case can have many Sessions. Sessions are persisted so users can track improvement across attempts and compare approaches on the same Case.

## Evaluator
A separate AI role — distinct from the Opposing Role — that produces the end-of-session Score. The Evaluator never speaks during a Case. After the Session ends, it reads the full Session transcript and delivers the multi-dimensional scorecard. Keeps the Opposing Role fully in character throughout.

## Difficulty
A user-selected setting that controls the intensity of the Opposing Role. Not in MVP — all Cases launch at authentic historical intensity. Planned feature: explicit tiers (e.g., Easy / Medium / Hard), where Hard is the historically-grounded Profile at full intensity.

## Case Library
The platform-curated collection of published Cases. All Cases in MVP are created and maintained by the COUNCIL team. User- or org-uploaded Cases are not supported in MVP but are a planned enterprise tier.

## Operator
A member of the COUNCIL team with access to the case authoring pipeline. Operators create and publish Cases using the ingestion pipeline — they are not Users. In MVP, only Operators can add Cases to the Case Library.

## Cohort
An org-scoped group of users (e.g., associates at a law firm, students in a class) with a private shared leaderboard. A Cohort belongs to an enterprise account. Scores within a Cohort are visible to Cohort members only.

## Leaderboard
A ranked view of best Scores on a given Case. Two kinds: global (opt-in, public) and Cohort (private, org-scoped). A user's Score appears on a global Leaderboard only if they opt in.

## Historical Record
The actual sequence of arguments made by the real lawyer in the original proceeding, extracted verbatim from the Transcript. Serves as the Deviation reference and one input to the Evaluator's Score. Not a "model answer" — a lawyer can score higher than the historical performance by finding a better argument.

## Session End
A Session concludes when the AI Opposing Role reaches a natural narrative close (e.g., "the court will take the matter under advisement"). The Opposing Role drives the ending — it is not gated on a fixed turn count or real-world timer.

## Review
A post-session mode available after a Score is delivered. Allows the user to expand any of the Score's flagged key moments for detailed Evaluator commentary. Does not provide full turn-by-turn annotation — only the inflection points the Evaluator surfaced.

## Deviation
What happens when the user argues differently than the historical lawyer did. Deviation is not a mode or a toggle — it is the natural state of the simulation. The AI always responds to what the user actually says. The historical path serves as a reference: the end-of-session Score surfaces where the user diverged and what consequences followed.
