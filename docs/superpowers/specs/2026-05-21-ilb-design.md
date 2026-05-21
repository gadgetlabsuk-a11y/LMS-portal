# Interactive Learning Broadcast (ILB) — Demo Design

**Status:** Approved design (v1)
**Date:** 2026-05-21
**Owner:** Stuart Roberts
**Type:** Extension of the existing LMS module (same repo)

---

## 1. Purpose & Framing

ILB delivers training as an interactive, avatar-led "broadcast": an AI host presents a
podcast-style narration while a HeyGen avatar speaks on screen, and the learner can interrupt
or queue questions (by voice) that the avatar answers live, grounded in the course content.

**This build is a DEMO.** Its job is to demonstrate the concept convincingly and greenlight a
proper rebuild as a module inside **praxis**. Therefore:

- Optimise for *demonstrability and impact*, not production hardening.
- The avatar + voice Q&A is the differentiator vs the existing AI Course Builder — it is the
  headline of the demo.
- Anything that is hardening, scale, or multi-customer concern is explicitly deferred to the
  praxis rebuild (see §9).

It is built as an **extension of the current LMS module** (FastAPI backend + Vite/React
frontend, same repo), reusing the shipped v1.0 AI Course Builder wherever possible.

---

## 2. Locked Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Delivery scope | **Full avatar demo** | The avatar/voice experience is the differentiator the demo must show |
| 2 | Avatar delivery | **Hybrid** — pre-rendered HeyGen video for scripted podcast; live HeyGen streaming for Q&A only | Isolates live-latency risk to question moments; scripted playback stays rock-solid |
| 3 | Avatar persona | One HeyGen **stock** avatar, must exist in **both** video-gen and interactive-streaming APIs | Seamless pre-render↔live switch; zero avatar-creation time |
| 4 | Voice input | **Deepgram** streaming STT | Reliable, low-latency, cross-browser — demo-safe |
| 5 | Interaction modes | **Both** interrupt + defer | Interrupt is the wow; defer is low marginal cost and shows the full concept |
| 6 | Q&A safety | Grounded + guardrails; **Q&A is a learning aid, comprehension is proven by the quiz** | Contains liability — a wrong Q&A answer can't pass a learner |
| 7 | Q&A grounding | **Long-context** (source passed in-prompt), **no vector store** | Demo briefs are short; pgvector/Qdrant is a praxis concern only if corpora grow |
| 8 | Audit | **Regulator-grade output** (record + hash-chain + PDF/JSON pack); external anchor **stubbed** | Show the compliance story; defer real TSA/WORM infra to praxis |
| 9 | Trust anchor (when hardened) | Hash-chain + **RFC 3161 timestamp + WORM (S3 Object Lock)** | Genuinely tamper-evident, no key-custody burden — but stubbed in the demo |
| 10 | Tenancy | **Single-tenant**; Stadler brand via existing `WhiteLabelConfig` | Fastest to demo; multi-tenancy is a large retrofit, deferred |
| 11 | Language | **EN only** | CY is additive later (multilingual TTS + captions); avoids per-component verification now |
| 12 | Audio download | **Streaming only** | Preserves engagement/interaction audit |
| 13 | TMS sync | **Skipped** | No named target; deferred to praxis |

> **Note on HSE:** HSE/safety content was an example use case, not the defining constraint.
> ILB is general training delivery; the grounded-and-guarded Q&A model is the sensible default
> everywhere and extra-defensible when content is safety-critical.

---

## 3. Architecture — Reuse vs Extend vs Build

### Reuse as-is
- AI authoring — `backend/services/claude_service.py` + SSE streaming infra
- Relational content model — Course / Module / Video / Slide / Block / Quiz / Question
- Knowledge checks & assessment — `Quiz` (`quiz_type`), `Question` (4 types), AI question gen
- Learner player — `backend/services/player_service.py`, `/learn`
- White-label theming — `WhiteLabelConfig` (Stadler brand)
- Audit base — `AuditLog`; cost tracking — `ApiUsage`, `AiPromptLog`
- Versioning / version pinning — `CourseVersion`, `Enrollment.course_version`
- Doc ingestion — `document_service.py` (PyMuPDF / python-docx / python-pptx)

### Extend
- `tts_service.py` — keep batch narration (used for pre-render); **add a separate
  live-streaming TTS path** (ElevenLabs Turbo) for spoken answers. The two are different
  pipelines: batch is throttled + SHA-256 cached; live is latency-sensitive, uncached.
- `Video` model — add `video_type='podcast'` (continuous) alongside `slideshow_narrated`, plus
  avatar/render config fields.

### Build (new)
- `avatar_service.py` — HeyGen integration: (a) **pre-render** scripted avatar video
  (video-generation API), (b) **live** session token + control (interactive-streaming API).
- `qa_service.py` — Claude grounded answer + guardrails (cite source / refuse / escalate /
  disclaimer) + `BroadcastSession` / `Interaction` logging.
- STT proxy — Deepgram streaming websocket relay.
- `audit_service.py` — broadcast-session record, hash-chain, regulator pack (PDF + JSON).
  The external trust anchor (RFC 3161 TSA + S3 WORM) sits **behind an interface that is
  stubbed** in the demo so praxis can drop in real anchors without refactor.
- **ILB Player** (frontend) — extends the learner player: pre-rendered avatar video playback +
  **LiveKit** live-avatar stream + mic capture + interrupt/defer controls + captions.

