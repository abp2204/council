"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Scale } from "lucide-react";

const EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

interface Turn {
  role: "user" | "opponent";
  text: string;
  deviation?: boolean;
  streaming?: boolean;
}

type RecordState = "idle" | "recording" | "processing";

const BARS = 11;

function WaveformBars() {
  return (
    <div className="flex items-end gap-[2px] h-[18px]">
      {Array.from({ length: BARS }).map((_, i) => (
        <div
          key={i}
          className="waveform-bar"
          style={{ animationDelay: `${(i / BARS) * 0.85}s` }}
        />
      ))}
    </div>
  );
}

function MicIcon() {
  return (
    <svg
      width="16" height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      style={{ color: "var(--gold-glow)" }}
    >
      <path d="M12 1a4 4 0 0 1 4 4v7a4 4 0 0 1-8 0V5a4 4 0 0 1 4-4z" />
      <path
        d="M6.5 11A5.5 5.5 0 0 0 17.5 11M12 18v4M9 22h6"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Session() {
  const { id: sessionId } = useParams<{ id: string }>();
  const router = useRouter();

  const [turns, setTurns]             = useState<Turn[]>([]);
  const [input, setInput]             = useState("");
  const [closed, setClosed]           = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [evaluating, setEvaluating]   = useState(false);
  const [recordState, setRecordState] = useState<RecordState>("idle");
  const [micError, setMicError]       = useState<string | null>(null);
  const [caseTitle, setCaseTitle]       = useState<string | null>(null);
  const [opponentRole, setOpponentRole] = useState<string>("The Court");

  const bottomRef        = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);

  useEffect(() => {
    const opening = sessionStorage.getItem(`council_opening_${sessionId}`);
    const title   = sessionStorage.getItem(`council_case_title_${sessionId}`);
    if (opening) {
      setTurns([{ role: "opponent", text: opening }]);
      sessionStorage.removeItem(`council_opening_${sessionId}`);
    }
    if (title) setCaseTitle(title);
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const handleMoveResponse = useCallback(
    (data: { deviation?: boolean; stream_url: string; transcription?: string }) => {
      if (data.transcription) setInput(data.transcription);
      setTurns((prev) => [...prev, { role: "opponent", text: "", streaming: true, deviation: data.deviation ?? false }]);

      const streamUrl = data.stream_url.replace(/^\//, "/api/");
      let accumulated = "";
      const es = new EventSource(streamUrl);

      es.onmessage = (e) => {
        let parsed: { type?: string; closes?: boolean } | null = null;
        try { parsed = JSON.parse(e.data); } catch { /* plain token — expected for streamed text */ }

        if (parsed?.type === "done") {
          es.close();
          setTurns((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.streaming) last.streaming = false;
            return next;
          });
          if (parsed.closes) setClosed(true);
          setSubmitting(false);
        } else {
          accumulated += e.data;
          setTurns((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.streaming) last.text = accumulated;
            return next;
          });
        }
      };

      es.onerror = () => {
        es.close();
        setTurns((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.streaming) {
            last.text = accumulated || "(no response)";
            last.streaming = false;
          }
          return next;
        });
        setSubmitting(false);
      };
    },
    []
  );

  async function submitText() {
    const text = input.trim();
    if (!text || submitting || closed) return;
    setInput("");
    setSubmitting(true);
    setTurns((prev) => [...prev, { role: "user", text }]);
    try {
      const r = await fetch(`/api/sessions/${sessionId}/moves`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const text2 = await r.text();
      if (!r.ok) throw new Error(`http ${r.status}`);
      handleMoveResponse(JSON.parse(text2));
    } catch (e) {
      console.error(e);
      setSubmitting(false);
    }
  }

  async function startRecording() {
    setMicError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecordState("processing");
        setSubmitting(true);
        const blob = new Blob(chunksRef.current, { type: mr.mimeType || "audio/webm" });
        setTurns((prev) => [...prev, { role: "user", text: "…", streaming: true }]);
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 60_000);
        try {
          const r = await fetch(`/api/sessions/${sessionId}/moves`, { method: "POST", body: form, signal: controller.signal });
          const raw = await r.text();
          if (!r.ok) throw new Error(`http ${r.status}`);
          const data = JSON.parse(raw);
          const displayText = data.transcription || "(voice argument)";
          setTurns((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.streaming) { last.text = displayText; last.streaming = false; }
            return next;
          });
          handleMoveResponse(data);
        } catch (e) {
          console.error(e);
          setTurns((prev) => prev.slice(0, -1));
          setSubmitting(false);
        } finally {
          clearTimeout(timeout);
          setRecordState("idle");
        }
      };

      mr.start();
      setRecordState("recording");
    } catch {
      setMicError("Microphone access denied. Use text input instead.");
      setRecordState("idle");
    }
  }

  function stopRecording() { mediaRecorderRef.current?.stop(); }

  function toggleRecording() {
    if (recordState === "recording") stopRecording();
    else if (recordState === "idle" && !submitting && !closed) startRecording();
  }

  async function evaluate() {
    setEvaluating(true);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120_000);
    try {
      const r = await fetch(`/api/sessions/${sessionId}/evaluate`, { method: "POST", signal: controller.signal });
      const raw = await r.text();
      if (!r.ok) throw new Error(`http ${r.status}: ${raw}`);
      const score = JSON.parse(raw);
      sessionStorage.setItem(`council_score_${sessionId}`, JSON.stringify(score));
      router.push(`/session/${sessionId}/review`);
    } catch (e) {
      console.error(e);
      setEvaluating(false);
    } finally {
      clearTimeout(timeout);
    }
  }

  const argCount = turns.filter((t) => t.role === "user").length;

  const romanNumerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
  let userTurnCount = 0;
  const turnsWithNums = turns.map((t) => ({
    ...t,
    userNum: t.role === "user" ? ++userTurnCount : 0,
  }));

  return (
    <main className="flex flex-col h-screen max-w-4xl mx-auto px-5 relative">

      {/* ── Header ── */}
      <header className="shrink-0 pt-6 pb-0">
        <div className="flex items-center justify-between">
          {/* Brand + breadcrumb */}
          <div className="flex items-center gap-3 min-w-0 overflow-hidden">
            <span
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.65rem",
                letterSpacing: "0.22em",
                textTransform: "uppercase",
                color: "var(--gold-glow)",
                flexShrink: 0,
              }}
            >
              Council
            </span>
            <span style={{ color: "rgba(212,175,55,0.22)", fontSize: "7px", flexShrink: 0 }}>◆</span>
            <span
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.65rem",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "rgba(212,175,55,0.42)",
                flexShrink: 0,
              }}
            >
              The Arena
            </span>
            {caseTitle && (
              <>
                <span style={{ color: "rgba(212,175,55,0.18)", fontSize: "7px", flexShrink: 0 }}>◆</span>
                <span className="session-case-title truncate">{caseTitle}</span>
              </>
            )}
          </div>

          {/* Right: arg counter + back */}
          <div className="flex items-center gap-5">
            {argCount > 0 && (
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: "0.58rem",
                  letterSpacing: "0.08em",
                  color: "rgba(212,175,55,0.3)",
                }}
              >
                {argCount} {argCount === 1 ? "argument" : "arguments"} on record
              </span>
            )}
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
              ← Cases
            </a>
          </div>
        </div>

        <div className="gold-rule mt-4" />
      </header>

      {/* ── Transcript ── */}
      <div className="flex-1 overflow-y-auto py-8">

        {/* Empty state */}
        {turns.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4 pb-10">
            <svg width="52" height="54" viewBox="0 0 52 54" fill="none" aria-hidden>
              <path
                d="M7 54 C7 22, 22 4, 26 4 C30 4, 45 22, 45 54"
                stroke="rgba(212,175,55,0.18)" strokeWidth="1.5" fill="none"
              />
              <polygon points="26,0 28.5,6 26,12 23.5,6" fill="rgba(212,175,55,0.32)" />
            </svg>
            <p
              className="text-sm italic text-center leading-[1.9]"
              style={{
                fontFamily: "'Playfair Display', serif",
                color: "rgba(212,175,55,0.32)",
              }}
            >
              The court is in session.<br />Awaiting opening argument…
            </p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {turnsWithNums.map((turn, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: EASE }}
              className={`mb-6 flex ${turn.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {turn.role === "opponent" ? (
                /* ── The Court ── */
                <div className="w-full" style={{ maxWidth: "90%" }}>
                  {/* Label */}
                  <div className="flex items-center gap-2.5 mb-2 pl-4">
                    <span
                      style={{
                        fontFamily: "'Cinzel', serif",
                        fontSize: "0.56rem",
                        letterSpacing: "0.24em",
                        textTransform: "uppercase",
                        color: "var(--gold-glow)",
                      }}
                    >
                      {opponentRole}
                    </span>
                    {turn.streaming && (
                      <span
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.52rem",
                          letterSpacing: "0.1em",
                          textTransform: "uppercase",
                          color: "rgba(212,175,55,0.32)",
                        }}
                      >
                        · deliberating
                      </span>
                    )}
                  </div>

                  {/* Deviation alert */}
                  {turn.deviation && (
                    <div className="deviation-band flex items-center gap-3 mb-3">
                      <span className="deviation-badge">⚑ Deviation</span>
                      <span
                        style={{
                          fontFamily: "'Cinzel', serif",
                          fontSize: "0.5rem",
                          letterSpacing: "0.12em",
                          color: "rgba(245, 158, 11, 0.55)",
                        }}
                      >
                        Argument departs from the historical record
                      </span>
                    </div>
                  )}

                  {/* Panel */}
                  <div
                    className="court-panel px-7 py-5 text-sm leading-[1.9]"
                    style={{ fontFamily: "'Playfair Display', serif", color: "var(--ivory)" }}
                  >
                    {turn.streaming && !turn.text ? (
                      <span className="streaming-cursor" />
                    ) : (
                      <>
                        {turn.text}
                        {turn.streaming && <span className="streaming-cursor" />}
                      </>
                    )}
                  </div>
                </div>
              ) : (
                /* ── You ── */
                <div style={{ maxWidth: "72%" }}>
                  {/* Label */}
                  <div className="flex items-center justify-end gap-2 mb-2 pr-4">
                    <span className="argument-label">
                      {turn.userNum && turn.userNum <= romanNumerals.length
                        ? `Argument ${romanNumerals[turn.userNum - 1]}`
                        : `Argument ${turn.userNum}`}
                    </span>
                  </div>

                  {/* Panel */}
                  <div
                    className="user-panel px-6 py-5 text-sm leading-[1.9]"
                    style={{ fontFamily: "'Playfair Display', serif", color: "var(--ivory)" }}
                  >
                    {turn.streaming && !turn.text ? (
                      <span className="streaming-cursor" />
                    ) : (
                      <>
                        {turn.text}
                        {turn.streaming && <span className="streaming-cursor" />}
                      </>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* ── Input area ── */}
      <div className="shrink-0 pb-7">
        <div className="gold-rule-dim mb-5" />

        {closed ? (
          /* ── Session closed state ── */
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.55, ease: EASE }}
            className="text-center py-9"
          >
            <div
              className="inline-flex items-center justify-center w-[68px] h-[68px] mb-5 scale-ring"
              style={{ background: "rgba(212,175,55,0.025)" }}
              aria-hidden
            >
              <Scale size={24} color="var(--gold-glow)" />
            </div>

            <p
              className="mb-1"
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.58rem",
                letterSpacing: "0.24em",
                textTransform: "uppercase",
                color: "rgba(212,175,55,0.48)",
              }}
            >
              The court has closed argument
            </p>
            <p
              className="mb-8 text-sm italic"
              style={{ fontFamily: "'Playfair Display', serif", color: "var(--ivory-dim)" }}
            >
              Judgment will now be rendered on your performance.
            </p>

            <button
              onClick={evaluate}
              disabled={evaluating}
              className="transition-all disabled:opacity-40"
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.7rem",
                letterSpacing: "0.2em",
                textTransform: "uppercase",
                padding: "13px 40px",
                border: "1px solid var(--gold-glow)",
                color: evaluating ? "var(--gold-dim)" : "var(--charcoal)",
                background: evaluating ? "rgba(212,175,55,0.08)" : "var(--gold-glow)",
              }}
            >
              {evaluating ? (
                <span className="flex items-center gap-2.5">
                  <span
                    className="w-3 h-3 rounded-full border animate-spin"
                    style={{ borderColor: "var(--gold-glow)", borderTopColor: "transparent" }}
                  />
                  Evaluating
                </span>
              ) : (
                "Receive Judgment →"
              )}
            </button>
          </motion.div>
        ) : (
          /* ── Active input ── */
          <div className="flex flex-col gap-2.5">
            {micError && (
              <p
                className="text-xs mb-1"
                style={{
                  fontFamily: "'Cinzel', serif",
                  letterSpacing: "0.08em",
                  color: "#f87171",
                }}
              >
                {micError}
              </p>
            )}

            <div className="flex items-end gap-2">
              {/* Mic button */}
              <button
                onClick={toggleRecording}
                disabled={submitting && recordState === "idle"}
                aria-label={recordState === "recording" ? "Stop recording" : "Start voice argument"}
                className={`shrink-0 flex items-center justify-center transition-all disabled:opacity-40${recordState === "recording" ? " mic-active" : ""}`}
                style={{
                  width: "44px",
                  height: "44px",
                  ...(recordState === "processing"
                    ? {
                        border: "1px solid rgba(212,175,55,0.18)",
                        background: "transparent",
                        opacity: 0.55,
                        cursor: "wait",
                      }
                    : recordState === "idle"
                    ? {
                        border: "1px solid rgba(212,175,55,0.2)",
                        background: "rgba(212,175,55,0.025)",
                      }
                    : {}),
                }}
              >
                {recordState === "recording" ? (
                  <WaveformBars />
                ) : recordState === "processing" ? (
                  <span
                    className="w-3.5 h-3.5 rounded-full border animate-spin"
                    style={{ borderColor: "var(--gold-glow)", borderTopColor: "transparent" }}
                  />
                ) : (
                  <MicIcon />
                )}
              </button>

              {/* Textarea */}
              <textarea
                rows={2}
                className="flex-1 text-sm resize-none focus:outline-none transition-colors"
                style={{
                  padding: "12px 16px",
                  background: "rgba(15,11,7,0.95)",
                  border: "1px solid rgba(212,175,55,0.16)",
                  color: "var(--ivory)",
                  fontFamily: "'Playfair Display', serif",
                  lineHeight: "1.8",
                  caretColor: "var(--gold-glow)",
                }}
                placeholder={
                  recordState === "recording"
                    ? "Recording…"
                    : "State your argument…"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(212,175,55,0.42)")}
                onBlur={(e) => (e.currentTarget.style.borderColor = "rgba(212,175,55,0.16)")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submitText(); }
                }}
                disabled={submitting || recordState !== "idle"}
              />

              {/* Submit */}
              <button
                onClick={submitText}
                disabled={submitting || !input.trim() || recordState !== "idle"}
                className="shrink-0 text-xs font-medium transition-all disabled:opacity-30"
                style={{
                  fontFamily: "'Cinzel', serif",
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  padding: "0 22px",
                  height: "44px",
                  background: "var(--gold-glow)",
                  color: "var(--charcoal)",
                  alignSelf: "flex-end",
                }}
                onMouseEnter={(e) => {
                  if (!submitting) (e.currentTarget as HTMLButtonElement).style.background = "var(--gold-bright)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background = "var(--gold-glow)";
                }}
              >
                {submitting && recordState === "idle" ? (
                  <span
                    className="w-3 h-3 rounded-full border animate-spin block"
                    style={{ borderColor: "var(--charcoal)", borderTopColor: "transparent" }}
                  />
                ) : (
                  "Submit"
                )}
              </button>
            </div>

            <p
              style={{
                fontFamily: "'Cinzel', serif",
                fontSize: "0.52rem",
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "rgba(212,175,55,0.22)",
                paddingLeft: "2px",
              }}
            >
              Enter to submit · Shift+Enter for new line · Mic for voice
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
