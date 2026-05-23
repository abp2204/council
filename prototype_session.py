"""
COUNCIL — Session State Machine Prototype (THROWAWAY)

Question: Does the Move → Opponent → Score → Review flow feel right?
          Specifically: when does the session end, how does deviation tracking
          feel, and does the Review mode (key moments only) make sense?

Run: python3 prototype_session.py
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from textwrap import dedent, fill
import sys
import os

from session_store import save_session, format_history_summary

# ── State Machine ──────────────────────────────────────────────────────────────

class State(Enum):
    CASE_SELECT  = auto()
    IN_SESSION   = auto()
    SESSION_END  = auto()   # AI is wrapping up; user sees final opponent line
    EVALUATING   = auto()
    SCORED       = auto()
    REVIEW       = auto()


@dataclass
class KeyMoment:
    turn: int
    label: str   # "best_move" | "worst_move" | "deviation_point"
    user_text: str
    commentary: str


@dataclass
class SessionState:
    state: State = State.CASE_SELECT
    case_id: str = ""
    session_id: int = 0
    turns: list[dict] = field(default_factory=list)   # [{role, text, deviation}]
    deviation_count: int = 0
    key_moments: list[KeyMoment] = field(default_factory=list)
    score: dict = field(default_factory=dict)         # filled at SCORED
    reviewing_moment: int | None = None               # index into key_moments


# ── Mock Data ──────────────────────────────────────────────────────────────────

CASES = {
    "brown": {
        "title": "Brown v. Board of Education (1952 Oral Argument)",
        "opposing_role": "Justice Felix Frankfurter",
        "user_role": "Thurgood Marshall (NAACP)",
        "context": "You are arguing before the Supreme Court that segregated public schools violate the Equal Protection Clause of the 14th Amendment.",
        "historical_opening": "The Fourteenth Amendment prohibits a state from maintaining a dual school system based solely on race.",
    }
}

# Scripted opponent turns — in a real build these come from a Profile-backed LLM
OPPONENT_SCRIPT = [
    {
        "text": "Mr. Marshall, suppose we agree that segregation causes psychological harm — does that mean *any* state classification by race is per se unconstitutional, or only this one?",
        "closes": False,
        "expects_keyword": None,
    },
    {
        "text": "But Plessy v. Ferguson is on the books. You're asking us to overrule a 56-year-old precedent. On what authority do we do that short of a constitutional amendment?",
        "closes": False,
        "expects_keyword": "plessy",
    },
    {
        "text": "You're telling me the intent of the Framers of the Fourteenth Amendment was to desegregate public schools — but the Congress that ratified the amendment also funded segregated schools in the District of Columbia. How do you reconcile that?",
        "closes": False,
        "expects_keyword": None,
    },
    {
        "text": "Mr. Marshall, I think you've given us a great deal to consider. We'll hear from the other side. The Court thanks you.",
        "closes": True,
        "expects_keyword": None,
    },
]

# Mock historical path (what Thurgood actually said, simplified)
HISTORICAL_MOVES = [
    "the constitution does not permit racial classification",
    "plessy was wrongly decided",
    "the framers intended to end racial caste",
]

def detect_deviation(user_text: str, turn_index: int) -> bool:
    """True if user's move diverges from the historical path."""
    if turn_index >= len(HISTORICAL_MOVES):
        return False
    historical = HISTORICAL_MOVES[turn_index]
    # Naive keyword overlap check — real version uses embeddings
    user_words = set(user_text.lower().split())
    hist_words = set(historical.lower().split())
    overlap = user_words & hist_words
    return len(overlap) < 2


def evaluate_session(s: SessionState) -> dict:
    """Mock evaluator — produces the 3-axis score + key moments."""
    turn_count = len([t for t in s.turns if t["role"] == "user"])
    deviation_pct = s.deviation_count / max(turn_count, 1)

    legal_soundness = max(40, 90 - (s.deviation_count * 8))
    creativity = min(95, 60 + (s.deviation_count * 12))
    strategic = 75 if deviation_pct < 0.4 else 55

    # Tag key moments from the session
    moments = []
    user_turns = [(i, t) for i, t in enumerate(s.turns) if t["role"] == "user"]

    if user_turns:
        best_idx, best_turn = user_turns[0]
        moments.append(KeyMoment(
            turn=best_idx + 1,
            label="best_move",
            user_text=best_turn["text"],
            commentary="Strong opening framing — you anchored the constitutional claim immediately, which constrained the Court's ability to dodge the 14th Amendment question.",
        ))

    deviations = [(i, t) for i, t in enumerate(s.turns) if t["role"] == "user" and t.get("deviation")]
    if deviations:
        worst_idx, worst_turn = deviations[-1]
        moments.append(KeyMoment(
            turn=worst_idx + 1,
            label="deviation_point",
            user_text=worst_turn["text"],
            commentary="This diverged from the historical record. The real Marshall grounded his rebuttal in the equal protection clause explicitly — your framing left the doctrinal hook implicit, which Frankfurter would have exploited.",
        ))

    if len(user_turns) >= 2:
        moments.append(KeyMoment(
            turn=user_turns[-1][0] + 1,
            label="worst_move",
            user_text=user_turns[-1][1]["text"],
            commentary="Closing too early without addressing the DC schools counterargument. Frankfurter flagged it — leaving it unanswered risks looking like you have no answer.",
        ))

    return {
        "legal_soundness": legal_soundness,
        "strategic_effectiveness": strategic,
        "creativity": creativity,
        "key_moments": moments,
    }


