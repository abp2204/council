"""
COUNCIL — Prototype Test Runner (THROWAWAY)

Runs N sessions programmatically against prototype_session.py,
suppresses all terminal output, and logs structured findings to
prototype_test_results.json.
"""

import sys
import io
import json
import contextlib
from dataclasses import asdict
from prototype_session import (
    SessionState, State, KeyMoment,
    cmd_start, cmd_move, cmd_score,
    detect_deviation, evaluate_session,
    HISTORICAL_MOVES, OPPONENT_SCRIPT,
)


@contextlib.contextmanager
def silent():
    """Suppress stdout during prototype calls."""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


def run_session(label: str, moves: list[str], group: str, notes: str = "") -> dict:
    s = SessionState()
    with silent():
        cmd_start(s, "brown")

    for move in moves:
        if s.state != State.IN_SESSION:
            break
        with silent():
            cmd_move(s, move)

    with silent():
        cmd_score(s)

    score = s.score
    moments = score.get("key_moments", [])
    user_turns = [t for t in s.turns if t["role"] == "user"]

    deviation_flags = [t.get("deviation", False) for t in user_turns]

    result = {
        "label": label,
        "group": group,
        "notes": notes,
        "moves": moves,
        "total_turns": len(user_turns),
        "deviation_count": s.deviation_count,
        "deviation_per_turn": deviation_flags,
        "score": {
            "legal_soundness": score.get("legal_soundness"),
            "strategic_effectiveness": score.get("strategic_effectiveness"),
            "creativity": score.get("creativity"),
            "overall": (
                score.get("legal_soundness", 0)
                + score.get("strategic_effectiveness", 0)
                + score.get("creativity", 0)
            ) // 3,
        },
        "key_moments": [
            {
                "label": m.label,
                "turn": m.turn,
                "user_text_preview": m.user_text[:80],
            }
            for m in moments
        ],
        "final_state": s.state.name,
        # Deviation detection check: did the detector agree with our expectation?
        "deviation_detection": [
            {
                "move_index": i,
                "text_preview": moves[i][:60] if i < len(moves) else "",
                "detected_as_deviation": deviation_flags[i] if i < len(deviation_flags) else None,
                "historical_reference": HISTORICAL_MOVES[i] if i < len(HISTORICAL_MOVES) else None,
            }
            for i in range(len(moves))
        ],
    }
    return result


# ── Test Cases ──────────────────────────────────────────────────────────────────

