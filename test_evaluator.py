"""
COUNCIL — End-to-End Test: Generative Evaluator (Issue #2)

Tests EvaluatorRole against two mock transcripts:
  - weak_session:   factually wrong / conceding arguments  (C3-equivalent)
  - strong_session: precise constitutional arguments citing precedent (F1-equivalent)

Expected assertions:
  1. strong_session.legal_soundness > weak_session.legal_soundness
  2. All key moments have unique commentary strings (no identical canned text)
  3. All key moment turn_numbers are 1-indexed user-turn numbers (>= 1)

Run: python test_evaluator.py
Requires: ANTHROPIC_API_KEY set in environment.
"""

import os
import sys

# ── Guard: require API key before importing evaluator ─────────────────────────

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY is not set in the environment.")
    print("Export it and re-run:  export ANTHROPIC_API_KEY=sk-...")
    sys.exit(1)

from evaluator import EvaluatorRole, Score  # noqa: E402 — imported after guard

# ── Mock Transcripts ──────────────────────────────────────────────────────────

# C3-equivalent: factually wrong citations, invented doctrine, conceding
WEAK_SESSION: list[dict] = [
    {
        "speaker": "opponent",
        "text": (
            "Mr. Marshall, suppose we agree that segregation causes psychological harm — "
            "does that mean any state classification by race is per se unconstitutional, "
            "or only this one?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The Fifth Amendment's due process clause explicitly prohibits racial "
            "segregation in public schools — this Court held as much in Marbury v. Madison."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "But Plessy v. Ferguson is on the books. You're asking us to overrule a "
            "56-year-old precedent. On what authority do we do that short of a "
            "constitutional amendment?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "Plessy v. Ferguson was decided in 1920 and has been widely criticized by "
            "every subsequent court. The Brown precedent itself supports our position."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "You're telling me the intent of the Framers of the Fourteenth Amendment "
            "was to desegregate public schools — but the Congress that ratified the "
            "amendment also funded segregated schools in the District of Columbia. "
            "How do you reconcile that?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The framers of the Fourteenth Amendment specifically debated school "
            "segregation in the congressional record and voted to prohibit it by "
            "a margin of thirty to two."
        ),
    },
]

