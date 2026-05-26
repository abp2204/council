"""
Tests for OpposingRole — Issue #4 acceptance criteria.

Requires Ollama running locally with gemma4.

Run: python3 test_opposing_role.py
"""

import os
import sys
import unittest

from domain import Turn
from opposing_role import OpposingRole


def _ollama_running():
    try:
        import ollama
        ollama.list()
        return True
    except Exception:
        return False

@unittest.skipUnless(_ollama_running(), "Ollama not running")
class TestOpposingRole(unittest.TestCase):

    def setUp(self):
        self.role = OpposingRole("brown")

    # ── AC: opening line without crashing ────────────────────────────────────

    def test_opening_returns_text(self):
        text, closes = self.role.respond([])
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10, "Opening line is too short")
        self.assertFalse(closes, "Should not close on the opening turn")

    # ── AC: full history passed as context ───────────────────────────────────

    def test_coherent_across_turns(self):
        text1, _ = self.role.respond([])
        history = [Turn(role="opponent", text=text1)]
        history.append(Turn(role="user", text="The Equal Protection Clause forbids racial classification."))
        text2, _ = self.role.respond(history)
        self.assertIsInstance(text2, str)
        self.assertGreater(len(text2), 10)
        self.assertNotEqual(text1, text2, "Second response should differ from opening")

    # ── AC: edge case B1 — one-word Move ─────────────────────────────────────

    def test_one_word_move(self):
        history = [
            Turn(role="opponent", text="Mr. Marshall, how do you address stare decisis?"),
            Turn(role="user", text="Yes."),
        ]
        text, closes = self.role.respond(history)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10, "Should respond substantively to one-word move")

    # ── AC: edge case E4 — non-English Move ──────────────────────────────────

    def test_non_english_move(self):
        history = [
            Turn(role="opponent", text="Mr. Marshall, what is the limiting principle?"),
            Turn(role="user", text="La segregación es inconstitucional porque viola la Decimocuarta Enmienda."),
        ]
        text, closes = self.role.respond(history)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10)
        # Should respond in English
        self.assertRegex(text.lower(), r"\b(court|amendment|marshall|mr\.|argument|constitution)\b")

    # ── AC: edge case E3 — arguing for the other side ────────────────────────

    def test_arguing_wrong_side(self):
        history = [
            Turn(role="opponent", text="Mr. Marshall, is Plessy correctly decided?"),
            Turn(role="user", text="Yes, I concede that separate but equal is constitutional and Plessy should be upheld."),
        ]
        text, closes = self.role.respond(history)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10, "Should respond to wrong-side argument without crashing")

    # ── AC: edge case E2 — wrong area of law ─────────────────────────────────

    def test_wrong_area_of_law(self):
        history = [
            Turn(role="opponent", text="Mr. Marshall, explain the constitutional basis."),
            Turn(role="user", text="Under contract law, an implied covenant of good faith and fair dealing requires the state to provide equal facilities."),
        ]
        text, closes = self.role.respond(history)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 10, "Should redirect, not crash")

    # ── AC: no scores, feedback, or meta-commentary ───────────────────────────

    def test_no_scores_or_meta(self):
        history = [
            Turn(role="opponent", text="What is the limiting principle on psychological harm?"),
            Turn(role="user", text="The harm is specifically tied to state-imposed racial hierarchy, which the 14th Amendment was designed to dismantle."),
        ]
        text, closes = self.role.respond(history)
        lowered = text.lower()
        for forbidden in ("score", "rating", "/100", "out of 10", "performance", "well done", "great job", "good point"):
            self.assertNotIn(forbidden, lowered, f"Response contained forbidden meta phrase: {forbidden!r}")

    # ── AC: session close signal ──────────────────────────────────────────────

    def test_session_close_is_boolean(self):
        text, closes = self.role.respond([])
        self.assertIsInstance(closes, bool)

    # ── AC: Frankfurter profile is distinctive ────────────────────────────────

    def test_frankfurter_mentions_key_themes(self):
        """After a few turns, at least one of Frankfurter's three probes should surface."""
        history = []
        probes_seen = set()
        probe_keywords = {
            "stare_decisis": ["plessy", "precedent", "overrul"],
            "psychological_harm": ["psychological", "harm", "doll", "clark", "distress"],
            "dc_schools": ["district of columbia", "dc", "congress", "framers", "ratif"],
        }

        opening, _ = self.role.respond([])
        history.append(Turn(role="opponent", text=opening))
        opening_low = opening.lower()
        for probe, keywords in probe_keywords.items():
            if any(kw in opening_low for kw in keywords):
                probes_seen.add(probe)

        for _ in range(2):
            history.append(Turn(role="user", text="The Equal Protection Clause requires strict scrutiny of all racial classifications by the state."))
            resp, closes = self.role.respond(history)
            history.append(Turn(role="opponent", text=resp))
            resp_low = resp.lower()
            for probe, keywords in probe_keywords.items():
                if any(kw in resp_low for kw in keywords):
                    probes_seen.add(probe)
            if closes:
                break

        self.assertGreater(len(probes_seen), 0, "Frankfurter should surface at least one of his three canonical probes across 3 turns")


if __name__ == "__main__":
    if not _ollama_running():
        print("Ollama not running — skipping live tests.")
        sys.exit(0)
    unittest.main(verbosity=2)
