"""
COUNCIL — SessionEngine test suite (Issue #15)

Ports all 19 parameterized test sessions from Groups A–F of the prototype
test runner. All tests run with MockOpposingRole and MockEvaluator injected,
so zero API calls are made.
"""

import pytest

from case_library import load_case
from session_engine import (
    InvalidStateError,
    MockEvaluator,
    MockOpposingRole,
    Score,
    SessionEngine,
    State,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def brown_case() -> dict:
    return load_case("brown")


@pytest.fixture(scope="module")
def mock_probes(brown_case) -> list[str]:
    return brown_case["opposing_role"]["mock_probes"]


@pytest.fixture(scope="module")
def mock_close(brown_case) -> str:
    return brown_case["opposing_role"]["mock_close"]


def make_engine(mock_probes: list[str], mock_close: str) -> SessionEngine:
    def factory(case: dict) -> MockOpposingRole:
        return MockOpposingRole(
            mock_probes=mock_probes,
            mock_close=mock_close,
        )

    return SessionEngine(
        opposing_role_factory=factory,
        evaluator=MockEvaluator(),
    )


def run_session(moves: list[str], mock_probes: list[str], mock_close: str) -> Score:
    """
    Full session: create → submit all moves → evaluate.
    Forces SESSION_END after all moves if the session hasn't closed yet.
    Returns the Score.
    """
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")

    for move in moves:
        s = engine._sessions[session_id]
        if s.state != State.IN_SESSION:
            break
        engine.submit_move(session_id, move)

    s = engine._sessions[session_id]
    if s.state == State.IN_SESSION:
        s.state = State.SESSION_END

    return engine.evaluate(session_id)


# ── Test cases (Groups A–F) ───────────────────────────────────────────────────

GROUP_A = [
    pytest.param(
        [
            "the constitution does not permit racial classification in any form",
            "plessy was wrongly decided and must be overruled by this court",
            "the framers intended to end racial caste and that intent governs",
        ],
        id="A1-zero-deviations",
    ),
    pytest.param(
        [
            "separate but equal is a legal fiction that has never reflected reality",
            "plessy was wrongly decided and the equal protection clause requires us to say so",
            "the framers intended to eliminate the racial caste system that the amendment was designed to dismantle",
        ],
        id="A2-one-deviation",
    ),
    pytest.param(
        [
            "the psychological harm inflicted by segregation is indistinguishable from a state-sanctioned badge of inferiority",
            "stare decisis cannot shield a decision that was constitutionally infirm from the moment it was handed down",
            "the framers intended to end racial caste — their intent is the controlling principle here",
        ],
        id="A3-two-deviations",
    ),
    pytest.param(
        [
            "justice frankfurter, the harm here is not psychological in the narrow sense — it is civic. Segregation tells a child they are not a full citizen.",
            "overruling plessy is not judicial activism — it is the court fulfilling the promise of the reconstruction amendments after ninety years of delay",
            "the dc argument proves too much. If inconsistent practice at ratification fixed constitutional meaning, the amendment could never have abolished slavery either.",
        ],
        id="A4-three-deviations",
    ),
]

GROUP_B = [
    pytest.param(
        ["Unconstitutional.", "Overrule.", "Equality."],
        id="B1-one-word-arguments",
    ),
    pytest.param(
        [
            "The Fourteenth Amendment's equal protection clause was ratified in 1868 with a singular purpose: to dismantle the legal architecture of racial hierarchy that had defined American law since the founding. When a state maintains two parallel school systems — one for white children and one for Black children — it is not making a neutral administrative choice. It is encoding a message of subordination into the law itself. The psychological evidence confirms what common sense already knows: children who attend segregated schools understand, from the very fact of segregation, that their government regards them as inferior. That is not education. That is state-sponsored stigma.",
            "Plessy v. Ferguson was decided in 1896 by a court that was either unwilling or unable to see what the Fourteenth Amendment plainly required. The separate but equal doctrine was not a faithful reading of the Constitution — it was a capitulation to the politics of the Reconstruction's collapse. This Court has corrected its own errors before and has the full authority — indeed the obligation — to do so again. The question is not whether Plessy can be defended on its own terms. It cannot. The question is whether this Court will continue to let a defective precedent govern the lives of millions of American schoolchildren.",
            "The argument from the District of Columbia proves far too much. It assumes that congressional practice at the moment of ratification defines the outer limit of a constitutional guarantee. But that cannot be right. If post-enactment legislative behavior controls, then no constitutional provision could ever be applied more broadly than it was on the day of its passage — which would make constitutional interpretation impossible and constitutional growth unthinkable. The Fourteenth Amendment was written as a permanent guarantee of equality before the law. The fact that Congress fell short of that guarantee in its own backyard does not diminish the guarantee — it underscores how urgently this Court must enforce it.",
        ],
        id="B2-very-long-arguments",
    ),
    pytest.param(
        [
            "Any racial classification maintained by a state violates the Fourteenth Amendment.",
            "Plessy was wrongly decided. The separate but equal doctrine has no basis in the equal protection clause and this Court should say so explicitly today.",
            "The DC schools argument misunderstands the relationship between legislative practice and constitutional meaning. The Fourteenth Amendment created a floor of equality that Congress itself was obligated to honor — and when Congress fell short, that failure was a constitutional violation, not a definition of the Amendment's scope. The framers intended to abolish racial caste; they did not intend to grandfather in every practice that happened to exist in 1868.",
        ],
        id="B3-escalating-length",
    ),
]

GROUP_C = [
    pytest.param(
        [
            "Justice Frankfurter, you are right that psychological harm alone may not be sufficient. But segregation is not before this Court merely because it causes harm — it is before this Court because it is a classification by race, and the Fourteenth Amendment makes all such classifications constitutionally suspect.",
            "I will grant that Plessy has been on the books for fifty-six years. But plessy was wrongly decided, and longevity does not cure a constitutional error. This Court corrected Lochner. It can correct Plessy.",
            "The DC schools point is a fair one. But the framers intended the amendment to be a living guarantee of equality, not a snapshot of 1868 congressional practice.",
        ],
        id="C1-concede-then-pivot",
    ),
    pytest.param(
        [
            "The question is not whether every racial classification is per se unconstitutional — the question is whether this one is. And the answer is plainly yes, because its only purpose and its only effect is to mark Black children as unfit to share a schoolroom with white children.",
            "The question is not what authority this Court has to overrule Plessy — the question is whether this Court has the authority to continue enforcing it. And I submit it does not.",
            "The question is not what Congress did in DC in 1868 — the question is what the Fourteenth Amendment requires of every state government today. And the answer is equality.",
        ],
        id="C2-question-the-question",
    ),
    pytest.param(
        [
            "The Fifth Amendment's due process clause explicitly prohibits racial segregation in public schools — this Court held as much in Marbury v. Madison.",
            "Plessy v. Ferguson was decided in 1920 and has been widely criticized by every subsequent court. The Brown precedent itself supports our position.",
            "The framers of the Fourteenth Amendment specifically debated school segregation in the congressional record and voted to prohibit it by a margin of thirty to two.",
        ],
        id="C3-factually-wrong-arguments",
    ),
    pytest.param(
        [
            "These are children. They go to school every morning knowing that their government has decided they are not good enough to sit beside a white child. No legal doctrine should protect that.",
            "Thurgood Marshall has spent his career watching Black Americans denied the education that would let them compete as equals. This Court has the power to end that today. The question is whether it will.",
            "History is watching. The children of this generation will judge this Court not by its adherence to Plessy but by whether it had the courage to read the Constitution as it was written.",
        ],
        id="C4-emotional-appeals-no-doctrine",
    ),
    pytest.param(
        [
            "Under strict scrutiny analysis, the state bears the burden of demonstrating a compelling governmental interest and that its chosen means are narrowly tailored thereto, which burden it cannot meet.",
            "The doctrine of stare decisis, while a cornerstone of jurisprudential stability, must yield to the constitutional imperative of the equal protection clause as construed pursuant to its original public meaning at the time of ratification.",
            "The historical record adduced by respondent is unavailing inasmuch as contemporaneous legislative practice cannot be dispositive of constitutional meaning where such practice is itself constitutionally infirm.",
        ],
        id="C5-pure-jargon-no-substance",
    ),
]

GROUP_D = [
    pytest.param(
        [
            "With the greatest respect to the Court and to the question posed, I would submit, if it please the Court, that the Fourteenth Amendment was designed to eliminate racial classifications of exactly this kind.",
            "Your Honor raises a most important question, and I am grateful for it. If I may, I would simply note that Plessy was wrongly decided, though I recognize that conclusion is one the Court must reach on its own terms.",
            "I take the Court's point about the DC schools seriously, and I do not wish to be dismissive of it. But I would gently suggest that the framers' intent was broader than any single practice at the time of ratification.",
        ],
        id="D1-deferential-tone",
    ),
    pytest.param(
        [
            "Any state that maintains segregated schools is violating the Constitution, full stop. There is no other reading of the Fourteenth Amendment that survives honest scrutiny.",
            "Plessy is indefensible. It was wrong in 1896 and it is wrong today. This Court should not waste another sentence defending it.",
            "The DC argument is a red herring and I won't dignify it with more than this: unconstitutional practice at ratification does not launder itself into constitutional permission.",
        ],
        id="D2-confrontational-tone",
    ),
    pytest.param(
        [
            "May I ask the Court to consider: if a state law said explicitly that Black children may not attend white schools, would there be any doubt that it violates the Fourteenth Amendment? And if not, why does it matter that the state has arranged the same outcome through separate facilities?",
            "What would it mean to follow Plessy faithfully? It would mean telling millions of Black schoolchildren that the Constitution permits their government to mark them as inferior. Is that really what this Court intends?",
            "If congressional practice at ratification defines the Amendment's scope, then what work does the Amendment do at all? Would it not have been simpler to simply codify the status quo?",
        ],
        id="D3-socratic-question-heavy",
    ),
]

GROUP_E = [
    pytest.param(
        [
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
            "Racial segregation in public schools violates the Fourteenth Amendment's equal protection clause.",
        ],
        id="E1-repeat-same-argument",
    ),
    pytest.param(
        [
            "Under the common law of contracts, the state's obligation to provide schooling constitutes an offer that all children may accept, and denying that offer on racial grounds constitutes a breach.",
            "The consideration for a child's attendance at a public school is their status as a citizen of the state. Denying that consideration based on race renders the contract void for unconscionability.",
            "Specific performance is the appropriate remedy — the Court should order the state to perform its contractual obligation to admit all students on equal terms.",
        ],
        id="E2-wrong-area-of-law",
    ),
    pytest.param(
        [
            "Plessy was correctly decided. Separate but equal is a permissible accommodation of social difference and the states retain authority to organize their own school systems.",
            "This Court should defer to the democratic choices of the states. If the people of Kansas wish to maintain separate schools, the Fourteenth Amendment does not prohibit it.",
            "The DC schools argument is dispositive. The Congress that ratified the Fourteenth Amendment continued to fund segregated schools in DC — proof that they did not intend to prohibit state-maintained segregation.",
        ],
        id="E3-argue-for-other-side",
    ),
    pytest.param(
        [
            "La segregación racial en las escuelas públicas viola la Decimocuarta Enmienda de la Constitución de los Estados Unidos.",
            "Plessy contra Ferguson fue decidido incorrectamente y debe ser revocado por este tribunal.",
            "Los fundadores de la Decimocuarta Enmienda tenían la intención de abolir el sistema de castas racial en todas sus formas.",
        ],
        id="E4-non-english-arguments",
    ),
    pytest.param(
        ["...", "?", "No."],
        id="E5-single-char-arguments",
    ),
]

GROUP_F = [
    pytest.param(
        [
            "The evidence before this Court includes the work of Dr. Kenneth Clark, whose studies show that Black children in segregated schools internalize a sense of inferiority. That is not conjecture — it is documented psychological harm caused directly by state action.",
            "This Court has previously held that separate facilities are inherently unequal in the context of graduate education — McLaurin and Sweatt. The principle does not stop at graduate school. It applies wherever the state segregates.",
            "The DC argument only reinforces our position: if Congress itself violated the Fourteenth Amendment by funding segregated schools, this Court should say so — and say so clearly — rather than use that violation to justify more of the same.",
        ],
        id="F1-cite-social-science-evidence",
    ),
    pytest.param(
        [
            "The Fourteenth Amendment prohibits racial classifications by the state. Segregated schools are a racial classification. Therefore they are prohibited.",
            "Plessy tried to escape that logic by inventing the fiction of separate but equal. But the fiction was always a lie — separate has never been equal — and it is time for this Court to say so.",
            "And as for DC: if the Congress that ratified the Amendment violated it, that makes their violation a constitutional wrong, not a constitutional permission. The Amendment's text controls, not the practice of those who failed to live up to it.",
        ],
        id="F2-build-incrementally",
    ),
    pytest.param(
        [
            "Segregation is bad and the Constitution says so.",
            "Well, Plessy was a mistake and we think you should fix it because the equal protection clause does not permit this kind of treatment of people.",
            "The framers intended the Fourteenth Amendment to be a guarantee of equal citizenship in perpetuity — not a baseline frozen at the practices of 1868. The DC schools were an inconsistency, not a definition. This Court should enforce the amendment as written and hold that racially segregated public schools are unconstitutional.",
        ],
        id="F3-strong-close-weak-open",
    ),
]


# ── Parametrized tests ────────────────────────────────────────────────────────

@pytest.mark.parametrize("moves", GROUP_A)
def test_group_a_deviation_sweep(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)
    assert isinstance(score.legal_soundness, int)
    assert isinstance(score.strategic_effectiveness, int)
    assert isinstance(score.creativity, int)


@pytest.mark.parametrize("moves", GROUP_B)
def test_group_b_argument_length(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)


@pytest.mark.parametrize("moves", GROUP_C)
def test_group_c_argument_quality(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)


@pytest.mark.parametrize("moves", GROUP_D)
def test_group_d_tone_extremes(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)


@pytest.mark.parametrize("moves", GROUP_E)
def test_group_e_edge_cases(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)


@pytest.mark.parametrize("moves", GROUP_F)
def test_group_f_realistic_variation(moves, mock_probes, mock_close):
    score = run_session(moves, mock_probes, mock_close)
    assert isinstance(score, Score)


# ── State machine enforcement tests ──────────────────────────────────────────

def test_evaluate_on_in_session_raises(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    with pytest.raises(InvalidStateError, match="IN_SESSION"):
        engine.evaluate(session_id)


def test_submit_move_after_session_end_raises(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    engine._sessions[session_id].state = State.SESSION_END
    with pytest.raises(InvalidStateError, match="SESSION_END"):
        engine.submit_move(session_id, "a move")


def test_review_before_scored_raises(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    engine._sessions[session_id].state = State.SESSION_END
    engine.evaluate(session_id)
    engine._sessions[session_id].state = State.IN_SESSION
    with pytest.raises(InvalidStateError, match="IN_SESSION"):
        engine.review(session_id, 0)


def test_review_requires_scored_or_review_state(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    engine.submit_move(session_id, "the constitution does not permit racial classification")
    engine.submit_move(session_id, "plessy was wrongly decided")
    engine.submit_move(session_id, "the framers intended to end racial caste")
    s = engine._sessions[session_id]
    if s.state == State.IN_SESSION:
        s.state = State.SESSION_END
    score = engine.evaluate(session_id)
    assert len(score.key_moments) > 0
    moment = engine.review(session_id, 0)
    assert moment is not None
    assert engine._sessions[session_id].state == State.REVIEW
    moment2 = engine.review(session_id, 0)
    assert moment2 is not None


def test_unknown_session_raises(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    with pytest.raises(KeyError):
        engine.submit_move("nonexistent-id", "text")


def test_create_session_returns_string(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_session_transitions_to_scored_after_evaluate(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    engine._sessions[session_id].state = State.SESSION_END
    engine.evaluate(session_id)
    assert engine._sessions[session_id].state == State.SCORED


def test_full_session_flow_no_api_calls(mock_probes, mock_close):
    """End-to-end session using only mocks."""
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")

    moves = [
        "the constitution does not permit racial classification",
        "plessy was wrongly decided",
        "the framers intended to end racial caste",
    ]
    for move in moves:
        s = engine._sessions[session_id]
        if s.state != State.IN_SESSION:
            break
        engine.submit_move(session_id, move)

    s = engine._sessions[session_id]
    if s.state == State.IN_SESSION:
        s.state = State.SESSION_END

    score = engine.evaluate(session_id)
    assert isinstance(score, Score)
    assert score.legal_soundness == 75
    assert score.strategic_effectiveness == 70
    assert score.creativity == 65

    if score.key_moments:
        moment = engine.review(session_id, 0)
        assert moment.label in ("best_move", "worst_move", "deviation_point")


def test_constructor_raises_if_factory_is_none():
    with pytest.raises(ValueError, match="opposing_role_factory"):
        SessionEngine(opposing_role_factory=None, evaluator=MockEvaluator())


def test_constructor_raises_if_evaluator_is_none():
    def factory(case: dict) -> MockOpposingRole:
        opp = case["opposing_role"]
        return MockOpposingRole(mock_probes=opp["mock_probes"], mock_close=opp["mock_close"])

    with pytest.raises(ValueError, match="evaluator"):
        SessionEngine(opposing_role_factory=factory, evaluator=None)


def test_create_session_invalid_case_id_raises(mock_probes, mock_close):
    engine = make_engine(mock_probes, mock_close)
    with pytest.raises(KeyError):
        engine.create_session("nonexistent-case")


def test_review_empty_key_moments_raises(mock_probes, mock_close):
    """review() with no key moments raises IndexError with a clear message."""
    engine = make_engine(mock_probes, mock_close)
    session_id = engine.create_session("brown")
    engine._sessions[session_id].state = State.SESSION_END

    score = engine.evaluate(session_id)
    score.key_moments.clear()

    with pytest.raises(IndexError, match="no key moments available"):
        engine.review(session_id, 0)


def test_evaluate_rollback_on_exception(mock_probes, mock_close):
    """evaluate() restores SESSION_END state if the evaluator raises."""

    class BrokenEvaluator:
        def evaluate(self, turns, historical_record, case):
            raise RuntimeError("evaluator exploded")

    def factory(case: dict) -> MockOpposingRole:
        return MockOpposingRole(mock_probes=mock_probes, mock_close=mock_close)

    engine = SessionEngine(opposing_role_factory=factory, evaluator=BrokenEvaluator())
    session_id = engine.create_session("brown")
    engine._sessions[session_id].state = State.SESSION_END

    with pytest.raises(RuntimeError, match="evaluator exploded"):
        engine.evaluate(session_id)

    assert engine._sessions[session_id].state == State.SESSION_END


def test_each_session_gets_fresh_opposing_role(mock_probes, mock_close):
    """Two sessions created from the same engine must not share probe state."""
    engine = make_engine(mock_probes, mock_close)
    sid1 = engine.create_session("brown")
    sid2 = engine.create_session("brown")

    role1 = engine._sessions[sid1].opposing_role
    role2 = engine._sessions[sid2].opposing_role
    assert role1 is not role2