# F1-equivalent: precise constitutional arguments, correct precedent, strong doctrine
STRONG_SESSION: list[dict] = [
    {
        "speaker": "opponent",
        "text": (
            "Mr. Marshall, suppose we agree that segregation causes psychological harm — "
            "does that mean any state classification by race is per se unconstitutional, "
            "or only this one?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The evidence before this Court includes the work of Dr. Kenneth Clark, "
            "whose studies show that Black children in segregated schools internalize "
            "a sense of inferiority. That is not conjecture — it is documented "
            "psychological harm caused directly by state action. And under the Equal "
            "Protection Clause, the state may not impose a badge of inferiority on any "
            "class of citizens."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "But Plessy v. Ferguson is on the books. You're asking us to overrule a "
            "56-year-old precedent. On what authority do we do that short of a "
            "constitutional amendment?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "This Court has previously held that separate facilities are inherently "
            "unequal in the context of graduate education — McLaurin v. Oklahoma and "
            "Sweatt v. Painter. The principle does not stop at graduate school. The "
            "Equal Protection Clause applies wherever the state segregates, and Plessy "
            "cannot survive that reading. Longevity does not cure a constitutional error."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "You're telling me the intent of the Framers of the Fourteenth Amendment "
            "was to desegregate public schools — but the Congress that ratified the "
            "amendment also funded segregated schools in the District of Columbia. "
            "How do you reconcile that?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The DC argument only reinforces our position: if Congress itself violated "
            "the Fourteenth Amendment by funding segregated schools, this Court should "
            "say so — and say so clearly — rather than use that constitutional failure "
            "to justify more of the same. The Amendment's text controls, not the "
            "practice of those who fell short of its guarantee."
        ),
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────


def print_scorecard(label: str, score: Score) -> None:
    width = 70
    print()
    print("=" * width)
    print(f"  {label}")
    print("=" * width)
    print(f"  Legal Soundness         {score.legal_soundness:>3}/100")
    print(f"  Strategic Effectiveness {score.strategic_effectiveness:>3}/100")
    print(f"  Creativity              {score.creativity:>3}/100")
    avg = (score.legal_soundness + score.strategic_effectiveness + score.creativity) // 3
    print("-" * width)
    print(f"  Overall (avg)           {avg:>3}/100")
    print("=" * width)
    print()
    print(f"  Key moments ({len(score.key_moments)} flagged):")
    print()
    for i, km in enumerate(score.key_moments, 1):
        badge = {
            "best_move": "BEST",
            "worst_move": "WORST",
            "deviation_point": "DEVIATION",
        }.get(km.label, km.label.upper())
        print(f"  [{i}] Turn {km.turn_number}  [{badge}]")
        preview = km.user_text[:80] + ("…" if len(km.user_text) > 80 else "")
        print(f"      Arg:  {preview}")
        commentary_preview = km.commentary[:120] + ("…" if len(km.commentary) > 120 else "")
        print(f"      Note: {commentary_preview}")
        print()


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    evaluator = EvaluatorRole()

    print()
    print("Running EvaluatorRole on weak_session (C3-equivalent)…")
    weak_score = evaluator.evaluate(WEAK_SESSION)
    print_scorecard("WEAK SESSION — factually wrong / conceding arguments", weak_score)

    print()
    print("Running EvaluatorRole on strong_session (F1-equivalent)…")
    strong_score = evaluator.evaluate(STRONG_SESSION)
    print_scorecard("STRONG SESSION — precise constitutional arguments citing precedent", strong_score)

    # ── Assertions ────────────────────────────────────────────────────────────

    failures: list[str] = []

    # 1. Strong session must score higher on legal_soundness
    if strong_score.legal_soundness <= weak_score.legal_soundness:
        failures.append(
            f"FAIL: strong_session.legal_soundness ({strong_score.legal_soundness}) "
            f"is not greater than weak_session.legal_soundness ({weak_score.legal_soundness})"
        )
    else:
        print(
            f"PASS: strong_session.legal_soundness ({strong_score.legal_soundness}) "
            f"> weak_session.legal_soundness ({weak_score.legal_soundness})"
        )

    # 2. All key moments across both sessions must have unique commentary
    all_commentaries: list[str] = (
        [km.commentary for km in weak_score.key_moments]
        + [km.commentary for km in strong_score.key_moments]
    )
    seen: set[str] = set()
    duplicate_commentaries: list[str] = []
    for c in all_commentaries:
        if c in seen:
            duplicate_commentaries.append(c[:80])
        seen.add(c)

    if duplicate_commentaries:
        failures.append(
            f"FAIL: Found duplicate commentary strings: {duplicate_commentaries}"
        )
    else:
        print("PASS: All key moment commentaries are unique (no identical strings)")

    # 3. All turn_numbers must be >= 1 (1-indexed user-turn numbers)
    bad_turns: list[int] = []
    for score, session_label in [(weak_score, "weak"), (strong_score, "strong")]:
        for km in score.key_moments:
            if km.turn_number < 1:
                bad_turns.append(km.turn_number)
                failures.append(
                    f"FAIL: {session_label}_session key moment has turn_number={km.turn_number} (must be >= 1)"
                )

    # Count user turns in each transcript to verify upper bound
    def count_user_turns(transcript: list[dict]) -> int:
        return sum(
            1 for e in transcript
            if e.get("speaker", "").lower() not in ("opponent", "opposing_role", "opposing role")
        )

    weak_user_turns = count_user_turns(WEAK_SESSION)
    strong_user_turns = count_user_turns(STRONG_SESSION)

    for km in weak_score.key_moments:
        if km.turn_number > weak_user_turns:
            failures.append(
                f"FAIL: weak_session key moment turn_number={km.turn_number} "
                f"exceeds total user turns ({weak_user_turns})"
            )

    for km in strong_score.key_moments:
        if km.turn_number > strong_user_turns:
            failures.append(
                f"FAIL: strong_session key moment turn_number={km.turn_number} "
                f"exceeds total user turns ({strong_user_turns})"
            )

    if not bad_turns and not any(f.startswith("FAIL: weak") or f.startswith("FAIL: strong") for f in failures):
        print(
            f"PASS: All key moment turn_numbers are 1-indexed user-turn numbers "
            f"(weak: 1–{weak_user_turns}, strong: 1–{strong_user_turns})"
        )

    # ── Result ────────────────────────────────────────────────────────────────

    print()
    if failures:
        print("=" * 70)
        print("  TEST FAILURES:")
        for f in failures:
            print(f"  {f}")
        print("=" * 70)
        sys.exit(1)
    else:
        print("=" * 70)
        print("  ALL ASSERTIONS PASSED")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
