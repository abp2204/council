"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, type Transition } from "framer-motion";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

interface Case {
  id: string;
  title: string;
  proceeding_type: string;
  practice_area: string;
  user_role: string;
}

const containerVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.5 } },
};

const itemTransition: Transition = { duration: 0.65, ease: EASE };
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show:  { opacity: 1, y: 0, transition: itemTransition },
};

function GothicArch() {
  return (
    <svg
      width="440"
      height="200"
      viewBox="0 0 300 140"
      fill="none"
      aria-hidden
      className="mx-auto"
    >
      {/* Outer arch */}
      <path
        d="M16 140 C16 50, 120 6, 150 6 C180 6, 284 50, 284 140"
        stroke="rgba(212,175,55,0.44)"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Mid arch */}
      <path
        d="M40 140 C40 66, 122 28, 150 28 C178 28, 260 66, 260 140"
        stroke="rgba(212,175,55,0.26)"
        strokeWidth="1"
        fill="none"
      />
      {/* Inner arch */}
      <path
        d="M68 140 C68 84, 126 52, 150 52 C174 52, 232 84, 232 140"
        stroke="rgba(212,175,55,0.13)"
        strokeWidth="1"
        fill="none"
      />
      {/* Keystone diamond */}
      <polygon points="150,0 156,11 150,22 144,11" fill="rgba(212,175,55,0.88)" />
      <polygon points="150,3 154,11 150,19 146,11" fill="rgba(212,175,55,0.26)" />
      {/* Keystone ambient glow */}
      <ellipse cx="150" cy="11" rx="14" ry="8" fill="rgba(212,175,55,0.12)" />
      {/* Column shafts */}
      <rect x="13" y="110" width="1.5" height="30" fill="rgba(212,175,55,0.24)" />
      <rect x="286" y="110" width="1.5" height="30" fill="rgba(212,175,55,0.24)" />
      {/* Column capitals */}
      <rect x="8" y="108" width="11" height="2" rx="0.5" fill="rgba(212,175,55,0.20)" />
      <rect x="281" y="108" width="11" height="2" rx="0.5" fill="rgba(212,175,55,0.20)" />
      {/* Column bases */}
      <rect x="8" y="136" width="16" height="4" rx="0.5" fill="rgba(212,175,55,0.28)" />
      <rect x="276" y="136" width="16" height="4" rx="0.5" fill="rgba(212,175,55,0.28)" />
      {/* Tracery horizontal bar */}
      <line
        x1="40" y1="96" x2="260" y2="96"
        stroke="rgba(212,175,55,0.09)"
        strokeWidth="0.5"
        strokeDasharray="6 6"
      />
      {/* Tracery vertical center */}
      <line
        x1="150" y1="22" x2="150" y2="140"
        stroke="rgba(212,175,55,0.06)"
        strokeWidth="0.5"
        strokeDasharray="5 8"
      />
      {/* Tracery side verticals */}
      <line x1="96" y1="96" x2="96" y2="140" stroke="rgba(212,175,55,0.05)" strokeWidth="0.5" />
      <line x1="204" y1="96" x2="204" y2="140" stroke="rgba(212,175,55,0.05)" strokeWidth="0.5" />
    </svg>
  );
}

