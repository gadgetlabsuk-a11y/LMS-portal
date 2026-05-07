"""
Course player service.
Generates a self-contained HTML course player with embedded slide data,
audio sync, video clip support, and keyboard navigation.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PlayerService:
    """Generates interactive HTML course players."""

    def generate_player(
        self, course_content: Dict[str, Any], audio_urls: Dict[str, str], course_id: int
    ) -> str:
        course_title = course_content.get("title", "Untitled Course")
        description = course_content.get("description", "")
        objectives = course_content.get("objectives", [])
        modules = course_content.get("modules", [])

        logger.info(f"Generating player for course {course_id}: {course_title}")

        slides = []

        # Title slide
        slides.append({"type": "title", "title": course_title, "subtitle": description})

        # Objectives
        if objectives:
            slides.append({"type": "objectives", "items": objectives})

        # Modules + lessons
        for module in modules:
            module_id = module.get("id", 0)
            module_title = module.get("title", "")

            slides.append({
                "type": "module",
                "number": module_id,
                "title": module_title,
                "description": module.get("description", ""),
            })

            for lesson in module.get("lessons", []):
                lesson_id = lesson.get("id", 0)
                audio_key = f"{module_id}_{lesson_id}"
                video_url = lesson.get("video_url")

                if video_url:
                    # Video clip slide
                    slides.append({
                        "type": "video",
                        "module": module_title,
                        "title": lesson.get("title", ""),
                        "video_url": video_url,
                        "duration": lesson.get("estimated_duration_minutes", 5),
                    })
                else:
                    # Text + audio slide
                    slides.append({
                        "type": "lesson",
                        "module": module_title,
                        "title": lesson.get("title", ""),
                        "points": self._key_points(lesson),
                        "audio": audio_urls.get(audio_key),
                        "duration": lesson.get("estimated_duration_minutes", 5),
                    })

        # Closing
        slides.append({"type": "closing", "title": course_title})

        html = self._build_html(slides, course_title, course_id)
        logger.info(f"Player built: {len(slides)} slides, course {course_id}")
        return html

    def _key_points(self, lesson: Dict[str, Any]) -> list:
        outcomes = lesson.get("learning_outcomes", [])
        if outcomes:
            return [str(o) for o in outcomes[:3]]
        content = str(lesson.get("content", ""))
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 10]
        return sentences[:3]

    def _build_html(self, slides: list, course_title: str, course_id: int) -> str:
        slides_json = json.dumps(slides, ensure_ascii=False)
        safe_title = self._esc(course_title)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --navy:#1F2937;--indigo:#6366F1;--indigo-dark:#4F46E5;
  --white:#FFFFFF;--gray:#F3F4F6;--accent:#E0E7FF;
  --text:#1F2937;--muted:#6B7280;
}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--navy);overflow:hidden;height:100vh}}
#player{{width:100vw;height:100vh;display:flex;flex-direction:column}}

/* ── Exit button ── */
#exit-btn{{
  position:fixed;top:1rem;left:1rem;z-index:1000;
  background:rgba(31,41,55,0.7);color:rgba(255,255,255,0.85);
  border:1px solid rgba(255,255,255,0.2);
  padding:0.4rem 0.85rem;border-radius:0.375rem;
  font-size:0.82rem;cursor:pointer;
  backdrop-filter:blur(4px);
  transition:background 0.2s, color 0.2s;
  text-decoration:none;display:inline-flex;align-items:center;gap:0.4rem;
}}
#exit-btn:hover{{background:rgba(99,102,241,0.8);color:#fff;border-color:transparent}}

/* ── Start overlay ── */
#start-overlay{{
  position:fixed;inset:0;z-index:999;
  background:rgba(31,41,55,0.96);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.5rem;
}}
#start-overlay h1{{color:#fff;font-size:2rem;font-weight:700;text-align:center;max-width:600px;line-height:1.3}}
#start-overlay p{{color:var(--accent);font-size:1.1rem;text-align:center}}
#start-btn{{
  background:var(--indigo);color:#fff;border:none;
  padding:1rem 2.5rem;font-size:1.1rem;font-weight:600;
  border-radius:0.5rem;cursor:pointer;transition:background 0.2s;
  margin-top:0.5rem;
}}
#start-btn:hover{{background:var(--indigo-dark)}}
.play-icon{{font-size:2.5rem}}

/* ── Slide area ── */
#slide-container{{
  flex:1;position:relative;overflow:hidden;
}}
.slide{{
  position:absolute;inset:0;display:none;
  flex-direction:column;align-items:center;justify-content:center;
  padding:3rem 4rem;animation:fadeIn 0.4s ease;
}}
.slide.active{{display:flex}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}

/* ── Slide types ── */
.slide.type-title{{background:var(--navy);color:#fff;text-align:center}}
.slide.type-title .s-title{{font-size:clamp(1.8rem,4vw,3.2rem);font-weight:700;margin-bottom:1rem;line-height:1.2}}
.slide.type-title .s-sub{{font-size:clamp(1rem,2vw,1.4rem);color:var(--accent);max-width:70%}}
.slide.type-title .accent-bar{{width:80px;height:4px;background:var(--indigo);margin:1.5rem auto 0}}

.slide.type-objectives{{background:var(--gray);color:var(--text)}}
.slide.type-objectives .s-title{{font-size:clamp(1.5rem,3vw,2.4rem);font-weight:700;margin-bottom:2rem}}
.obj-list{{list-style:none;max-width:800px;width:100%}}
.obj-list li{{
  font-size:clamp(0.95rem,1.8vw,1.2rem);padding:0.75rem 0 0.75rem 2.5rem;
  position:relative;border-bottom:1px solid rgba(99,102,241,0.1);
}}
.obj-list li:before{{content:"✓";position:absolute;left:0;color:var(--indigo);font-weight:700;font-size:1.2rem}}

.slide.type-module{{background:var(--indigo);color:#fff;text-align:center}}
.slide.type-module .s-num{{font-size:1rem;opacity:0.8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem}}
.slide.type-module .s-title{{font-size:clamp(1.6rem,3.5vw,2.8rem);font-weight:700;margin-bottom:1rem;line-height:1.2}}
.slide.type-module .s-desc{{font-size:clamp(0.95rem,1.8vw,1.15rem);color:var(--accent);max-width:65%}}

.slide.type-lesson{{background:var(--white);color:var(--text);align-items:flex-start;justify-content:flex-start;padding-top:0}}
.lesson-top{{
  width:100%;padding:1.25rem 4rem;
  background:linear-gradient(135deg,rgba(99,102,241,0.08),transparent);
  border-top:4px solid var(--indigo);margin-bottom:2rem;
}}
.lesson-mod-label{{font-size:0.8rem;color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.3rem}}
.lesson-title{{font-size:clamp(1.3rem,2.5vw,2rem);font-weight:700;color:var(--text)}}
.lesson-body{{width:100%;max-width:900px;margin:0 auto}}
.pts-list{{list-style:none;width:100%}}
.pts-list li{{
  font-size:clamp(0.95rem,1.8vw,1.15rem);
  padding:0.9rem 0 0.9rem 2.5rem;
  position:relative;line-height:1.6;
  border-bottom:1px solid rgba(99,102,241,0.08);
}}
.pts-list li:before{{content:"▸";position:absolute;left:0;color:var(--indigo);font-size:1.2rem;top:0.85rem}}
.lesson-footer{{
  position:absolute;bottom:90px;right:2.5rem;
  display:flex;align-items:center;gap:0.5rem;
  font-size:0.8rem;color:var(--muted);
}}
.lesson-audio-bar{{
  position:absolute;bottom:90px;left:50%;transform:translateX(-50%);
  display:flex;align-items:center;gap:0.75rem;
  background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);
  padding:0.5rem 1rem;border-radius:2rem;
}}
.lesson-audio-bar audio{{
  height:28px;width:280px;
  accent-color:var(--indigo);
}}
.audio-indicator{{
  display:inline-flex;align-items:center;gap:0.4rem;
  padding:0.3rem 0.7rem;border-radius:99px;
  background:rgba(99,102,241,0.1);color:var(--indigo);
  font-size:0.78rem;font-weight:600;
}}
.audio-indicator.playing .wave{{animation:wave 1s infinite}}
@keyframes wave{{0%,100%{{transform:scaleY(1)}}50%{{transform:scaleY(2)}}}}
.wave{{display:inline-block;width:3px;height:10px;background:currentColor;margin:0 1px;border-radius:2px}}

.slide.type-video{{background:#000;color:#fff;flex-direction:column}}
.slide.type-video .s-title{{font-size:1.2rem;font-weight:600;margin-bottom:1rem;color:#fff}}
.slide.type-video video{{
  max-width:100%;max-height:calc(100vh - 200px);
  border-radius:4px;outline:none;
}}

.slide.type-closing{{background:var(--navy);color:#fff;text-align:center}}
.slide.type-closing .s-title{{font-size:clamp(2rem,5vw,4rem);font-weight:700;margin-bottom:0.5rem}}
.slide.type-closing .s-sub{{font-size:clamp(1rem,2vw,1.5rem);color:var(--indigo);margin-bottom:2rem}}
.complete-btn{{
  background:var(--indigo);color:#fff;border:none;
  padding:1rem 2.5rem;font-size:1rem;font-weight:600;
  border-radius:0.5rem;cursor:pointer;transition:background 0.2s;
}}
.complete-btn:hover{{background:var(--indigo-dark)}}

/* ── Controls bar ── */
#controls{{
  background:var(--navy);padding:0.75rem 1.5rem 1rem;
  display:flex;flex-direction:column;gap:0.6rem;flex-shrink:0;
}}
#progress-bar{{
  width:100%;height:5px;background:rgba(255,255,255,0.12);
  border-radius:3px;overflow:hidden;cursor:pointer;
}}
#progress-fill{{height:100%;background:var(--indigo);transition:width 0.3s ease;border-radius:3px}}
#nav-row{{display:flex;justify-content:space-between;align-items:center}}
.nav-btn{{
  background:var(--indigo);color:#fff;border:none;
  padding:0.6rem 1.4rem;border-radius:0.375rem;
  cursor:pointer;font-size:0.9rem;font-weight:500;
  transition:background 0.2s;
}}
.nav-btn:hover{{background:var(--indigo-dark)}}
.nav-btn:disabled{{background:rgba(255,255,255,0.15);cursor:not-allowed}}
#slide-info{{text-align:center;color:rgba(255,255,255,0.7);font-size:0.85rem;line-height:1.4}}
#lesson-label{{color:rgba(255,255,255,0.5);font-size:0.75rem;text-align:center;min-height:1em}}

@media(max-width:768px){{
  .slide{{padding:1.5rem}}
  .lesson-top{{padding:1rem 1.5rem}}
}}
</style>
</head>
<body>

<!-- Exit button — always visible -->
<a id="exit-btn" href="/admin/courses" title="Exit course">← Exit</a>

<!-- Click-to-start overlay (required by browser autoplay policy) -->
<div id="start-overlay">
  <div class="play-icon">🎓</div>
  <h1>{safe_title}</h1>
  <p>Audio narration included — use headphones for best experience</p>
  <button id="start-btn" onclick="startCourse()">▶ Start Course</button>
</div>

<div id="player">
  <div id="slide-container"></div>
  <div id="controls">
    <div id="progress-bar" onclick="onProgressClick(event)">
      <div id="progress-fill"></div>
    </div>
    <div id="nav-row">
      <button class="nav-btn" id="prev-btn" onclick="prevSlide()">◀ Prev</button>
      <div id="slide-info">
        <div id="slide-counter">1 / {len(slides)}</div>
        <div id="lesson-label"></div>
      </div>
      <button class="nav-btn" id="next-btn" onclick="nextSlide()">Next ▶</button>
    </div>
  </div>
</div>

<audio id="audio-el" preload="auto"></audio>

<script>
const SLIDES = {slides_json};
const COURSE_ID = {course_id};
const TOTAL = SLIDES.length;

let cur = 0;
let started = false;
let autoTimer = null;

const audioEl = document.getElementById('audio-el');
const slideContainer = document.getElementById('slide-container');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const counter = document.getElementById('slide-counter');
const fill = document.getElementById('progress-fill');
const label = document.getElementById('lesson-label');

function esc(t) {{
  if (!t) return '';
  return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function buildSlides() {{
  SLIDES.forEach((s, i) => {{
    const el = document.createElement('div');
    el.className = `slide type-${{s.type}}`;
    el.id = `slide-${{i}}`;

    switch(s.type) {{
      case 'title':
        el.innerHTML = `
          <div class="s-title">${{esc(s.title)}}</div>
          <div class="s-sub">${{esc(s.subtitle)}}</div>
          <div class="accent-bar"></div>`;
        break;

      case 'objectives':
        el.innerHTML = `
          <div class="s-title">Learning Objectives</div>
          <ul class="obj-list">${{s.items.map(x=>`<li>${{esc(x)}}</li>`).join('')}}</ul>`;
        break;

      case 'module':
        el.innerHTML = `
          <div class="s-num">Module ${{s.number}}</div>
          <div class="s-title">${{esc(s.title)}}</div>
          ${{s.description ? `<div class="s-desc">${{esc(s.description)}}</div>` : ''}}`;
        break;

      case 'lesson': {{
        let audioHtml = '';
        if (s.audio) {{
          audioHtml = `
            <div class="lesson-audio-bar">
              <audio id="slide-audio-${{i}}" controls preload="auto" src="${{esc(s.audio)}}"></audio>
            </div>`;
        }}
        el.innerHTML = `
          <div class="lesson-top">
            <div class="lesson-mod-label">${{esc(s.module)}}</div>
            <div class="lesson-title">${{esc(s.title)}}</div>
          </div>
          <div class="lesson-body">
            <ul class="pts-list">${{s.points.map(p=>`<li>${{esc(p)}}</li>`).join('')}}</ul>
          </div>
          ${{audioHtml}}
          <div class="lesson-footer">
            <span>⏱ ${{s.duration}} min</span>
          </div>`;
        break;
      }}
        break;

      case 'video':
        el.innerHTML = `
          <div class="s-title">${{esc(s.title)}}</div>
          <video id="vid-${{i}}" controls playsinline>
            <source src="${{esc(s.video_url)}}" type="video/mp4">
          </video>`;
        break;

      case 'closing':
        el.innerHTML = `
          <div class="s-title">🎉 Course Complete!</div>
          <div class="s-sub">Well done — you've completed ${{esc(s.title)}}</div>
          <button class="complete-btn" onclick="markComplete()">Mark as Complete ✓</button>`;
        break;
    }}

    slideContainer.appendChild(el);
  }});
}}

function renderSlide(i) {{
  clearTimeout(autoTimer);
  stopAudio();
  pauseVideos();

  document.querySelectorAll('.slide').forEach((el, idx) => {{
    el.classList.toggle('active', idx === i);
  }});

  const s = SLIDES[i];
  counter.textContent = `${{i + 1}} / ${{TOTAL}}`;
  fill.style.width = `${{Math.round(((i + 1) / TOTAL) * 100)}}%`;
  label.textContent = s.type === 'lesson' ? `${{s.module}} — ${{s.title}}` : '';

  prevBtn.disabled = i === 0;
  nextBtn.disabled = i === TOTAL - 1;

  if (!started) return;

  if (s.type === 'lesson' && s.audio) {{
    playAudio(s.audio, i);
  }} else if (s.type === 'video') {{
    const vid = document.getElementById(`vid-${{i}}`);
    if (vid) {{
      vid.play().catch(()=>{{}});
      vid.onended = () => setTimeout(nextSlide, 800);
    }}
  }}
  // No auto-advance for other slide types — user clicks Next
  // This keeps the user gesture chain alive for audio.play()
}}

function playAudio(src, slideIdx) {{
  const slideAudio = document.getElementById('slide-audio-' + slideIdx);
  if (!slideAudio) return;
  // Wire up auto-advance when audio ends
  slideAudio.onended = () => setTimeout(nextSlide, 800);
  // Attempt autoplay (works when called from user gesture chain)
  const p = slideAudio.play();
  if (p && p.catch) p.catch(() => {{
    // Autoplay blocked — audio controls are visible, user can press play
  }});
}}

function stopAudio() {{
  audioEl.pause();
  audioEl.src = '';
  // Pause any visible slide audio players
  document.querySelectorAll('audio[id^="slide-audio-"]').forEach(a => a.pause());
}}

function pauseVideos() {{
  document.querySelectorAll('video').forEach(v => {{ v.pause(); v.currentTime = 0; }});
}}

audioEl.addEventListener('ended', () => setTimeout(nextSlide, 800));

function nextSlide() {{
  if (cur < TOTAL - 1) {{ cur++; renderSlide(cur); }}
}}

function prevSlide() {{
  if (cur > 0) {{ cur--; renderSlide(cur); }}
}}

function onProgressClick(e) {{
  const rect = e.currentTarget.getBoundingClientRect();
  const pct = (e.clientX - rect.left) / rect.width;
  const idx = Math.floor(pct * TOTAL);
  cur = Math.max(0, Math.min(TOTAL - 1, idx));
  renderSlide(cur);
}}

function startCourse() {{
  document.getElementById('start-overlay').style.display = 'none';
  started = true;
  renderSlide(cur);
}}

async function markComplete() {{
  try {{
    const token = localStorage.getItem('token') || '';
    await fetch(`/api/courses/${{COURSE_ID}}/progress?progress=100`, {{
      method: 'PUT',
      headers: token ? {{'Authorization': `Bearer ${{token}}`}} : {{}}
    }});
    const btn = document.querySelector('.complete-btn');
    if (btn) {{ btn.textContent = '✓ Completed!'; btn.disabled = true; btn.style.background='#10B981'; }}
  }} catch(e) {{ console.error(e); }}
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === ' ') {{ e.preventDefault(); nextSlide(); }}
  if (e.key === 'ArrowLeft') {{ e.preventDefault(); prevSlide(); }}
}});

// Exit button — close tab if opened as popup, else navigate back
const exitBtn = document.getElementById('exit-btn');
if (exitBtn) {{
  exitBtn.addEventListener('click', (e) => {{
    if (window.opener || window.history.length <= 1) {{
      e.preventDefault();
      window.close();
    }}
    // else follow the href naturally
  }});
}}

// Init
buildSlides();
renderSlide(0);
</script>
</body>
</html>"""

    def _esc(self, text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#039;")
        )