### Transport
- **LiveKit** for the live avatar (HeyGen Interactive Avatar's native WebRTC transport).

### Queue
- No separate queue (no BullMQ). The pre-render job runs in-process with SSE progress, mirroring
  the existing bulk-TTS pattern. (If praxis needs a queue, use a Python-native one — arq/Celery.)

---

## 4. Data Model Deltas (against `backend/models/models.py`)

**Naming collision fix:** the spec's "Session" entity clashes with the existing `Session`
table (JWT auth sessions). The ILB one is named **`BroadcastSession`**.

New tables:
- **`BroadcastSession`** — `enrollment_id` (FK), `mode` (interrupt|defer), `started_at`,
  `completed_at`, `final_score`, `completion_status`.
- **`Interaction`** — `broadcast_session_id` (FK), `ts`, `type` (q|a|check|attention),
  `question_text`, `answer_text`, `source_refs` (JSON), `confidence`, `escalated` (bool),
  `input_mode` (voice|text).
- **`SessionAttestation`** — `broadcast_session_id` (FK), `content_hash`, `prev_hash`,
  `signed_at`, `signature` (anchor stubbed for demo).

Reuse (no new entities):
- **`Enrollment`** = assignment + course-version pinning (no separate `Assignment` entity).
- **`Quiz` / `Question`** = knowledge checks + final assessment (no separate
  `knowledge_checks[]`).

Extend:
- **`Video`** — `video_type='podcast'`; avatar config (HeyGen avatar id, pre-rendered video URL,
  host-persona voice id — `narration_voice_id` already exists).

---

## 5. Core Flows

### Author
1. Existing authoring (identity, structure, source ingestion, AI generation).
2. Generate podcast-style script in a host persona (extend the script prompt).
3. ElevenLabs batch audio (existing TTS).
4. **HeyGen pre-render** avatar video from the scripted narration.
5. Knowledge checks via existing Quiz Builder.
6. Publish.

### Learner
1. Launch ILB Player.
2. Pre-rendered avatar plays the podcast.
3. **Interrupt:** say "pause" / tap → Deepgram STT → Claude grounded answer → live TTS →
   **live HeyGen avatar** speaks the answer → resume at the last sentence boundary.
4. **Defer:** say "queue" / tap → question buffered with context → batch-answered by the live
   avatar at the next segment boundary.
5. Knowledge check at segment boundaries (existing quiz).
6. Final assessment → completion → audit record + regulator pack.

### The seam (pre-render ↔ live)
Same stock persona in both HeyGen APIs. On interrupt: pause the `<video>` element, bring up the
LiveKit live stream of the same avatar, answer, fade back to the video, resume. **The
same-avatar-in-both-APIs assumption is the #1 thing the feasibility spike must verify.**

---

## 6. Q&A Safety Model

- **Grounded** in the course source via long-context (source passed in-prompt; no vector store).
- **Mandatory citation** of the source passage used.
- **Refuse + escalate to a human** when the source doesn't cover the question.
- **Disclaimer:** "refer to the official brief."
- **Q&A is a learning aid, not the assessment.** Comprehension is proven by the knowledge-check
  quiz, so a wrong/declined Q&A answer can never pass a learner. Q&A transcripts are logged for
  audit but are not the compliance proof.

---

## 7. Audit (Regulator-Grade Output, Demo-Stubbed Anchor)

- Log `BroadcastSession` + every `Interaction` (incl. attention checks and escalations).
- Compute a per-learner hash-chain over session records (`SessionAttestation`).
- Generate a regulator **audit pack**: PDF (human-readable) + JSON (machine-readable) per learner
  per course — completion, knowledge-check score, Q&A transcript, time-on-task.
- The external trust anchor (RFC 3161 timestamp + S3 Object Lock WORM) is implemented **behind a
  stub interface** in the demo. Praxis swaps in the real anchors without touching call sites.

---

## 8. Build Approach (high level — detail goes to writing-plans)

Numbered as a continuation of the existing GSD phases (19+), inside the current module.

1. **Feasibility spike (first, throwaway).** Confirm: one HeyGen stock avatar exists in *both*
   video-gen and interactive-streaming APIs; live Q&A latency is demo-acceptable; LiveKit
   transport wired (HeyGen ↔ browser). **Hard gate** — a failure reshapes the design.
2. Podcast pre-render pipeline (script → ElevenLabs → HeyGen video → stored MP4).
3. ILB Player (video playback + LiveKit live stream + the seam + captions).
4. Live Q&A (Deepgram → Claude grounded → live TTS → live avatar) + interrupt + defer.
5. `BroadcastSession` / `Interaction` logging + regulator-grade audit pack (stubbed anchor).
6. Stadler demo content + end-to-end run-through.

---

## 9. Explicitly NOT in the Demo (→ praxis rebuild)

Multi-tenancy · Welsh (CY) · audio download · live TMS sync · real audit trust-anchor
(TSA/WORM) · custom branded avatar · vector-store RAG · production latency tuning ·
self-host TTS.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| HeyGen stock avatar not available in both APIs | Spike verifies first; pick a confirmed-dual-mode avatar |
| Live Q&A latency too high to feel responsive | Demo bar is lower than production; "thinking" avatar state; spike measures real latency |
| Pre-render ↔ live visual seam is jarring | Same persona both modes; fade transition; resume at sentence boundary |
| Coordinating Deepgram + LiveKit + ElevenLabs streaming | Vertical-slice first (spike), then build outward |
| Live demo fails in front of stakeholders | Pre-render portion is reliable video; rehearse; have a recorded fallback |

---

## 11. Testing

It's a demo, so live/avatar pieces are verified by **vertical-slice-first + manual demo-path**
run-throughs (they can't be unit-tested meaningfully). The parts likely to **survive into
praxis** get real tests:
- Data model (`BroadcastSession`, `Interaction`, `SessionAttestation`)
- Q&A grounding + guardrails (cite / refuse / escalate behaviour)
- Audit-pack generation (PDF + JSON correctness, hash-chain integrity)
