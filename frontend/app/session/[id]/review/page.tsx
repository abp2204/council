"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

interface KeyMoment {
  turn: number;
  label: string;
  user_text: string;
  commentary: string;
}

interface Score {
  legal_soundness: number;
  strategic_effectiveness: number;
  creativity: number;
  key_moments: KeyMoment[];
}

const MOMENT_CONFIG: Record<string, { label: string; color: string; glow: string; border: string }> = {
  best_move: {
    label: "Best Move",
    color: "#6ee7b7",
    glow: "rgba(110, 231, 183, 0.1)",
    border: "rgba(110, 231, 183, 0.18)",
  },
  worst_move: {
    label: "Weakest Move",
    color: "#fca5a5",
    glow: "rgba(252, 165, 165, 0.1)",
    border: "rgba(252, 165, 165, 0.18)",
  },
  deviation_point: {
    label: "Deviation",
    color: "var(--gold-glow)",
    glow: "rgba(212, 175, 55, 0.1)",
    border: "rgba(212, 175, 55, 0.28)",
  },
};

/* ── Animated circular score ring ── */
function ScoreRing({
  value,
  color,
  delay = 0.4,
}: {
  value: number;
  color: string;
  delay?: number;
}) {
  const r = 90;
  const cx = 100;
  const cy = 100;
  const circumference = 2 * Math.PI * r;
  const targetOffset = circumference * (1 - value / 100);

  return (
    <svg
      width="200"
      height="200"
      viewBox="0 0 200 200"
      style={{ overflow: "visible" }}
    >
      {/* Outer decorative ring */}
      <circle
        cx={cx} cy={cy} r={r + 12}
        fill="none"
        stroke="rgba(212,175,55,0.05)"
        strokeWidth="1"
      />
      {/* Secondary outer ring */}
      <circle
        cx={cx} cy={cy} r={r + 6}
        fill="none"
        stroke="rgba(212,175,55,0.03)"
        strokeWidth="0.5"
      />
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke="rgba(255,255,255,0.04)"
        strokeWidth="5"
      />
      {/* Animated fill */}
      <motion.circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth="5"
        strokeLinecap="butt"
        strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: targetOffset }}
        transition={{ delay, duration: 1.5, ease: EASE }}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ filter: `drop-shadow(0 0 10px ${color}55)` }}
      />
      {/* Inner glow */}
      <circle
        cx={cx} cy={cy} r={r - 15}
        fill="rgba(212,175,55,0.02)"
      />
    </svg>
  );
}

/* ── Metric score bar ── */
function ScoreBar({
  label,
  value,
  delay,
}: {
  label: string;
  value: number;
  delay: number;
}) {
  const color =
    value >= 80 ? "#6ee7b7"
    : value >= 60 ? "var(--gold-glow)"
    : "#fca5a5";

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.55, ease: EASE }}
    >
      <div className="flex justify-between items-baseline mb-2">
        <span
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.6rem",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "var(--ivory-dim)",
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "0.72rem",
            color,
          }}
        >
          {value}
          <span style={{ color: "rgba(212,175,55,0.35)", fontSize: "0.58rem" }}>
            /100
          </span>
        </span>
      </div>

      <div className="score-bar-track">
        <motion.div
          className="score-bar-fill"
          style={{ background: `linear-gradient(to right, ${color}88, ${color})`, boxShadow: `0 0 6px ${color}55` }}
          initial={{ width: "0%" }}
          animate={{ width: `${value}%` }}
          transition={{ delay: delay + 0.08, duration: 1.1, ease: EASE }}
        />
      </div>
    </motion.div>
  );
}