export default function Lobby() {
  const [cases, setCases]           = useState<Case[]>([]);
  const [loading, setLoading]       = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [starting, setStarting]     = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch("/api/cases")
      .then(async (r) => {
        const text = await r.text();
        if (!r.ok) throw new Error(`http ${r.status}`);
        return JSON.parse(text);
      })
      .then(setCases)
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false));
  }, []);

  async function startSession(c: Case) {
    setStarting(c.id);
    try {
      const r = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: c.id }),
      });
      const raw = await r.text();
      if (!r.ok) throw new Error(`http ${r.status}: ${raw}`);
      const data = JSON.parse(raw);
      sessionStorage.setItem(`council_opening_${data.session_id}`, data.opening ?? "");
      sessionStorage.setItem(`council_case_title_${data.session_id}`, c.title);
      sessionStorage.setItem(`council_case_meta_${data.session_id}`, JSON.stringify({
        practice_area: c.practice_area,
        proceeding_type: c.proceeding_type,
        user_role: c.user_role,
      }));
      router.push(`/session/${data.session_id}`);
    } catch (e) {
      console.error(e);
      setStarting(null);
    }
  }

  return (
    <main className="relative min-h-screen flex flex-col items-center">

      {/* ── Hero ── */}
      <motion.header
        className="w-full max-w-2xl mx-auto px-8 pt-20 pb-16 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.1, ease: EASE }}
      >
        {/* Arch ornament */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.0, ease: EASE }}
        >
          <GothicArch />
        </motion.div>

        {/* Wordmark */}
        <motion.h1
          className="mt-4"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "clamp(3rem, 8vw, 6rem)",
            fontWeight: 600,
            letterSpacing: "0.36em",
            color: "var(--ivory)",
            textShadow: "0 0 100px rgba(212,175,55,0.12)",
            lineHeight: 1,
          }}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.9, ease: EASE }}
        >
          COUNCIL
        </motion.h1>

        {/* Gold rule */}
        <motion.div
          className="gold-rule my-7 max-w-[200px] mx-auto"
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.8, ease: EASE }}
          style={{ transformOrigin: "center" }}
        />

        {/* Sub-tagline */}
        <motion.p
          className="text-base leading-[1.85] italic max-w-sm mx-auto"
          style={{
            fontFamily: "'Playfair Display', serif",
            color: "var(--ivory-dim)",
          }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38, duration: 0.7, ease: EASE }}
        >
          Argue landmark historical cases against AI opponents
          backed by actual court transcripts.
        </motion.p>

        {/* Scoring note */}
        <motion.p
          className="mt-5 tracking-[0.28em] uppercase"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "0.58rem",
            color: "var(--gold-dim)",
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.52, duration: 0.6 }}
        >
          Legal Soundness · Strategy · Creativity
        </motion.p>
      </motion.header>

      {/* ── Case list ── */}
      <section className="w-full max-w-4xl mx-auto px-8 pb-32">

        {/* Section divider */}
        <motion.div
          className="flex items-center gap-5 mb-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.58, duration: 0.5 }}
        >
          <div className="h-px flex-1" style={{ background: "rgba(212,175,55,0.14)" }} />
          <span
            style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "0.55rem",
              letterSpacing: "0.28em",
              textTransform: "uppercase",
              color: "var(--gold-dim)",
            }}
          >
            Select Your Case
          </span>
          <div className="h-px flex-1" style={{ background: "rgba(212,175,55,0.14)" }} />
        </motion.div>

        {/* Loading skeletons */}
        {loading && (
          <div className="case-grid">
            {[...Array(2)].map((_, i) => (
              <div
                key={i}
                className="animate-pulse"
                style={{
                  background: "var(--walnut-panel)",
                  border: "1px solid rgba(212,175,55,0.12)",
                  padding: "28px 32px",
                  minHeight: "160px",
                }}
              >
                <div className="h-2 w-1/4 mb-5 rounded-sm" style={{ background: "rgba(212,175,55,0.07)" }} />
                <div className="h-5 w-2/3 mb-4 rounded-sm" style={{ background: "rgba(255,255,255,0.04)" }} />
                <div className="h-2.5 w-1/3 rounded-sm" style={{ background: "rgba(255,255,255,0.03)" }} />
              </div>
            ))}
          </div>
        )}

        {/* Case cards */}
        {!loading && !fetchError && cases.length > 0 && (
          <motion.ul
            className="case-grid list-none p-0"
            variants={containerVariants}
            initial="hidden"
            animate="show"
          >
            {cases.map((c, idx) => (
              <motion.li key={c.id} variants={itemVariants}>
                <div
                  className="relative group cursor-pointer overflow-hidden gold-border pillar-shadow gold-glow-hover corner-notch"
                  style={{
                    background: "linear-gradient(150deg, #241b12 0%, var(--walnut-deep) 100%)",
                    minHeight: "190px",
                  }}
                  onClick={() => !starting && startSession(c)}
                >
                  {/* Left pillar accent */}
                  <div className="case-card-accent" aria-hidden />

                  {/* Top edge accent */}
                  <div
                    className="absolute top-0 inset-x-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                    style={{ background: "linear-gradient(to right, transparent, rgba(212,175,55,0.38) 40%, rgba(212,175,55,0.38) 60%, transparent)" }}
                    aria-hidden
                  />

                  {/* Case index watermark */}
                  <span className="case-index-num" aria-hidden>
                    {String(idx + 1).padStart(2, "0")}
                  </span>

                  <div className="px-8 py-7 relative z-10">
                    {/* Top meta row */}
                    <div className="flex items-center justify-between mb-4">
                      <span
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.56rem",
                          letterSpacing: "0.26em",
                          textTransform: "uppercase",
                          color: "var(--gold-glow)",
                        }}
                      >
                        {c.practice_area || c.proceeding_type}
                      </span>
                      <span
                        style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: "0.6rem",
                          letterSpacing: "0.08em",
                          color: "rgba(212,175,55,0.28)",
                        }}
                      >
                        case on record
                      </span>
                    </div>

                    {/* Title */}
                    <h2
                      className="mb-5 leading-snug"
                      style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "1.1rem",
                        fontWeight: 500,
                        letterSpacing: "0.04em",
                        color: "var(--ivory)",
                      }}
                    >
                      {c.title}
                    </h2>

                    {/* Role line + CTA */}
                    <div className="flex items-end justify-between gap-4">
                      <div className="flex items-center gap-2.5">
                        <div className="h-px w-7" style={{ background: "rgba(212,175,55,0.28)" }} />
                        <p
                          className="text-sm"
                          style={{
                            fontFamily: "'Playfair Display', serif",
                            color: "var(--ivory-dim)",
                          }}
                        >
                          Arguing as{" "}
                          <span className="not-italic font-medium" style={{ color: "var(--ivory)" }}>
                            {c.user_role}
                          </span>
                        </p>
                      </div>

                      {/* CTA button */}
                      <button
                        onClick={(e) => { e.stopPropagation(); if (!starting) startSession(c); }}
                        disabled={starting !== null}
                        className="chamber-enter-btn shrink-0 text-xs"
                      >
                        {starting === c.id ? (
                          <span className="flex items-center gap-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full border animate-spin"
                              style={{ borderColor: "var(--gold-glow)", borderTopColor: "transparent" }}
                            />
                            Entering
                          </span>
                        ) : (
                          "Enter the Chamber →"
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </motion.li>
            ))}
          </motion.ul>
        )}

        {/* Error state */}
        {!loading && fetchError && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{
              border: "1px solid rgba(180,40,40,0.28)",
              background: "rgba(36,0,0,0.5)",
              padding: "24px 28px",
            }}
          >
            <p
              className="mb-2 text-xs uppercase tracking-widest"
              style={{ fontFamily: "'Cinzel', serif", color: "#f87171" }}
            >
              The chamber is unreachable
            </p>
            <p
              className="mb-4 text-sm italic"
              style={{ fontFamily: "'Playfair Display', serif", color: "var(--ivory-dim)" }}
            >
              Ensure the API server is running:
            </p>
            <code
              className="block text-xs px-3 py-2"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                background: "rgba(0,0,0,0.55)",
                color: "var(--ivory-dim)",
                letterSpacing: "0.04em",
              }}
            >
              uvicorn api:app --reload
            </code>
          </motion.div>
        )}

        {/* Empty state */}
        {!loading && !fetchError && cases.length === 0 && (
          <p
            className="text-center"
            style={{
              fontFamily: "'Cinzel', serif",
              fontSize: "0.6rem",
              letterSpacing: "0.22em",
              textTransform: "uppercase",
              color: "var(--gold-dim)",
            }}
          >
            No published cases found
          </p>
        )}
      </section>
    </main>
  );
}
