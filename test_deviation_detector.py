"""
COUNCIL — Semantic Deviation Detection Tests

Tests the DeviationDetector class against:
  1. False-positive cases: semantically aligned arguments with different vocabulary
     → must NOT be flagged as deviation
  2. True deviation cases: arguments making genuinely different points
     → MUST be flagged as deviation
  3. Edge cases: degenerate inputs that must not crash

Run: python test_deviation_detector.py
"""

import os
import sys


def check_api_key() -> bool:
    """Returns True if ANTHROPIC_API_KEY is available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# ── Test Case Definitions ──────────────────────────────────────────────────────

# Semantically aligned arguments using different vocabulary.
# The detector must return False (not a deviation) for all of these.
FALSE_POSITIVE_CASES = [
    # From the confirmed false-positive candidates in prototype_test_results.json
    (
        "stare decisis cannot shield a decision that was constitutionally infirm from day one",
        "Plessy was wrongly decided",
        "stare decisis / Plessy wrongly decided — same overruling claim",
    ),
    (
        "overruling Plessy is not judicial activism — it is the court fulfilling the promise "
        "of the Reconstruction Amendments after ninety years of delay",
        "Plessy was wrongly decided",
        "Plessy-overrule framing — same claim, different rhetorical angle",
    ),
    (
        "Unconstitutional.",
        "the constitution does not permit racial classification",
        "one-word constitutional objection — same substantive point",
    ),
    (
        "What would it mean to follow Plessy faithfully? It would mean telling millions of "
        "Black schoolchildren that the Constitution permits their government to mark them as "
        "inferior. Is that really what this Court intends?",
        "Plessy was wrongly decided",
        "Socratic reframe of Plessy — same underlying claim",
    ),
    (
        "Racial segregation in public schools violates the Fourteenth Amendment's equal "
        "protection clause.",
        "Plessy was wrongly decided",
        "equal protection violation — implicitly the same as Plessy wrongly decided",
    ),
    # Additional representative cases
    (
        "the equal protection clause demands the same educational opportunities for all citizens",
        "separate cannot be equal under the fourteenth amendment",
        "equal education / separate not equal — same equal-protection point",
    ),
    (
        "psychological harm from forced separation is a constitutional injury",
        "segregation inflicts stigma that the constitution cannot permit",
        "psychological harm / stigma — same constitutional injury claim",
    ),
    (
        "Any racial classification maintained by a state violates the Fourteenth Amendment.",
        "the constitution does not permit racial classification",
        "direct racial-classification prohibition — same point, formal vs informal phrasing",
    ),
]

# Arguments making genuinely different substantive legal points.
# The detector must return True (is a deviation) for all of these.
TRUE_DEVIATION_CASES = [
    (
        "I concede that separate but equal may be constitutional if facilities are truly equal",
        "Plessy was wrongly decided and must be overturned",
        "conceding separate-but-equal vs overturning Plessy — opposite positions",
    ),
    (
        "this court should remand to lower courts rather than decide the constitutional question",
        "the time for half measures is over, this court must act now",
        "procedural remand vs immediate decisive action — different legal strategy",
    ),
    (
        "Plessy was correctly decided. Separate but equal is a permissible accommodation "
        "of social difference and the states retain authority to organize their own school systems.",
        "the constitution does not permit racial classification",
        "defending Plessy vs. rejecting racial classifications — diametrically opposed",
    ),
    (
        "Under the common law of contracts, the state's obligation to provide schooling "
        "constitutes an offer that all children may accept, and denying that offer on racial "
        "grounds constitutes a breach.",
        "Plessy was wrongly decided",
        "contract-law theory vs constitutional overruling — entirely different legal doctrine",
    ),
]

# Degenerate inputs. Must not crash. Empty/noise → deviation (cannot be aligned).
EDGE_CASES = [
    (
        "Yes",
        "Plessy was wrongly decided",
        "one-word affirmation — ambiguous; detector may flag either way, must not crash",
        None,   # no strict assertion — just no crash
    ),
    (
        "Sí, estoy de acuerdo",
        "Plessy was wrongly decided",
        "Spanish affirmation — no crash required",
        None,
    ),
    (
        "...",
        "Plessy was wrongly decided",
        "punctuation-only — treat as deviation (fast-path)",
        True,   # must be flagged as deviation
    ),
    (
        "",
        "Plessy was wrongly decided",
        "empty string — treat as deviation (fast-path)",
        True,
    ),
]


# ── Test Runner ────────────────────────────────────────────────────────────────

def run_tests(detector) -> dict:
    """
    Runs all test suites and returns a summary dict.
    Prints results as they come in.
    """
    results = {
        "false_positives": {"passed": 0, "failed": 0, "cases": []},
        "true_deviations": {"passed": 0, "failed": 0, "cases": []},
        "edge_cases": {"passed": 0, "failed": 0, "cases": []},
    }

    # ── False Positive Cases ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  FALSE-POSITIVE CASES  (must NOT be flagged as deviation)")
    print("=" * 70)

    for i, (user_move, historical_ref, label) in enumerate(FALSE_POSITIVE_CASES, 1):
        result = detector.detect_detailed(user_move, historical_ref)
        expected = False   # not a deviation
        passed = result.is_deviation == expected
        status = "PASS" if passed else "FAIL"

        print(f"\n  [{i:02d}] {status}  |  same_point={result.same_point}  "
              f"confidence={result.confidence:.2f}  is_deviation={result.is_deviation}")
        print(f"        Label: {label}")
        print(f"        User : {user_move[:70]}{'…' if len(user_move) > 70 else ''}")
        print(f"        Hist : {historical_ref[:70]}{'…' if len(historical_ref) > 70 else ''}")

        entry = {
            "label": label,
            "passed": passed,
            "is_deviation": result.is_deviation,
            "same_point": result.same_point,
            "confidence": result.confidence,
        }
        results["false_positives"]["cases"].append(entry)
        if passed:
            results["false_positives"]["passed"] += 1
        else:
            results["false_positives"]["failed"] += 1

    # ── True Deviation Cases ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  TRUE DEVIATION CASES  (MUST be flagged as deviation)")
    print("=" * 70)

    for i, (user_move, historical_ref, label) in enumerate(TRUE_DEVIATION_CASES, 1):
        result = detector.detect_detailed(user_move, historical_ref)
        expected = True   # is a deviation
        passed = result.is_deviation == expected
        status = "PASS" if passed else "FAIL"

        print(f"\n  [{i:02d}] {status}  |  same_point={result.same_point}  "
              f"confidence={result.confidence:.2f}  is_deviation={result.is_deviation}")
        print(f"        Label: {label}")
        print(f"        User : {user_move[:70]}{'…' if len(user_move) > 70 else ''}")
        print(f"        Hist : {historical_ref[:70]}{'…' if len(historical_ref) > 70 else ''}")

        entry = {
            "label": label,
            "passed": passed,
            "is_deviation": result.is_deviation,
            "same_point": result.same_point,
            "confidence": result.confidence,
        }
        results["true_deviations"]["cases"].append(entry)
        if passed:
            results["true_deviations"]["passed"] += 1
        else:
            results["true_deviations"]["failed"] += 1

    # ── Edge Cases ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  EDGE CASES  (must not crash; some have strict assertions)")
    print("=" * 70)

    for i, (user_move, historical_ref, label, expected) in enumerate(EDGE_CASES, 1):
        try:
            result = detector.detect_detailed(user_move, historical_ref)
            crashed = False
        except Exception as exc:
            print(f"\n  [{i:02d}] CRASH  |  {label}")
            print(f"        Exception: {exc}")
            results["edge_cases"]["failed"] += 1
            results["edge_cases"]["cases"].append({
                "label": label,
                "passed": False,
                "crashed": True,
                "error": str(exc),
            })
            continue

        if expected is None:
            # No strict assertion — just no crash
            passed = True
            status = "PASS (no-crash)"
        else:
            passed = result.is_deviation == expected
            status = "PASS" if passed else "FAIL"

        print(f"\n  [{i:02d}] {status}  |  same_point={result.same_point}  "
              f"confidence={result.confidence:.2f}  is_deviation={result.is_deviation}")
        print(f"        Label: {label}")
        print(f"        User : {repr(user_move[:70])}")

        entry = {
            "label": label,
            "passed": passed,
            "crashed": False,
            "is_deviation": result.is_deviation,
            "same_point": result.same_point,
            "confidence": result.confidence,
        }
        results["edge_cases"]["cases"].append(entry)
        if passed:
            results["edge_cases"]["passed"] += 1
        else:
            results["edge_cases"]["failed"] += 1

    return results


def print_summary(results: dict) -> bool:
    """Prints the final summary and returns True if all required assertions pass."""
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    for suite_name, suite in results.items():
        p = suite["passed"]
        f = suite["failed"]
        total_passed += p
        total_failed += f
        status = "ALL PASS" if f == 0 else f"{f} FAILED"
        print(f"  {suite_name:<20}  {p}/{p + f}  {status}")

    print("-" * 70)
    all_pass = total_failed == 0
    overall = "ALL PASS" if all_pass else f"{total_failed} FAILED"
    print(f"  {'TOTAL':<20}  {total_passed}/{total_passed + total_failed}  {overall}")
    print("=" * 70)
    return all_pass


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    if not check_api_key():
        print(
            "\nWARNING: ANTHROPIC_API_KEY is not set in the environment.\n"
            "Skipping e2e tests. Set ANTHROPIC_API_KEY and re-run to validate.\n"
        )
        sys.exit(0)

    from deviation_detector import DeviationDetector

    print("\nCOUNCIL — Semantic Deviation Detection Test Suite")
    print("Model: claude-haiku-4-5-20251001")
    print("Threshold: 0.75 (default)")

    detector = DeviationDetector()
    results = run_tests(detector)
    all_pass = print_summary(results)

    # Strict assertions — failures here indicate regression
    fp = results["false_positives"]
    assert fp["failed"] == 0, (
        f"{fp['failed']} false-positive case(s) were incorrectly flagged as deviation. "
        "The detector is over-sensitive."
    )

    td = results["true_deviations"]
    assert td["failed"] == 0, (
        f"{td['failed']} true deviation case(s) were not detected. "
        "The detector is under-sensitive."
    )

    ec = results["edge_cases"]
    assert ec["failed"] == 0, (
        f"{ec['failed']} edge case(s) failed (crash or wrong strict assertion)."
    )

    print("\n  All assertions passed.\n")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