export default function Review() {
  const { id: sessionId } = useParams<{ id: string }>();
  const [score, setScore]     = useState<Score | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [caseTitle, setCaseTitle] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem(`council_score_${sessionId}`);
    if (cached) setScore(JSON.parse(cached));
    const title = sessionStorage.getItem(`council_case_title_${sessionId}`);
    if (title) setCaseTitle(title);
  }, [sessionId]);

  if (!score) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-28 text-center">
        <div
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.58rem",
            letterSpacing: "0.24em",
            textTransform: "uppercase",
            color: "rgba(212,175,55,0.35)",
          }}
        >
          Awaiting judgment…
        </div>
      </main>
    );
  }

  const overall = Math.round(
    (score.legal_soundness + score.strategic_effectiveness + score.creativity) / 3
  );

  const overallColor =
    overall >= 80 ? "#6ee7b7"
    : overall >= 60 ? "var(--gold-glow)"
    : "#fca5a5";

  return (
    <main className="max-w-3xl mx-auto px-6 py-12 pb-28">

      {/* ── Nav ── */}
      <div className="flex items-center justify-between mb-14">
        <div className="flex flex-col gap-1.5">
          <span
            style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "0.6rem",
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: "var(--gold-glow)",
            }}
          >
            Session Review
          </span>
          {caseTitle && (
            <span className="session-case-title">{caseTitle}</span>
          )}
        </div>
        <a
          href="/"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.6rem",
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: "rgba(212,175,55,0.38)",
            textDecoration: "none",
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "var(--gold-glow)")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "rgba(212,175,55,0.38)")}
        >
          ← Back to Cases
        </a>
      </div>

      {/* ── Judgment header ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, ease: EASE }}
        className="text-center mb-14"
      >
        {/* Arch ornament */}
        <svg width="280" height="130" viewBox="0 0 120 56" fill="none" className="mx-auto mb-6" aria-hidden>
          <path
            d="M8 56 C8 22, 44 4, 60 4 C76 4, 112 22, 112 56"
            stroke="rgba(212,175,55,0.38)" strokeWidth="1.5" fill="none"
          />
          <path
            d="M22 56 C22 30, 46 14, 60 14 C74 14, 98 30, 98 56"
            stroke="rgba(212,175,55,0.20)" strokeWidth="1" fill="none"
          />
          <polygon points="60,0 63,7 60,14 57,7" fill="rgba(212,175,55,0.82)" />
        </svg>

        <p
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.56rem",
            letterSpacing: "0.36em",
            textTransform: "uppercase",
            color: "var(--gold-dim)",
            marginBottom: "20px",
          }}
        >
          Judgment Rendered
        </p>

        {/* Score ring */}
        <div className="relative inline-flex items-center justify-center">
          <ScoreRing value={overall} color={overallColor} delay={0.3} />

          <div className="absolute flex flex-col items-center justify-center">
            <motion.span
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6, duration: 0.5, ease: EASE }}
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "3.5rem",
                fontWeight: 600,
                lineHeight: 1,
                color: overallColor,
                textShadow: `0 0 40px ${overallColor}40`,
              }}
            >
              {overall}
            </motion.span>
            <span
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.5rem",
                letterSpacing: "0.22em",
                textTransform: "uppercase",
                color: "rgba(212,175,55,0.42)",
                marginTop: "4px",
              }}
            >
              Overall
            </span>
          </div>
        </div>

        <div className="gold-rule mt-8 max-w-[160px] mx-auto" />
      </motion.div>

      {/* ── Score breakdown ── */}
      <motion.section
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.32, duration: 0.55, ease: EASE }}
        className="gold-border pillar-shadow mb-5"
        style={{
          background: "linear-gradient(155deg, #201810 0%, var(--walnut-deep) 100%)",
          padding: "28px 32px",
        }}
      >
        <h2
          className="mb-7"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.58rem",
            letterSpacing: "0.26em",
            textTransform: "uppercase",
            color: "var(--gold-glow)",
          }}
        >
          Scoring Breakdown
        </h2>

        <div className="space-y-6">
          <ScoreBar label="Legal Soundness"         value={score.legal_soundness}        delay={0.45} />
          <ScoreBar label="Strategic Effectiveness" value={score.strategic_effectiveness} delay={0.55} />
          <ScoreBar label="Creativity"              value={score.creativity}              delay={0.65} />
        </div>
      </motion.section>

      {/* ── Key moments ── */}
      {score.key_moments.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.48, duration: 0.55, ease: EASE }}
          className="gold-border pillar-shadow"
          style={{
            background: "linear-gradient(155deg, #201810 0%, var(--walnut-deep) 100%)",
            padding: "28px 32px",
          }}
        >
          <h2
            className="mb-7"
            style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "0.58rem",
              letterSpacing: "0.26em",
              textTransform: "uppercase",
              color: "var(--gold-glow)",
            }}
          >
            Key Moments
          </h2>

          <div className="space-y-3">
            {score.key_moments.map((km, i) => {
              const cfg = MOMENT_CONFIG[km.label] ?? {
                label: km.label,
                color: "var(--ivory-dim)",
                glow: "transparent",
                border: "rgba(212,175,55,0.2)",
              };
              const isOpen = expanded === i;

              return (
                <div
                  key={i}
                  style={{
                    border: `1px solid ${cfg.border}`,
                    overflow: "hidden",
                  }}
                >
                  {/* Accordion header */}
                  <button
                    className="w-full text-left flex items-center justify-between transition-all"
                    style={{
                      padding: "14px 20px",
                      background: isOpen ? cfg.glow : "transparent",
                    }}
                    onClick={() => setExpanded(isOpen ? null : i)}
                  >
                    <div className="min-w-0 flex-1 pr-4">
                      <span
                        className="block mb-1"
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.54rem",
                          letterSpacing: "0.22em",
                          textTransform: "uppercase",
                          color: cfg.color,
                        }}
                      >
                        {cfg.label} — Turn {km.turn}
                      </span>
                      <p
                        className="text-sm truncate"
                        style={{
                          fontFamily: "'Playfair Display', serif",
                          color: "var(--ivory)",
                          opacity: 0.85,
                        }}
                      >
                        {km.user_text}
                      </p>
                    </div>

                    <span
                      className="shrink-0 transition-transform"
                      style={{
                        color: cfg.color,
                        transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                        fontSize: "10px",
                      }}
                    >
                      ▾
                    </span>
                  </button>

                  {/* Accordion body */}
                  {isOpen && (
                    <div
                      className="accordion-content"
                      style={{
                        padding: "18px 20px 20px",
                        borderTop: `1px solid ${cfg.border}`,
                        background: cfg.glow,
                      }}
                    >
                      <p
                        className="mb-0.5"
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.52rem",
                          letterSpacing: "0.2em",
                          textTransform: "uppercase",
                          color: "rgba(212,175,55,0.38)",
                        }}
                      >
                        Your Argument
                      </p>
                      <p
                        className="text-sm italic mb-5"
                        style={{
                          fontFamily: "'Playfair Display', serif",
                          color: "var(--ivory-dim)",
                          lineHeight: "1.8",
                          marginTop: "6px",
                        }}
                      >
                        "{km.user_text}"
                      </p>

                      <p
                        className="mb-0.5"
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.52rem",
                          letterSpacing: "0.2em",
                          textTransform: "uppercase",
                          color: "rgba(212,175,55,0.38)",
                        }}
                      >
                        Evaluator Commentary
                      </p>
                      <p
                        className="text-sm leading-[1.85]"
                        style={{
                          fontFamily: "'Playfair Display', serif",
                          color: "var(--ivory)",
                          marginTop: "6px",
                        }}
                      >
                        {km.commentary}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </motion.section>
      )}

      {/* ── Call to action ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.75, duration: 0.55, ease: EASE }}
        className="flex items-center justify-center gap-6 mt-10"
      >
        <a
          href="/"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.62rem",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            padding: "12px 32px",
            border: "1px solid var(--gold-glow)",
            color: "var(--charcoal)",
            background: "var(--gold-glow)",
            textDecoration: "none",
            transition: "background 0.2s",
            display: "inline-block",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "var(--gold-bright)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "var(--gold-glow)";
          }}
        >
          Argue Again →
        </a>
        <a
          href="/"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.62rem",
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            padding: "12px 32px",
            border: "1px solid rgba(212,175,55,0.38)",
            color: "var(--gold-glow)",
            background: "rgba(212,175,55,0.04)",
            textDecoration: "none",
            transition: "background 0.2s, border-color 0.2s",
            display: "inline-block",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "rgba(212,175,55,0.10)";
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(212,175,55,0.60)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.background = "rgba(212,175,55,0.04)";
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(212,175,55,0.38)";
          }}
        >
          Browse Cases
        </a>
      </motion.div>
    </main>
  );
}