# ── Rendering ──────────────────────────────────────────────────────────────────

W = 70

def hr(char="─"):
    print(char * W)

def print_state_banner(s: SessionState):
    print()
    hr("═")
    print(f"  STATE: {s.state.name}   |   Session #{s.session_id}   |   Turn {len([t for t in s.turns if t['role'] == 'user'])}")
    if s.state == State.IN_SESSION:
        print(f"  Deviations so far: {s.deviation_count}  |  Key moments flagged: {len(s.key_moments)}")
    hr("═")
    print()

def wrap(text, indent=0):
    prefix = " " * indent
    for line in fill(text, width=W - indent, initial_indent=prefix, subsequent_indent=prefix).split("\n"):
        print(line)

def print_turn_log(s: SessionState):
    print()
    hr()
    print("  TURN LOG")
    hr()
    for i, t in enumerate(s.turns, 1):
        tag = "[DEV]" if t.get("deviation") else "     "
        role_label = "YOU" if t["role"] == "user" else "OPP"
        print(f"  {i:02d}. [{role_label}] {tag}  ", end="")
        wrap(t["text"][:80] + ("…" if len(t["text"]) > 80 else ""), indent=13)
    print()

def print_score(score: dict):
    print()
    hr("═")
    print("  END-OF-SESSION SCORECARD")
    hr("═")
    print(f"  Legal Soundness         {score['legal_soundness']:>3}/100")
    print(f"  Strategic Effectiveness {score['strategic_effectiveness']:>3}/100")
    print(f"  Creativity              {score['creativity']:>3}/100")
    hr()
    avg = (score["legal_soundness"] + score["strategic_effectiveness"] + score["creativity"]) // 3
    print(f"  Overall                 {avg:>3}/100")
    hr("═")
    print()
    print(f"  Key moments ({len(score['key_moments'])} flagged — type 'review N' to expand):")
    print()
    for i, m in enumerate(score["key_moments"], 1):
        badge = {"best_move": "★ BEST", "worst_move": "✗ WORST", "deviation_point": "△ DEVIATION"}[m.label]
        print(f"    [{i}] Turn {m.turn}  {badge}")
        wrap(m.user_text[:60] + ("…" if len(m.user_text) > 60 else ""), indent=8)
    print()

def print_review(moment: KeyMoment):
    print()
    hr("═")
    badge = {"best_move": "★ BEST MOVE", "worst_move": "✗ WORST MOVE", "deviation_point": "△ DEVIATION POINT"}[moment.label]
    print(f"  REVIEW — {badge} (Turn {moment.turn})")
    hr("═")
    print()
    print("  Your argument:")
    wrap(moment.user_text, indent=4)
    print()
    print("  Evaluator commentary:")
    wrap(moment.commentary, indent=4)
    print()


# ── Command Dispatch ───────────────────────────────────────────────────────────

def cmd_start(s: SessionState, case_id: str):
    if case_id not in CASES:
        print(f"  Unknown case. Available: {', '.join(CASES.keys())}")
        return
    s.case_id = case_id
    s.session_id += 1
    s.turns = []
    s.deviation_count = 0
    s.key_moments = []
    s.score = {}
    s.reviewing_moment = None
    s.state = State.IN_SESSION
    case = CASES[case_id]
    print()
    hr("═")
    print(f"  CASE: {case['title']}")
    print(f"  You are: {case['user_role']}")
    print(f"  Opposing: {case['opposing_role']}")
    hr()
    wrap(case["context"], indent=2)
    hr("═")
    print()
    # First opponent line
    first = OPPONENT_SCRIPT[0]["text"]
    s.turns.append({"role": "opponent", "text": first})
    print("  [OPPONENT]")
    wrap(first, indent=4)
    print()


