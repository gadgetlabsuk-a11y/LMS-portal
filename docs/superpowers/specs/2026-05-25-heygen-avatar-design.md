# HeyGen Avatar — Pre-rendered Podcast Video (Design)

**Date:** 2026-05-25
**Status:** Approved (pending spec review)
**Backlog item:** C-3 (HeyGen avatar integration), first increment.
**Builds on:** `docs/superpowers/specs/2026-05-21-ilb-design.md` §3 (the hybrid pre-render + live design).

## 1. Goal & scope

Make the Interactive Learning Broadcast (ILB) podcast play a **real HeyGen avatar video**
for each segment, instead of the current text + audio-only placeholder.

**In scope (this increment):**
- Pre-rendered avatar video **per segment**, lip-synced to the existing ElevenLabs narration audio.
- A **default HeyGen stock avatar**, overridable per podcast via the existing `avatar_id` field.
- Standalone **broadcasts** (the `/learn/broadcast/:id` player) — the path already verified end-to-end.
- Asynchronous render via **submit + poll status** (HeyGen video generation takes minutes).
- **Graceful fallback** to today's text + ElevenLabs audio for any segment without a rendered video.

**Explicitly NOT in scope (deferred):**
- Live streaming avatar for Q&A (LiveKit / Interactive-Streaming API) — the spec's harder half.
- Course-attached podcasts (`Course.ilb_*`) — same provider + flow; a fast follow once broadcasts land.
- An avatar **picker** UI (thumbnail grid) — default + manual `avatar_id` override only for now.
- HeyGen's own TTS voice — we lip-sync to ElevenLabs to keep one consistent voice.

## 2. Decisions (from brainstorming)

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Build scope | Pre-rendered video first | Lower risk/cost; mirrors the ElevenLabs render flow; independently shippable. Live Q&A avatar deferred. |
| 2 | Avatar voice | **Lip-sync to ElevenLabs audio** | One consistent voice across the product; reuses the verified render-audio step. |
| 3 | Avatar choice | **Default stock avatar + optional `avatar_id` override** | Fastest to working video; picker can come later. |
| 4 | Render execution | **Submit + poll status (async)** | HeyGen renders take minutes; a synchronous endpoint would hit proxy timeouts. |
| 5 | Video hosting | **Self-host the MP4** under `/api/media/video/…` | No HeyGen URL expiry, same-origin, consistent with the audio routing fix. |

## 3. Data model (Alembic migration 014)

On `Broadcast`:
- `segment_video` — `JSON` list of MP4 URLs, parallel index to `segments` / `segment_audio`
  (`null` or missing entry = that segment has no avatar video → audio fallback).
- `video_render_jobs` — `JSON`, transient per-segment job tracking while rendering:
  `[{"seg_index": int, "heygen_video_id": str, "status": "processing"|"completed"|"failed"}]`.
- Existing `avatar_id` carries the per-podcast override; a `DEFAULT_HEYGEN_AVATAR_ID`
  constant supplies the default when unset.

`BroadcastOut` gains `segment_video` so the player receives the URLs. (Prod SQLite has no
persistent volume, so `create_all` recreates these columns on each redeploy; migration 014
keeps the dev/migration chain correct.)

## 4. Backend

### 4.1 Config
- `HEYGEN_API_KEY` (already added to `config.Settings` + the admin Settings page) is now
  **consumed**. `DEFAULT_HEYGEN_AVATAR_ID` constant in the provider module.

### 4.2 `HeyGenAvatarProvider` (services/integrations.py)
Replaces the stub when `HEYGEN_API_KEY` is set (via `get_avatar_provider()`), implementing an
async-friendly interface (extends/replaces the current `AvatarProvider` ABC):
- `submit_segment(audio_url: str, avatar_id: str) -> str` — calls HeyGen video-generation,
  lip-syncing the avatar to the segment's **publicly served** ElevenLabs audio URL
  (`/api/media/audio/…`). Returns the HeyGen `video_id`.
