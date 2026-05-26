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
  show: { transition: { staggerChildren: 0.14, delayChildren: 0.55 } },
};

const itemTransition: Transition = { duration: 0.65, ease: EASE };
const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  show:  { opacity: 1, y: 0, transition: itemTransition },
};

function GothicArch() {
  return (
    <svg
      width="300"
      height="140"
      viewBox="0 0 300 140"
      fill="none"
      aria-hidden
      className="mx-auto"
    >
      {/* Outer arch */}
      <path
        d="M16 140 C16 50, 120 6, 150 6 C180 6, 284 50, 284 140"
        stroke="rgba(212,175,55,0.38)"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Mid arch */}
      <path
        d="M40 140 C40 66, 122 28, 150 28 C178 28, 260 66, 260 140"
        stroke="rgba(212,175,55,0.22)"
        strokeWidth="1"
        fill="none"
      />
      {/* Inner arch */}
      <path
        d="M68 140 C68 84, 126 52, 150 52 C174 52, 232 84, 232 140"
        stroke="rgba(212,175,55,0.11)"
        strokeWidth="1"
        fill="none"
      />
      {/* Keystone diamond */}
      <polygon points="150,0 155,10 150,20 145,10" fill="rgba(212,175,55,0.78)" />
      <polygon points="150,3 153,10 150,17 147,10" fill="rgba(212,175,55,0.28)" />
      {/* Keystone ambient glow */}
      <ellipse cx="150" cy="10" rx="10" ry="6" fill="rgba(212,175,55,0.07)" />
      {/* Column shafts */}
      <rect x="13" y="110" width="1.5" height="30" fill="rgba(212,175,55,0.18)" />
      <rect x="286" y="110" width="1.5" height="30" fill="rgba(212,175,55,0.18)" />
      {/* Column bases */}
      <rect x="8" y="136" width="16" height="4" rx="0.5" fill="rgba(212,175,55,0.22)" />
      <rect x="276" y="136" width="16" height="4" rx="0.5" fill="rgba(212,175,55,0.22)" />
      {/* Tracery horizontal bar */}
      <line
        x1="40" y1="96" x2="260" y2="96"
        stroke="rgba(212,175,55,0.07)"
        strokeWidth="0.5"
        strokeDasharray="6 6"
      />
      {/* Tracery vertical center */}
      <line
        x1="150" y1="20" x2="150" y2="140"
        stroke="rgba(212,175,55,0.05)"
        strokeWidth="0.5"
        strokeDasharray="5 8"
      />
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

  async function startSession(caseId: string) {
    setStarting(caseId);
    try {
      const r = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId }),
      });
      const raw = await r.text();
      if (!r.ok) throw new Error(`http ${r.status}: ${raw}`);
      const data = JSON.parse(raw);
      sessionStorage.setItem(`council_opening_${data.session_id}`, data.opening ?? "");
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
        className="w-full max-w-xl mx-auto px-8 pt-20 pb-16 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.1, ease: EASE }}
      >
        {/* Arch ornament */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: EASE }}
        >
          <GothicArch />
        </motion.div>

        {/* Wordmark */}
        <motion.h1
          className="mt-6"
          style={{
            fontFamily: "'Cinzel', serif",
            fontSize: "clamp(3rem, 8vw, 5.5rem)",
            fontWeight: 600,
            letterSpacing: "0.32em",
            color: "var(--ivory)",
            textShadow: "0 0 80px rgba(212,175,55,0.1)",
            lineHeight: 1,
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.9, ease: EASE }}
        >
          COUNCIL
        </motion.h1>

        {/* Gold rule */}
        <motion.div
          className="gold-rule my-7 max-w-[180px] mx-auto"
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.8, ease: EASE }}
          style={{ transformOrigin: "center" }}
        />

        {/* Sub-tagline */}
        <motion.p
          className="text-base leading-[1.85] italic max-w-xs mx-auto"
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
      <section className="w-full max-w-xl mx-auto px-8 pb-32">

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
          <div className="space-y-5">
            {[...Array(2)].map((_, i) => (
              <div
                key={i}
                className="animate-pulse"
                style={{
                  background: "var(--walnut-panel)",
                  border: "1px solid rgba(212,175,55,0.12)",
                  padding: "28px 32px",
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
            className="space-y-5 list-none p-0"
            variants={containerVariants}
            initial="hidden"
            animate="show"
          >
            {cases.map((c) => (
              <motion.li key={c.id} variants={itemVariants}>
                <div
                  className="relative group cursor-pointer overflow-hidden gold-border pillar-shadow gold-glow-hover"
                  style={{
                    background: "linear-gradient(150deg, #241b12 0%, var(--walnut-deep) 100%)",
                  }}
                  onClick={() => !starting && startSession(c.id)}
                >
                  {/* Left pillar accent — visible on hover */}
                  <div className="case-card-accent" aria-hidden />

                  {/* Top edge accent — appears on hover */}
                  <div
                    className="absolute top-0 inset-x-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                    style={{ background: "linear-gradient(to right, transparent, rgba(212,175,55,0.38) 40%, rgba(212,175,55,0.38) 60%, transparent)" }}
                    aria-hidden
                  />

                  <div className="px-8 py-7">
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

                    {/* Title + CTA row */}
                    <div className="flex items-start justify-between gap-6">
                      <div className="min-w-0 flex-1">
                        <h2
                          className="mb-4 leading-snug"
                          style={{
                            fontFamily: "'Cinzel', serif",
                            fontSize: "1.15rem",
                            fontWeight: 500,
                            letterSpacing: "0.04em",
                            color: "var(--ivory)",
                          }}
                        >
                          {c.title}
                        </h2>

                        {/* Role line */}
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
                            <span
                              className="not-italic font-medium"
                              style={{ color: "var(--ivory)" }}
                            >
                              {c.user_role}
                            </span>
                          </p>
                        </div>
                      </div>

                      {/* CTA button */}
                      <button
                        onClick={(e) => { e.stopPropagation(); if (!starting) startSession(c.id); }}
                        disabled={starting !== null}
                        className="shrink-0 mt-0.5 text-xs font-medium transition-all disabled:opacity-40 whitespace-nowrap"
                        style={{
                          fontFamily: "'Cinzel', serif",
                          letterSpacing: "0.18em",
                          padding: "10px 22px",
                          border: "1px solid rgba(212,175,55,0.38)",
                          color: "var(--gold-glow)",
                          background: "rgba(212,175,55,0.04)",
                        }}
                        onMouseEnter={(e) => {
                          (e.currentTarget as HTMLButtonElement).style.background = "rgba(212,175,55,0.1)";
                          (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(212,175,55,0.6)";
                        }}
                        onMouseLeave={(e) => {
                          (e.currentTarget as HTMLButtonElement).style.background = "rgba(212,175,55,0.04)";
                          (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(212,175,55,0.38)";
                        }}
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
                          "Argue →"
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
