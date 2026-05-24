"""
COUNCIL — Opposing Role: Profile-backed LLM (Issue #4)

Implements OpposingRole: a generative AI that inhabits the named historical
participant opposing the user during a Session. Backed by a Profile that captures
the participant's behavioral tendencies, argumentation patterns, and rhetorical habits.

ADR 0003: Deviation is implicit — the Opposing Role always responds to what the
user actually said, regardless of whether it matches the Historical Record.
ADR 0001: The Opposing Role never scores and never breaks character.

Usage:
    from opposing_role import OpposingRole
    role = OpposingRole(case_id="brown")
    text, closes = role.respond(turn_history)
"""

import json
import re

import ollama

from case_library import load_case
from domain import Turn


class MockOpposingRole:
    """
    Offline opponent for development and demo — no API key required.

    Cycles through the three canonical probes, handles edge cases in character,
    and closes naturally after all probes have been asked.
    """

    def __init__(self, case_id: str) -> None:
        case = load_case(case_id, operator=True)
        opp = case["opposing_role"]
        self._mock_probes: list[str] = opp["mock_probes"]
        self._mock_close: str = opp["mock_close"]
        self._probes_asked: list[int] = []
        user_role = case.get("user_role", "")
        self._addressee: str = user_role.split()[1] if " " in user_role else "Counsel"

    def respond(self, turn_history: list[Turn]) -> tuple[str, bool]:
        user_turns = [t for t in turn_history if t.role == "user"]
        n = len(user_turns)

        # Close after 3 user turns regardless — ensures test runner always gets a score
        if n >= 3:
            return self._mock_close, True

        # Edge-case detection on the most recent user turn
        if user_turns:
            last = user_turns[-1].text
            response = self._edge_case_response(last)
            if response:
                return response, False

        # Pick the next probe that hasn't been asked yet
        for i, probe in enumerate(self._mock_probes):
            if i not in self._probes_asked:
                self._probes_asked.append(i)
                return probe, False

        # All probes asked but not enough user turns yet — press on the last one
        return (
            f"Mr. {self._addressee}, you have not yet given me a satisfactory answer. "
            "Let me put the question again: " + self._mock_probes[self._probes_asked[-1]],
            False,
        )

    def _edge_case_response(self, text: str) -> str | None:
        words = text.split()
        lower = text.lower()

        if len(words) <= 2:
            return (
                f"That is not an answer, Mr. {self._addressee}. \"{text}\" tells me nothing "
                "about the constitutional basis for your position. "
                "I am asking you to explain the doctrinal framework."
            )

        if any(ord(c) > 127 for c in text):
            return (
                f"I confess I did not follow that, Mr. {self._addressee}. "
                "Would you kindly restate your argument for the Court?"
            )

        pro_segregation = ("separate but equal", "plessy is correct", "plessy was right",
                           "segregation is constitutional", "i concede that plessy")
        if any(phrase in lower for phrase in pro_segregation):
            return (
                f"Mr. {self._addressee}, are you now conceding that Plessy controls? "
                "That is rather remarkable for counsel who has argued the opposite "
                "in every court below. Do you wish to be heard on behalf of the "
                "respondents instead?"
            )

        off_topic = ("contract", "tort", "property law", "negligence", "common law")
        if any(phrase in lower for phrase in off_topic):
            return (
                f"Mr. {self._addressee}, we are not here on questions of common law. "
                "The issue before us is one of constitutional law under the "
                "Fourteenth Amendment. Kindly direct your argument there."
            )

        return None


# ── Opposing Role ─────────────────────────────────────────────────────────────


class OpposingRole:
    """
    Profile-backed generative opponent for a COUNCIL Session.

    Receives the full turn history on every call so responses are coherent
    across the Session. Signals session close via structured JSON output.
    """

    MODEL = "qwen2.5:14b"

    def __init__(self, case_id: str, model: str | None = None) -> None:
        case = load_case(case_id, operator=True)
        self._profile = case["opposing_role"]
        self._model = model or self.MODEL

    def respond(self, user_text: str, turn_history: list[Turn]) -> dict:
        """
        Generate the next Opposing Role line given the full turn history.

        Args:
            user_text: The user's latest argument (unused directly; already in turn_history).
            turn_history: The session's Turn list.

        Returns:
            {"response": str, "closes": bool}
        """
        messages = self._build_messages(turn_history)
        api_response = ollama.chat(model=self._model, messages=messages)
        raw = api_response.message.content.strip()
        text, closes = self._parse_response(raw)
        return {"response": text, "closes": closes}

    def respond_stream(self, turn_history: list[Turn]):
        """
        Stream the Opposing Role response token by token.

        Yields str tokens as they arrive from the model. After iteration is
        exhausted, StopIteration.value holds the closes boolean.

        The full accumulated text is parsed for the JSON output contract only
        after the stream ends — the closes signal is never emitted early.
        """
        messages = self._build_messages(turn_history)
        accumulated: list[str] = []
        for chunk in ollama.chat(model=self._model, messages=messages, stream=True):
            token: str = chunk.message.content
            if token:
                accumulated.append(token)
                yield token
        full_text = "".join(accumulated)
        _, closes = self._parse_response(full_text)
        return closes

    def _build_messages(self, turn_history: list[Turn]) -> list[dict]:
        """Convert the session Turn list to the OpenAI-compatible messages format."""
        messages: list[dict] = [
            {"role": "system", "content": self._profile["system_prompt"]}
        ]

        # Prepend a kick-off if the first turn is from the opponent
        if not turn_history or turn_history[0].role == "opponent":
            messages.append(
                {"role": "user", "content": "The oral argument has begun. Please open."}
            )

        for turn in turn_history:
            if turn.role == "user":
                messages.append({"role": "user", "content": turn.text})
            else:
                # Wrap opponent turns in the JSON envelope so the model sees
                # its own prior structured outputs in context.
                messages.append(
                    {"role": "assistant", "content": json.dumps({"response": turn.text, "closes": False})}
                )

        # Ensure the last message is from "user" (API requirement)
        if messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": "[Continue the oral argument.]"})

        return messages

    def _parse_response(self, raw: str) -> tuple[str, bool]:
        """Parse JSON response from the model; fall back gracefully on failure."""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            response_text = str(data.get("response", raw))
            closes = bool(data.get("closes", False))
        except json.JSONDecodeError:
            # Fallback: treat entire output as response text, no close signal
            response_text = raw
            closes = False

        return response_text, closes