- `poll(video_id: str) -> tuple[status, mp4_url | None]` — queries HeyGen job status.
- `StubAvatarProvider` keeps the `create_live_session` stub (live path unchanged) and
  implements the new methods to complete instantly with a placeholder URL (dev/tests).

Exact HeyGen endpoint/payload shapes (v2 generate + status poll, audio-input lip-sync,
asset upload vs public-URL) are **confirmed in the research step** before coding — not
hardcoded from assumption here.

### 4.3 Endpoints (on broadcasts; mirror `render-audio`)
- `POST /api/ilb/broadcasts/{id}/render-avatar`
  - `503` if HeyGen not configured (same pattern as TTS).
  - For each segment that has audio, call `submit_segment` and record a `processing` job in
    `video_render_jobs`. Returns the job list immediately.
- `GET /api/ilb/broadcasts/{id}/avatar-status`
  - For each `processing` job, `poll`; when completed, **download the MP4** and write it to
    `uploads/video/ilb_bcast_{id}_seg_{i}.mp4`, set `segment_video[i] = /api/media/video/…`,
    mark the job `completed`. On HeyGen failure → mark `failed`.
  - Returns `{overall: processing|complete|failed, segments: [{seg, status, url}]}`.

### 4.4 Static serving
`uploads/video/` is served by the existing `/uploads` and `/api/media` mounts (the audio fix
already mounts the whole `uploads` dir at `/api/media`), so no new mount is needed.

## 5. Frontend

### 5.1 Player (`ILBPlayerPage`)
- Read `segment_video` from the loaded config; `currentVideo = segment_video?.[segIdx]`.
- If `currentVideo` exists → render a `<video>` in the avatar stage (MP4 has the ElevenLabs
  audio baked in). Auto-advance is driven by the video's `onEnded`, **reusing the existing
  autoplay / Play-Pause logic** — the media ref is generalised to point at either the
  `<audio>` or the `<video>` element. Timer fallback still only runs when there is neither.
- If no `currentVideo` → unchanged behaviour (text + ElevenLabs `<audio>`). A partially
  rendered podcast still plays through.

### 5.2 Authoring (broadcast editor)
- Add a **"Render avatar video"** action, enabled once segment audio exists.
- On click: `POST render-avatar`, then poll `avatar-status`, showing progress ("Rendering 2/3…").
- On completion, the preview plays the avatar video.

## 6. Error handling / graceful degradation
- HeyGen key absent → `render-avatar` `503`; player uses audio. No crash.
- A segment's job fails → marked `failed`; player falls back to audio for that segment only.
- MP4 download/store failure → logged; that segment falls back to audio.
- Self-hosted MP4s avoid HeyGen URL expiry and cross-origin issues.

## 7. Testing
- **Backend unit:** `HeyGenAvatarProvider` with mocked `httpx` (submit → `video_id`; poll →
  `completed` + url). Stub completes instantly.
- **Backend router:** `render-avatar` `503` without key; with a mocked provider, submitting
  creates `processing` jobs; `avatar-status` transitions `processing → completed` and
  populates `segment_video`; a failed job degrades gracefully.
- **Frontend:** player renders `<video>` and advances on `ended` when `segment_video` is
  present; falls back to `<audio>` when absent.
- **Live prod check (after deploy):** render a real avatar for one short broadcast and confirm
  it plays + auto-advances (as done for audio).

## 8. Risks
- **HeyGen plan access:** the account may not expose the Video-Generation API, or may
  watermark/limit output. Surfaced as a clean error from `render-avatar`; player still works on audio.
- **Render latency/cost:** minutes + credits per segment-second. Keep test segments short;
  consider a future length cap. Not a blocker for this increment.
- **Public audio URL reach:** HeyGen must fetch `/api/media/audio/…`. It is public in prod;
  if a future deployment locks it down, switch to HeyGen asset upload (noted in research).

## 9. Out-of-scope follow-ups
Course-attached podcast parity · avatar picker UI · live streaming Q&A avatar (LiveKit) ·
HeyGen-native voice option · render length/cost caps.
