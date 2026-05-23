# ADR 0005: Opponent TTS deferred to v2

## Status
Accepted

## Context
ADR 0002 establishes voice as the primary input modality — the user argues out loud, mirroring real courtroom advocacy. A natural extension is making the Opposing Role's responses spoken as well (text-to-speech), so the entire exchange is audio. This would make the simulation fully immersive.

However, TTS adds:
- An additional API call per opponent turn (latency compounds on top of Groq inference)
- Cost per character generated
- Audio playback state management in the browser
- Voice selection and character decisions (what does Frankfurter sound like?)

## Decision
Opponent responses are displayed as text in v1. TTS for the Opposing Role is deferred to v2 and treated as a high-priority feature, not a cut.

## Consequences
- v1 is asymmetric: voice in, text out. This is a known product gap, not an oversight.
- The session UI (transcript format) must make text responses feel alive without audio — streaming token-by-token via SSE partially compensates.
- When TTS ships, the opponent's voice must be consistent with their historical persona. Voice selection (ElevenLabs clone vs. generic TTS) will require its own decision at that time.
- ADR 0002's rationale (authenticity of spoken advocacy) applies equally to the opponent's side — this decision should be revisited as soon as the core loop is stable.