def cmd_move(s: SessionState, text: str):
    if s.state != State.IN_SESSION:
        print(f"  Can't submit a move in state {s.state.name}.")
        return

    turn_index = len([t for t in s.turns if t["role"] == "user"])
    deviation = detect_deviation(text, turn_index)
    if deviation:
        s.deviation_count += 1

    s.turns.append({"role": "user", "text": text, "deviation": deviation})

    if deviation:
        print("  (( your argument diverges from the historical path ))")
    else:
        print("  (( following historical playbook ))")

    # Pick next opponent line
    opponent_turn_index = len([t for t in s.turns if t["role"] == "opponent"])
    if opponent_turn_index < len(OPPONENT_SCRIPT):
        opp = OPPONENT_SCRIPT[opponent_turn_index]
        s.turns.append({"role": "opponent", "text": opp["text"]})
        print()
        print("  [OPPONENT]")
        wrap(opp["text"], indent=4)
        print()
        if opp["closes"]:
            s.state = State.SESSION_END
            print("  — Session closing. Type 'score' to evaluate. —")
    else:
        s.state = State.SESSION_END
        print()
        print("  [OPPONENT] The Court thanks you. We'll take the matter under advisement.")
        s.turns.append({"role": "opponent", "text": "The Court thanks you. We'll take the matter under advisement."})
        print()
        print("  — Session closing. Type 'score' to evaluate. —")


def cmd_score(s: SessionState):
    if s.state == State.SCORED:
        # Already scored — just reprint; don't re-evaluate or re-save.
        print_score(s.score)
        return
    if s.state != State.SESSION_END:
        print(f"  Session not ended yet (state: {s.state.name}). Keep arguing.")
        return
    s.state = State.EVALUATING
    print()
    print("  [ Evaluator reading session transcript… ]")
    result = evaluate_session(s)
    s.score = result
    s.state = State.SCORED
    print_score(s.score)
    try:
        path = save_session(s)
        print(f"  [ Session saved → {path} ]")
        summary = format_history_summary(s.case_id)
        if summary:
            print()
            print(summary)
    except OSError as e:
        print(f"  [ Warning: could not save session — {e} ]")


def cmd_review(s: SessionState, index: int):
    if s.state != State.SCORED:
        print("  Score the session first (type 'score').")
        return
    moments = s.score.get("key_moments", [])
    if index < 1 or index > len(moments):
        print(f"  Invalid moment index. Choose 1–{len(moments)}.")
        return
    s.reviewing_moment = index - 1
    s.state = State.REVIEW
    print_review(moments[s.reviewing_moment])


def cmd_back(s: SessionState):
    if s.state != State.REVIEW:
        print(f"  Nothing to go back from (state: {s.state.name}).")
        return
    s.state = State.SCORED
    print()
    print("  Back to scorecard. Type 'review N' to expand another moment, or 'start brown' to replay.")
    print_score(s.score)


def cmd_replay(s: SessionState):
    """Start a new Session on the same Case."""
    if s.state not in (State.SCORED, State.REVIEW, State.SESSION_END):
        print("  Finish the current session first.")
        return
    case_id = s.case_id
    cmd_start(s, case_id)


def print_help():
    print()
    hr()
    print("  COMMANDS")
    hr()
    print("  start <case>     — begin a session (case: 'brown')")
    print("  > <text>         — submit your Move (argument)")
    print("  score            — evaluate the session (after it ends)")
    print("  review <N>       — expand key moment N")
    print("  back             — return to scorecard from review")
    print("  replay           — new session on same case")
    print("  log              — show full turn log")
    print("  state            — print current state")
    print("  help             — this screen")
    print("  quit             — exit")
    hr()
    print()


# ── REPL ───────────────────────────────────────────────────────────────────────

def repl():
    s = SessionState()
    os.system("clear")
    print()
    hr("═")
    print("  COUNCIL — Session State Machine Prototype  [THROWAWAY]")
    print("  Question: does Move → Score → Review flow feel right?")
    hr("═")
    print_help()

    while True:
        print_state_banner(s)
        try:
            raw = input("  » ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            sys.exit(0)

        if not raw:
            continue

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "quit":
            print("  Exiting.")
            sys.exit(0)
        elif cmd == "help":
            print_help()
        elif cmd == "start":
            cmd_start(s, arg or "brown")
        elif cmd == ">":
            if not arg:
                print("  Provide your argument after '>'. Example:  > The 14th Amendment prohibits racial classification.")
            else:
                cmd_move(s, arg)
        elif cmd == "score":
            cmd_score(s)
        elif cmd == "review":
            try:
                cmd_review(s, int(arg))
            except ValueError:
                print("  Usage: review <number>")
        elif cmd == "back":
            cmd_back(s)
        elif cmd == "replay":
            cmd_replay(s)
        elif cmd == "log":
            print_turn_log(s)
        elif cmd == "state":
            print(f"  State: {s.state.name}")
        else:
            print(f"  Unknown command '{cmd}'. Type 'help'.")


if __name__ == "__main__":
    repl()