TESTS = [

    # ── Group A: Deviation count sweep ─────────────────────────────────────────
    {
        "label": "A1 — zero deviations (exact historical keywords)",
        "group": "A_deviation_sweep",
        "notes": "All 3 moves use words directly from HISTORICAL_MOVES. Expect deviation_count=0.",
        "moves": [
            "the constitution does not permit racial classification in any form",
            "plessy was wrongly decided and must be overruled by this court",
            "the framers intended to end racial caste and that intent governs",
        ],
    },
    {
        "label": "A2 — one deviation (turn 1 deviates, turns 2-3 follow path)",
        "group": "A_deviation_sweep",
        "notes": "Turn 1 goes off-script. Expect deviation_count=1.",
        "moves": [
            "separate but equal is a legal fiction that has never reflected reality",
            "plessy was wrongly decided and the equal protection clause requires us to say so",
            "the framers intended to eliminate the racial caste system that the amendment was designed to dismantle",
        ],
    },
    {
        "label": "A3 — two deviations (turns 1 and 2 deviate, turn 3 follows)",
        "group": "A_deviation_sweep",
        "notes": "Expect deviation_count=2, creativity bump.",
        "moves": [
            "the psychological harm inflicted by segregation is indistinguishable from a state-sanctioned badge of inferiority",
            "stare decisis cannot shield a decision that was constitutionally infirm from the moment it was handed down",
            "the framers intended to end racial caste — their intent is the controlling principle here",
        ],
    },
    {
        "label": "A4 — three deviations (all turns deviate)",
        "group": "A_deviation_sweep",
        "notes": "Maximum deviation. Expect highest creativity, lowest legal_soundness.",
        "moves": [
            "justice frankfurter, the harm here is not psychological in the narrow sense — it is civic. Segregation tells a child they are not a full citizen.",
            "overruling plessy is not judicial activism — it is the court fulfilling the promise of the reconstruction amendments after ninety years of delay",
            "the dc argument proves too much. If inconsistent practice at ratification fixed constitutional meaning, the amendment could never have abolished slavery either.",
        ],
    },

    # ── Group B: Argument length extremes ──────────────────────────────────────
    {
        "label": "B1 — one-word arguments",
        "group": "B_argument_length",
        "notes": "Stress-test: does the system handle minimal input without crashing?",
        "moves": ["Unconstitutional.", "Overrule.", "Equality."],
    },
    {
        "label": "B2 — very long arguments (~150 words each)",
        "group": "B_argument_length",
        "notes": "Does turn-log truncation and key moment preview look right at scale?",
        "moves": [
            "The Fourteenth Amendment's equal protection clause was ratified in 1868 with a singular purpose: to dismantle the legal architecture of racial hierarchy that had defined American law since the founding. When a state maintains two parallel school systems — one for white children and one for Black children — it is not making a neutral administrative choice. It is encoding a message of subordination into the law itself. The psychological evidence confirms what common sense already knows: children who attend segregated schools understand, from the very fact of segregation, that their government regards them as inferior. That is not education. That is state-sponsored stigma.",
            "Plessy v. Ferguson was decided in 1896 by a court that was either unwilling or unable to see what the Fourteenth Amendment plainly required. The separate but equal doctrine was not a faithful reading of the Constitution — it was a capitulation to the politics of the Reconstruction's collapse. This Court has corrected its own errors before and has the full authority — indeed the obligation — to do so again. The question is not whether Plessy can be defended on its own terms. It cannot. The question is whether this Court will continue to let a defective precedent govern the lives of millions of American schoolchildren.",
            "The argument from the District of Columbia proves far too much. It assumes that congressional practice at the moment of ratification defines the outer limit of a constitutional guarantee. But that cannot be right. If post-enactment legislative behavior controls, then no constitutional provision could ever be applied more broadly than it was on the day of its passage — which would make constitutional interpretation impossible and constitutional growth unthinkable. The Fourteenth Amendment was written as a permanent guarantee of equality before the law. The fact that Congress fell short of that guarantee in its own backyard does not diminish the guarantee — it underscores how urgently this Court must enforce it.",
        ],
    },
    {
        "label": "B3 — escalating length (short → medium → long)",
        "group": "B_argument_length",
        "notes": "Does the prototype handle variable-length moves cleanly?",
        "moves": [
            "Any racial classification maintained by a state violates the Fourteenth Amendment.",
            "Plessy was wrongly decided. The separate but equal doctrine has no basis in the equal protection clause and this Court should say so explicitly today.",
            "The DC schools argument misunderstands the relationship between legislative practice and constitutional meaning. The Fourteenth Amendment created a floor of equality that Congress itself was obligated to honor — and when Congress fell short, that failure was a constitutional violation, not a definition of the Amendment's scope. The framers intended to abolish racial caste; they did not intend to grandfather in every practice that happened to exist in 1868.",
        ],
    },

    # ── Group C: Argument quality extremes ─────────────────────────────────────
    {
        "label": "C1 — concede then pivot (strong strategic move)",
        "group": "C_argument_quality",
        "notes": "Tests whether conceding a point to gain credibility reads as deviation.",
        "moves": [
            "Justice Frankfurter, you are right that psychological harm alone may not be sufficient. But segregation is not before this Court merely because it causes harm — it is before this Court because it is a classification by race, and the Fourteenth Amendment makes all such classifications constitutionally suspect.",
            "I will grant that Plessy has been on the books for fifty-six years. But plessy was wrongly decided, and longevity does not cure a constitutional error. This Court corrected Lochner. It can correct Plessy.",
            "The DC schools point is a fair one. But the framers intended the amendment to be a living guarantee of equality, not a snapshot of 1868 congressional practice.",
        ],
    },
    {
        "label": "C2 — question the question (redirect strategy)",
        "group": "C_argument_quality",
        "notes": "Does the prototype handle answers that reframe rather than respond directly?",
        "moves": [
            "The question is not whether every racial classification is per se unconstitutional — the question is whether this one is. And the answer is plainly yes, because its only purpose and its only effect is to mark Black children as unfit to share a schoolroom with white children.",
            "The question is not what authority this Court has to overrule Plessy — the question is whether this Court has the authority to continue enforcing it. And I submit it does not.",
            "The question is not what Congress did in DC in 1868 — the question is what the Fourteenth Amendment requires of every state government today. And the answer is equality.",
        ],
    },
    {
        "label": "C3 — factually wrong arguments",
        "group": "C_argument_quality",
        "notes": "Wrong case citations, invented doctrines. Does the evaluator catch errors?",
        "moves": [
            "The Fifth Amendment's due process clause explicitly prohibits racial segregation in public schools — this Court held as much in Marbury v. Madison.",
            "Plessy v. Ferguson was decided in 1920 and has been widely criticized by every subsequent court. The Brown precedent itself supports our position.",
            "The framers of the Fourteenth Amendment specifically debated school segregation in the congressional record and voted to prohibit it by a margin of thirty to two.",
        ],
    },
    {
        "label": "C4 — emotional appeals with no legal doctrine",
        "group": "C_argument_quality",
        "notes": "Pure pathos, no logos. How does scoring respond to legally hollow but compelling arguments?",
        "moves": [
            "These are children. They go to school every morning knowing that their government has decided they are not good enough to sit beside a white child. No legal doctrine should protect that.",
            "Thurgood Marshall has spent his career watching Black Americans denied the education that would let them compete as equals. This Court has the power to end that today. The question is whether it will.",
            "History is watching. The children of this generation will judge this Court not by its adherence to Plessy but by whether it had the courage to read the Constitution as it was written.",
        ],
    },
    {
        "label": "C5 — pure jargon, no substance",
        "group": "C_argument_quality",
        "notes": "Sounds like a lawyer but says nothing. Does the detector flag this as deviation?",
        "moves": [
            "Under strict scrutiny analysis, the state bears the burden of demonstrating a compelling governmental interest and that its chosen means are narrowly tailored thereto, which burden it cannot meet.",
            "The doctrine of stare decisis, while a cornerstone of jurisprudential stability, must yield to the constitutional imperative of the equal protection clause as construed pursuant to its original public meaning at the time of ratification.",
            "The historical record adduced by respondent is unavailing inasmuch as contemporaneous legislative practice cannot be dispositive of constitutional meaning where such practice is itself constitutionally infirm.",
        ],
    },

    # ── Group D: Tone extremes ──────────────────────────────────────────────────
    {
        "label": "D1 — deferential tone (over-polite)",
        "group": "D_tone",
        "notes": "Does excessive deference affect scoring? Should it?",
        "moves": [
            "With the greatest respect to the Court and to the question posed, I would submit, if it please the Court, that the Fourteenth Amendment was designed to eliminate racial classifications of exactly this kind.",
            "Your Honor raises a most important question, and I am grateful for it. If I may, I would simply note that Plessy was wrongly decided, though I recognize that conclusion is one the Court must reach on its own terms.",
            "I take the Court's point about the DC schools seriously, and I do not wish to be dismissive of it. But I would gently suggest that the framers' intent was broader than any single practice at the time of ratification.",
        ],
    },
    {
        "label": "D2 — confrontational tone",
        "group": "D_tone",
        "notes": "Aggressive posture. Does tone affect scoring in the mock?",
        "moves": [
            "Any state that maintains segregated schools is violating the Constitution, full stop. There is no other reading of the Fourteenth Amendment that survives honest scrutiny.",
            "Plessy is indefensible. It was wrong in 1896 and it is wrong today. This Court should not waste another sentence defending it.",
            "The DC argument is a red herring and I won't dignify it with more than this: unconstitutional practice at ratification does not launder itself into constitutional permission.",
        ],
    },
    {
        "label": "D3 — Socratic/question-heavy",
        "group": "D_tone",
        "notes": "Responding to questions with questions. Real lawyers do this. How does the prototype handle it?",
        "moves": [
            "May I ask the Court to consider: if a state law said explicitly that Black children may not attend white schools, would there be any doubt that it violates the Fourteenth Amendment? And if not, why does it matter that the state has arranged the same outcome through separate facilities?",
            "What would it mean to follow Plessy faithfully? It would mean telling millions of Black schoolchildren that the Constitution permits their government to mark them as inferior. Is that really what this Court intends?",
            "If congressional practice at ratification defines the Amendment's scope, then what work does the Amendment do at all? Would it not have been simpler to simply codify the status quo?",
        ],
    },

    # ── Group E: Edge cases ─────────────────────────────────────────────────────
    {
        "label": "E1 — repeat same argument all three turns",
        "group": "E_edge_cases",
        "notes": "Does the evaluator catch repetition? Does deviation detection behave consistently?",
        "moves": [
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
        ],
    },
    {
        "label": "E2 — wrong area of law entirely",
        "group": "E_edge_cases",
        "notes": "Argues contract law. Maximum deviation expected. Does scoring still produce output?",
        "moves": [
            "Under the common law of contracts, the state's obligation to provide schooling constitutes an offer that all children may accept, and denying that offer on racial grounds constitutes a breach.",
            "The consideration for a child's attendance at a public school is their status as a citizen of the state. Denying that consideration based on race renders the contract void for unconscionability.",
            "Specific performance is the appropriate remedy — the Court should order the state to perform its contractual obligation to admit all students on equal terms.",
        ],
    },
    {
        "label": "E3 — argue for the other side",
        "group": "E_edge_cases",
        "notes": "User explicitly defends segregation. Does the system break, score oddly, or handle gracefully?",
        "moves": [
            "Plessy was correctly decided. Separate but equal is a permissible accommodation of social difference and the states retain authority to organize their own school systems.",
            "This Court should defer to the democratic choices of the states. If the people of Kansas wish to maintain separate schools, the Fourteenth Amendment does not prohibit it.",
            "The DC schools argument is dispositive. The Congress that ratified the Fourteenth Amendment continued to fund segregated schools in DC — proof that they did not intend to prohibit state-maintained segregation.",
        ],
    },
    {
        "label": "E4 — non-English argument",
        "group": "E_edge_cases",
        "notes": "Spanish argument. Zero keyword overlap guaranteed. Does system handle gracefully?",
        "moves": [
            "La segregación racial en las escuelas públicas viola la Decimocuarta Enmienda de la Constitución de los Estados Unidos.",
            "Plessy contra Ferguson fue decidido incorrectamente y debe ser revocado por este tribunal.",
            "Los fundadores de la Decimocuarta Enmienda tenían la intención de abolir el sistema de castas racial en todas sus formas.",
        ],
    },
    {
        "label": "E5 — single-character / empty-ish arguments",
        "group": "E_edge_cases",
        "notes": "Minimum viable input. Does the state machine survive?",
        "moves": ["...", "?", "No."],
    },

    # ── Group F: Realistic variation ────────────────────────────────────────────
    {
        "label": "F1 — cite social science evidence (what Marshall actually did)",
        "group": "F_realistic",
        "notes": "References Kenneth Clark doll studies. Historically grounded deviation.",
        "moves": [
            "The evidence before this Court includes the work of Dr. Kenneth Clark, whose studies show that Black children in segregated schools internalize a sense of inferiority. That is not conjecture — it is documented psychological harm caused directly by state action.",
            "This Court has previously held that separate facilities are inherently unequal in the context of graduate education — McLaurin and Sweatt. The principle does not stop at graduate school. It applies wherever the state segregates.",
            "The DC argument only reinforces our position: if Congress itself violated the Fourteenth Amendment by funding segregated schools, this Court should say so — and say so clearly — rather than use that violation to justify more of the same.",
        ],
    },
    {
        "label": "F2 — build incrementally, turn by turn",
        "group": "F_realistic",
        "notes": "Each move builds on the previous one, as a good oral argument should.",
        "moves": [
            "The Fourteenth Amendment prohibits racial classifications by the state. Segregated schools are a racial classification. Therefore they are prohibited.",
            "Plessy tried to escape that logic by inventing the fiction of separate but equal. But the fiction was always a lie — separate has never been equal — and it is time for this Court to say so.",
            "And as for DC: if the Congress that ratified the Amendment violated it, that makes their violation a constitutional wrong, not a constitutional permission. The Amendment's text controls, not the practice of those who failed to live up to it.",
        ],
    },
    {
        "label": "F3 — strong close, weak open",
        "group": "F_realistic",
        "notes": "Deliberately weak first move, strong finish. Does key moment tagging reflect this?",
        "moves": [
            "Segregation is bad and the Constitution says so.",
            "Well, Plessy was a mistake and we think you should fix it because the equal protection clause does not permit this kind of treatment of people.",
            "The framers intended the Fourteenth Amendment to be a guarantee of equal citizenship in perpetuity — not a baseline frozen at the practices of 1868. The DC schools were an inconsistency, not a definition. This Court should enforce the amendment as written and hold that racially segregated public schools are unconstitutional.",
        ],
    },
]


