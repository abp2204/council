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
from collections.abc import Generator
from typing import Protocol

import ollama

from case_library import load_case
from domain import Turn


# ── Protocol ──────────────────────────────────────────────────────────────────


class OpposingRoleProtocol(Protocol):
    """
    Formal contract for all OpposingRole implementations.

    Any object satisfying this Protocol can be used wherever an Opposing Role
    is expected — real (LLM-backed) or mock (test/offline).
    """

    def respond(self, turns: list[Turn]) -> tuple[str, bool]:
        """
        Generate the next Opposing Role line.

        Returns (response_text, closes) where closes signals that the session
        should end after this response.
        """
        ...

    def respond_stream(self, turns: list[Turn]) -> Generator[str, None, bool]:
        """
        Stream the response word-by-word.

        Yields word tokens. The generator's return value (accessible via
        StopIteration.value) carries the closes boolean.
        """
        ...


# ── Mock ──────────────────────────────────────────────────────────────────────


class MockOpposingRole:
    """
    Offline opponent for development, testing, and demo — no API key required.

    Accepts either a case_id (loads probes from the case library) or explicit
    mock_probes/mock_close lists (used by test fixtures). Cycles through the
    canonical probes in order, handles edge cases in character, and closes
    naturally once all probes have been delivered and enough user turns have
    accumulated.

    Instance is per-session; do not share across sessions.
    """

    def __init__(
        self,
        case_id: str | None = None,
        *,
        mock_probes: list[str] | None = None,
        mock_close: str | None = None,
    ) -> None:
        if case_id is not None:
            case = load_case(case_id, operator=True)
            opp = case["opposing_role"]
            self._mock_probes: list[str] = opp["mock_probes"]
            self._mock_close: str = opp["mock_close"]
            user_role = case.get("user_role", "")
            self._addressee: str = user_role.split()[1] if " " in user_role else "Counsel"
        else:
            if not mock_probes:
                raise ValueError("mock_probes must be a non-empty list when case_id is not given")
            if mock_close is None:
                raise ValueError("mock_close is required when case_id is not given")
            self._mock_probes = mock_probes
            self._mock_close = mock_close
            self._addressee = "Counsel"

        self._probe_index: int = 0
        self._probes_completed: bool = False

    def respond(self, turns: list[Turn]) -> tuple[str, bool]:
        user_turns = [t for t in turns if t.role == "user"]
        n = len(user_turns)

        if not self._probes_completed and self._probe_index >= len(self._mock_probes):
            self._probes_completed = True

        # Close once all probes have been asked and there are enough user turns
        if self._probes_completed and n >= 3:
            return self._mock_close, True

        # Edge-case detection on the most recent user turn
        if user_turns:
            last = user_turns[-1].text
            edge = self._edge_case_response(last)
            if edge:
                return edge, False

        # Pick the next probe in sequence
        response = self._mock_probes[self._probe_index % len(self._mock_probes)]
        self._probe_index += 1

        if self._probe_index >= len(self._mock_probes):
            self._probes_completed = True

        closes = self._probes_completed and n >= 3
        return response, closes

    def respond_stream(self, turns: list[Turn]) -> Generator[str, None, bool]:
        """Stream mock response word-by-word; return closes via StopIteration.value."""
        text, closes = self.respond(turns)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == len(words) - 1 else word + " "
        return closes

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

    MODEL = "gemma4"

    def __init__(self, case_id: str, model: str | None = None) -> None:
        case = load_case(case_id, operator=True)
        self._profile = case["opposing_role"]
        self._model = model or self.MODEL

    def respond(self, turn_history: list[Turn]) -> tuple[str, bool]:
        """Generate the next Opposing Role line. Returns (response_text, closes)."""
        messages = self._build_messages(turn_history)
        api_response = ollama.chat(model=self._model, messages=messages)
        raw = api_response.message.content.strip()
        return self._parse_response(raw)

    def respond_stream(self, turn_history: list[Turn]):
        """
        Generate the full response via Ollama, parse the JSON envelope, then
        stream the clean response text word-by-word.

        Accumulating before yielding prevents the raw JSON wrapper from reaching
        the client. StopIteration.value carries the closes boolean.
        """
        messages = self._build_messages(turn_history)
        accumulated: list[str] = []
        for chunk in ollama.chat(model=self._model, messages=messages, stream=True):
            token: str = chunk.message.content
            if token:
                accumulated.append(token)
        full_raw = "".join(accumulated)
        text, closes = self._parse_response(full_raw)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word if i == len(words) - 1 else word + " "
        return closes

    def _build_messages(self, turn_history: list[Turn]) -> list[dict]:
        """Convert the session Turn list to the OpenAI-compatible messages format."""
        system_prompt = self._profile["system_prompt"] + "\n\nIMPORTANT: Always respond in English only, regardless of the language of the user's input."
        messages: list[dict] = [
            {"role": "system", "content": system_prompt}
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