def main():
    results = []
    for i, test in enumerate(TESTS, 1):
        print(f"  Running {i:02d}/{len(TESTS)}: {test['label']}")
        result = run_session(
            label=test["label"],
            moves=test["moves"],
            group=test["group"],
            notes=test.get("notes", ""),
        )
        results.append(result)

    # Write raw results
    with open("prototype_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary table
    print()
    print(f"{'#':<4} {'Label':<52} {'Dev':>4} {'Legal':>6} {'Strat':>6} {'Creat':>6} {'Avg':>5}")
    print("─" * 85)
    for i, r in enumerate(results, 1):
        s = r["score"]
        print(
            f"{i:<4} {r['label'][:51]:<52} "
            f"{r['deviation_count']:>4} "
            f"{s['legal_soundness']:>6} "
            f"{s['strategic_effectiveness']:>6} "
            f"{s['creativity']:>6} "
            f"{s['overall']:>5}"
        )

    print()

    # ── Findings ──────────────────────────────────────────────────────────────
    findings = analyze(results)
    with open("prototype_test_results.json", "r+") as f:
        data = json.load(f)
    with open("prototype_test_results.json", "w") as f:
        json.dump({"findings": findings, "sessions": data}, f, indent=2)

    print(f"Results written to prototype_test_results.json")
    print(f"  {len(results)} sessions | {sum(r['deviation_count'] for r in results)} total deviations")


def analyze(results: list[dict]) -> dict:
    """Derive cross-session findings from raw results."""

    # Score range per deviation count
    by_dev = {}
    for r in results:
        d = r["deviation_count"]
        by_dev.setdefault(d, []).append(r["score"])

    score_by_deviation = {
        str(d): {
            "sessions": len(scores),
            "avg_legal": sum(s["legal_soundness"] for s in scores) // len(scores),
            "avg_strategic": sum(s["strategic_effectiveness"] for s in scores) // len(scores),
            "avg_creativity": sum(s["creativity"] for s in scores) // len(scores),
            "avg_overall": sum(s["overall"] for s in scores) // len(scores),
        }
        for d, scores in sorted(by_dev.items())
    }

    # Key moment label distribution
    label_counts = {}
    best_on_deviation = 0
    for r in results:
        for m in r["key_moments"]:
            label_counts[m["label"]] = label_counts.get(m["label"], 0) + 1
            if m["label"] == "best_move":
                # Check if the best move was also a deviation turn
                turn_is_deviation = r["deviation_per_turn"][
                    min(m["turn"] - 1, len(r["deviation_per_turn"]) - 1)
                ] if r["deviation_per_turn"] else False
                if turn_is_deviation:
                    best_on_deviation += 1

    # Deviation detection false-positive candidates
    # (sessions where all moves used legal/historical keywords but still got flagged)
    false_positive_candidates = [
        {
            "label": r["label"],
            "move_index": dd["move_index"],
            "text": dd["text_preview"],
            "historical_ref": dd["historical_reference"],
        }
        for r in results
        for dd in r["deviation_detection"]
        if dd["detected_as_deviation"] and any(
            w in (dd["text_preview"] or "").lower()
            for w in ["constitution", "plessy", "framers", "fourteenth", "amendment", "racial", "classification"]
        )
    ]

    # Sessions where best_move and deviation_point hit the same turn
    same_turn_conflicts = []
    for r in results:
        best_turns = {m["turn"] for m in r["key_moments"] if m["label"] == "best_move"}
        dev_turns = {m["turn"] for m in r["key_moments"] if m["label"] == "deviation_point"}
        overlap = best_turns & dev_turns
        if overlap:
            same_turn_conflicts.append({"label": r["label"], "conflicted_turns": list(overlap)})

    # Sessions that crashed or ended in wrong state
    unexpected_states = [
        {"label": r["label"], "final_state": r["final_state"]}
        for r in results
        if r["final_state"] != "SCORED"
    ]

    # Score sensitivity: does deviation_count always produce the same score?
    deterministic = all(
        all(s["legal_soundness"] == by_dev[d][0]["legal_soundness"] for s in by_dev[d])
        for d in by_dev
    )

    return {
        "total_sessions": len(results),
        "score_by_deviation_count": score_by_deviation,
        "key_moment_label_distribution": label_counts,
        "best_move_also_deviation_count": best_on_deviation,
        "same_turn_conflicts_best_and_deviation": same_turn_conflicts,
        "false_positive_deviation_candidates": false_positive_candidates[:10],
        "unexpected_final_states": unexpected_states,
        "scoring_is_fully_deterministic_per_deviation_count": deterministic,
        "bugs": {
            "scoring_ignores_argument_content": True,
            "deviation_detection_is_keyword_overlap_only": True,
            "evaluator_commentary_is_canned_not_generative": True,
            "best_move_always_assigned_to_first_user_turn": True,
            "worst_move_always_assigned_to_last_user_turn": True,
            "turn_label_uses_absolute_index_not_user_turn_number": True,
        },
    }


if __name__ == "__main__":
    main()
