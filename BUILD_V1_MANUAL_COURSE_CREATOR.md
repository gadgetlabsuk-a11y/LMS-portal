# BUILD V1: Manual Course Creator + SCORM Export

**Target:** Claude Code (autonomous build agent)
**Scope:** Additive feature on top of existing LMS backend. Base AI auto-generation pipeline already complete.
**Date:** 2026-05-06
**Status:** Build-ready spec

---

## 0. Context for Claude Code

### What already exists (DO NOT REBUILD)

Existing FastAPI + SQLAlchemy backend at `backend/`:

- Auth: email/password, MFA, sessions, audit logs, IP allowlist
- Roles: `ADMIN`, `CREATOR`, `TRAINEE` (see `models/models.py`)
- Course CRUD with JSON `content` field (`routers/courses.py`)
- AI pipeline: `claude_service.py`, `document_service.py`, `script_service.py`, `slide_service.py` (PPTX gen), `tts_service.py`, `player_service.py`
- White-label config table with logo, colours, fonts, custom CSS (`WhiteLabelConfig`)
- Enrollment tracking with progress + completed (`Enrollment`)
- API usage tracking, error logs, feature flags
- Frontend at `frontend/index.html` plus `backend/static/js/` (React + react-router via CDN scripts)

### What we are adding (V1 SCOPE)

1. Block-based manual course editor (Wix-style drag-and-drop)
2. Block taxonomy (text, heading, image, list, accordion, video, audio, divider, MCQ single, MCQ multi, T/F, button)
3. Theme + template system (5 starter themes, layout templates per slide)
4. Per-course media library + Unsplash search + Lucide icon picker
5. SCORM 1.2 export (zip download per published course)
6. Optional AI quiz generation toggle on document upload (extends existing pipeline)
7. Self-enrol catalog page + admin enrol UI
8. CSV reporting (per-learner, per-course)
9. Email notifications (assigned, due, overdue, completed)
10. Stripe pay-as-you-go billing wiring
11. Postgres migration from SQLite for prod
12. WCAG 2.1 AA pass on all new surfaces
13. GDPR DSAR + retention endpoints
14. Learner activity audit log (extend existing `AuditLog`)

### Out of scope for V1 (deferred to V2/V3 - DO NOT BUILD)

SCORM 2004, xAPI, multi-author, review workflow, real-time collab, configurable hierarchy, tenant question bank, drag-match assessment, configurable completion rules, course versioning, AI image gen, custom CSS per tenant, custom domains, translation, PWA, native mobile, EU region, SAML/SCIM, auto-enrol rules, HRIS, calendar/Zoom, Slack/Teams notifications, per-cohort reporting, custom metrics, enterprise tier billing, SOC 2.

---

## 1. Build Order (Sequencing)

Execute in this order. Each phase is independently testable.

| Phase | Task | Files touched | Acceptance |
|---|---|---|---|
| P1 | Postgres migration scaffolding | `database.py`, `alembic/` (new), `.env.example` | App boots against Postgres locally |
| P2 | Schema additions (block model, themes, media, enrolment audit) | `models/models.py`, alembic migration | Tables exist, FKs valid |
| P3 | Block + slide CRUD service | `services/block_service.py` (new), `routers/courses.py` | API tests pass |
| P4 | Theme registry + template system | `services/theme_service.py` (new), seed data | Themes available via API |
| P5 | Media library + Unsplash + Lucide | `services/media_service.py` (new), `routers/media.py` (new) | Upload, search, list |
| P6 | SCORM 1.2 exporter | `services/scorm_service.py` (new), `routers/scorm.py` (new) | Validates against testing tool |
| P7 | AI quiz gen toggle | extend `script_service.py`, `routers/courses.py` | Toggle flag respected |
| P8 | Catalog + self-enrol + admin enrol | `routers/catalog.py` (new), extend `enrollments` | Trainee can self-enrol |
| P9 | Email notifications | `services/notification_service.py` (new), worker queue | Email sent on event |
| P10 | CSV reporting | `routers/reports.py` (new) | CSV downloads correctly |
| P11 | Stripe billing | `services/billing_service.py` (new), `routers/billing.py` (new), webhook | Payment + receipt |
| P12 | Frontend block editor | new React components under `frontend/src/editor/` | Drag-drop works |
| P13 | Frontend catalog + learner shell | new React components | Self-enrol + play course |
| P14 | GDPR endpoints + retention job | extend `routers/users.py`, cron | DSAR returns user data |
| P15 | WCAG 2.1 AA audit + remediation | all new surfaces | axe-core CI passes |

---

## 2. Data Model Additions

Add to `backend/models/models.py`. All new tables. Do not modify existing tables except where noted.

### 2.1 New tables

```python
class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    position = Column(Integer, nullable=False)  # ordering within course
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    __table_args__ = (Index("idx_module_course_pos", "course_id", "position"),)


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    module = relationship("Module", back_populates="lessons")
    slides = relationship("Slide", back_populates="lesson", cascade="all, delete-orphan")


class Slide(Base):
    __tablename__ = "slides"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=True)
    position = Column(Integer, nullable=False)
    layout = Column(String(100), nullable=False, default="single-column")  # template id
    blocks = Column(JSON, nullable=False, default=list)  # array of block objects, see Section 4
    notes = Column(Text, nullable=True)  # speaker notes, hidden from learner
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    lesson = relationship("Lesson", back_populates="slides")


class Theme(Base):
    __tablename__ = "themes"
    id = Column(Integer, primary_key=True)
    slug = Column(String(50), unique=True, nullable=False)  # e.g. "corporate", "minimal"
    name = Column(String(255), nullable=False)
    tokens = Column(JSON, nullable=False)  # full token set, see Section 5
    is_system = Column(Boolean, default=True)  # system-seeded vs user-created
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CourseTheme(Base):
    """Course to theme assignment with optional overrides."""
    __tablename__ = "course_themes"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    overrides = Column(JSON, nullable=True)  # partial token overrides on top of theme


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    kind = Column(String(50), nullable=False)  # image, video, audio, document
    filename = Column(String(500), nullable=False)
    storage_key = Column(String(1000), nullable=False)  # S3 key or local path
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)  # for images/video
    height = Column(Integer, nullable=True)
    duration_s = Column(Float, nullable=True)  # for video/audio
    alt_text = Column(String(1000), nullable=True)  # accessibility (required for images)
    source = Column(String(50), nullable=False, default="upload")  # upload | unsplash | lucide
    source_ref = Column(String(500), nullable=True)  # original Unsplash URL etc.
    created_at = Column(DateTime, default=datetime.utcnow)


class ScormPackage(Base):
    """Track exported SCORM packages for re-download and audit."""
    __tablename__ = "scorm_packages"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    version = Column(String(50), nullable=False)  # "1.2"
    export_version = Column(Integer, nullable=False)  # incrementing per export
    storage_key = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    exported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    exported_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(50), nullable=False)  # assigned | due | overdue | completed
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    payload = Column(JSON, nullable=True)
    sent_email_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BillingAccount(Base):
    __tablename__ = "billing_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    plan = Column(String(50), nullable=False, default="payg")  # payg | enterprise (V2)
    created_at = Column(DateTime, default=datetime.utcnow)


class BillingTransaction(Base):
    __tablename__ = "billing_transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("billing_accounts.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=True)
    stripe_payment_intent = Column(String(255), unique=True, nullable=True)
    amount_pence = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="GBP")
    status = Column(String(50), nullable=False)  # pending | succeeded | failed | refunded
    created_at = Column(DateTime, default=datetime.utcnow)


class DataDeletionRequest(Base):
    """GDPR right-to-be-forgotten requests."""
    __tablename__ = "data_deletion_requests"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")  # pending | processing | completed | rejected
```

### 2.2 Existing table modifications

`Course`:

```python
# Add to Course
catalog_visible = Column(Boolean, default=False, nullable=False)  # show in self-enrol catalog
self_enrol_enabled = Column(Boolean, default=False, nullable=False)
price_pence = Column(Integer, default=0, nullable=False)  # 0 = free
estimated_minutes = Column(Integer, nullable=True)
pass_threshold = Column(Integer, default=80, nullable=False)  # quiz score % required
modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
```

`Enrollment`:

```python
# Add to Enrollment
score = Column(Float, nullable=True)  # final assessment score 0-100
last_slide_id = Column(Integer, ForeignKey("slides.id"), nullable=True)  # resume point
time_spent_s = Column(Integer, default=0, nullable=False)
due_date = Column(DateTime, nullable=True)  # admin-set deadline
assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
```

### 2.3 Migration approach

Use Alembic. Generate migration:

```bash
alembic revision --autogenerate -m "v1_manual_course_creator"
alembic upgrade head
```

Provide a separate seed script `scripts/seed_themes.py` that inserts the 5 starter themes (Section 5).

---

## 3. Backend Endpoints (REST API)

All endpoints under `/api/`. JWT-protected via existing `auth_middleware`. Apply role checks.

### 3.1 Course structure

```
POST   /api/courses/{course_id}/modules                  -> create module       [creator]
PATCH  /api/courses/{course_id}/modules/{id}             -> rename, reorder     [creator]
DELETE /api/courses/{course_id}/modules/{id}             -> delete + cascade    [creator]
POST   /api/modules/{module_id}/lessons                  -> create lesson       [creator]
PATCH  /api/lessons/{id}                                 -> rename, reorder     [creator]
DELETE /api/lessons/{id}                                 -> delete + cascade    [creator]
POST   /api/lessons/{lesson_id}/slides                   -> create slide        [creator]
GET    /api/slides/{id}                                  -> read slide          [creator|trainee*]
PATCH  /api/slides/{id}                                  -> update blocks       [creator]
DELETE /api/slides/{id}                                  -> delete              [creator]
POST   /api/slides/{id}/duplicate                        -> clone slide         [creator]
POST   /api/courses/{course_id}/reorder                  -> bulk reorder        [creator]
```

(*) trainee can read slide only if enrolled and slide belongs to a published course.

### 3.2 Themes

```
GET    /api/themes                                       -> list themes         [any]
GET    /api/themes/{slug}                                -> theme detail        [any]
GET    /api/courses/{course_id}/theme                    -> course theme + overrides
PUT    /api/courses/{course_id}/theme                    -> set theme + overrides [creator]
```

### 3.3 Media

```
POST   /api/courses/{course_id}/media                    -> upload (multipart)  [creator]
GET    /api/courses/{course_id}/media                    -> list assets         [creator]
DELETE /api/media/{id}                                   -> delete              [creator]
GET    /api/media/unsplash/search?q=...                  -> proxy Unsplash      [creator]
POST   /api/courses/{course_id}/media/from-unsplash      -> import to course    [creator]
GET    /api/media/lucide/search?q=...                    -> Lucide icon list    [creator]
```

### 3.4 SCORM export

```
POST   /api/courses/{course_id}/scorm/export             -> trigger build       [creator]
GET    /api/courses/{course_id}/scorm/packages           -> list past exports   [creator]
GET    /api/scorm/packages/{id}/download                 -> signed URL or stream
```

### 3.5 AI quiz gen toggle

Extend existing document upload endpoint:

```
POST   /api/courses/{course_id}/ingest                   -> body: { file, generate_quiz: bool, depth: int }
```

`generate_quiz=true` triggers existing `script_service.py` to draft questions for each lesson, returned as draft blocks for author review (not auto-published).

### 3.6 Catalog + enrolment

```
GET    /api/catalog                                      -> public-visible courses [trainee]
POST   /api/catalog/{course_id}/enrol                    -> self-enrol             [trainee]
POST   /api/courses/{course_id}/enrol                    -> admin enrol N users    [admin|creator]
                                                            body: { user_ids: [...], due_date? }
DELETE /api/enrollments/{id}                             -> unenrol                [admin|self]
```

### 3.7 Reporting

```
GET    /api/reports/learner/{user_id}.csv                -> per-learner CSV     [admin]
GET    /api/reports/course/{course_id}.csv               -> per-course CSV      [creator|admin]
GET    /api/reports/learner/{user_id}                    -> JSON view           [admin|self]
GET    /api/reports/course/{course_id}                   -> JSON view           [creator|admin]
```

CSV columns:
- Learner CSV: `course_title, enrolled_at, completed_at, progress_%, score, time_spent_s, due_date, status`
- Course CSV: `learner_email, learner_name, enrolled_at, completed_at, progress_%, score, time_spent_s, status`

### 3.8 Billing

```
POST   /api/billing/checkout                             -> create Stripe session [trainee]
                                                            body: { course_id }
POST   /api/billing/webhook                              -> Stripe webhook       [unauthenticated, signed]
GET    /api/billing/transactions                         -> own transactions     [self]
```

### 3.9 Notifications

```
GET    /api/notifications                                -> my notifications     [self]
PATCH  /api/notifications/{id}/read                      -> mark read            [self]
```

Email send is server-side, triggered by domain events. No public endpoint for sending.

### 3.10 GDPR

```
POST   /api/users/me/data-export                         -> async, emails JSON   [self]
POST   /api/users/me/delete                              -> creates DataDeletionRequest [self]
GET    /api/admin/data-deletion-requests                 -> list                 [admin]
POST   /api/admin/data-deletion-requests/{id}/process    -> hard-delete          [admin]
```

---

## 4. Block Taxonomy

All blocks stored as JSON inside `Slide.blocks` array. Each block has a stable `id` (UUIDv4), `type`, and `props`.

### 4.1 Common shape

```json
{
  "id": "b_8f3a2c10-...",
  "type": "heading",
  "props": { ... },
  "layout": { "col_start": 1, "col_span": 12, "row_start": 1, "row_span": 1 }
}
```

`layout` is a 12-column grid (Wix-style). Slides have `layout` template that defines available rows/columns.

### 4.2 Block types (V1)

| Type | Props | Notes |
|---|---|---|
| `heading` | `text`, `level (1-3)`, `align` | h1, h2, h3 only |
| `paragraph` | `text` (rich, HTML-sanitised), `align` | Tiptap output |
| `image` | `media_id`, `alt`, `caption`, `fit (cover|contain)`, `radius` | `alt` required for WCAG |
| `video` | `media_id` OR `url`, `poster`, `controls`, `autoplay (false)` | mp4/webm |
| `audio` | `media_id`, `transcript`, `controls` | transcript required for WCAG |
| `divider` | `style (solid|dashed)`, `thickness` | |
| `spacer` | `height_px` | layout aid |
| `bullets` | `items[]`, `style (bullet|number)` | |
| `accordion` | `panels[]: [{ title, body_blocks[] }]` | nested blocks |
| `button` | `label`, `action (next|prev|external|complete)`, `url?` | |
| `mcq_single` | `question`, `options: [{ id, text, correct }]`, `feedback`, `points` | exactly one correct |
| `mcq_multi` | `question`, `options: [{ id, text, correct }]`, `feedback`, `points` | one or more correct |
| `tf` | `question`, `correct_answer (true|false)`, `feedback`, `points` | |

### 4.3 Slide layouts (templates)

Defined as JSON, stored in `services/slide_layouts.py`:

```python
LAYOUTS = {
  "single-column":   { "rows": 1, "cols": 12, "regions": [{"col": 1, "span": 12}] },
  "two-column":      { "rows": 1, "cols": 12, "regions": [{"col": 1, "span": 6}, {"col": 7, "span": 6}] },
  "title-content":   { "rows": 2, "cols": 12, "regions": [{"row": 1, "span": 12}, {"row": 2, "span": 12}] },
  "image-left":      { "rows": 1, "cols": 12, "regions": [{"col": 1, "span": 5, "type": "image"}, {"col": 6, "span": 7}] },
  "image-right":     { "rows": 1, "cols": 12, "regions": [{"col": 1, "span": 7}, {"col": 8, "span": 5, "type": "image"}] },
  "centered":        { "rows": 1, "cols": 12, "regions": [{"col": 3, "span": 8}] },
  "quiz":            { "rows": 1, "cols": 12, "regions": [{"col": 2, "span": 10, "type": "assessment"}] }
}
```

### 4.4 Block validation

Validate on PATCH `/api/slides/{id}`. Reject if:

- Image block missing `alt` text
- Audio/video block missing transcript
- MCQ has zero correct options (single must have exactly 1, multi >= 1)
- Block layout overlaps another block on same row
- Unknown block type

---

## 5. Theme System

5 starter themes seeded at first boot. Stored in `themes` table.

### 5.1 Token schema

```json
{
  "colors": {
    "primary": "#1F3A5F",
    "secondary": "#6366F1",
    "accent": "#F59E0B",
    "bg": "#FFFFFF",
    "text": "#1F2937",
    "muted": "#6B7280",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444"
  },
  "typography": {
    "body_family": "Inter, system-ui, sans-serif",
    "heading_family": "Poppins, system-ui, sans-serif",
    "scale": { "h1": 32, "h2": 24, "h3": 20, "body": 16, "small": 14 },
    "line_height": 1.5
  },
  "spacing": { "unit": 8, "slide_padding": 48 },
  "radius": { "sm": 4, "md": 8, "lg": 16 },
  "buttons": { "style": "rounded", "weight": 500 },
  "shadows": { "sm": "0 1px 2px rgba(0,0,0,0.05)", "md": "0 4px 6px rgba(0,0,0,0.1)" }
}
```

### 5.2 Starter themes

1. **Corporate** - navy `#1F3A5F`, indigo `#6366F1`, Inter/Poppins
2. **Modern** - gradient primary (purple to pink), large type, rounded
3. **Minimal** - black/white only, mono-spaced headings, no shadows
4. **Compliance** - high contrast (black on white), Atkinson Hyperlegible font, dense spacing
5. **Branded** - neutral defaults, designed to be overridden by tenant `WhiteLabelConfig`

### 5.3 Theme application

Frontend resolves theme tokens at slide render time:

```js
// pseudocode
const tokens = { ...theme.tokens, ...courseTheme.overrides };
applyCssVariables(tokens);
```

CSS variables: `--color-primary`, `--color-text`, `--font-body`, `--space-unit`, `--radius-md`, etc.

---

## 6. SCORM 1.2 Export

New service: `backend/services/scorm_service.py`

### 6.1 Output package structure

```
course_<id>_v<n>.zip
├── imsmanifest.xml          (SCORM 1.2 manifest)
├── adlcp_rootv1p2.xsd
├── ims_xml.xsd
├── imscp_rootv1p1p2.xsd
├── imsmd_rootv1p2p1.xsd
├── index.html               (entry point, loads runtime)
├── scorm_runtime.js         (LMS API wrapper, calls window.parent.API.LMSInitialize, etc.)
├── player.js                (block renderer)
├── styles.css               (compiled theme)
├── content/
│   ├── slide_001.json       (slide definitions)
│   ├── slide_002.json
│   └── ...
├── media/
│   ├── img_001.jpg
│   ├── vid_001.mp4
│   └── ...
└── meta/
    └── course.json          (course metadata, hierarchy)
```

### 6.2 imsmanifest.xml template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="LMS_COURSE_{course_id}_V{export_version}"
          version="1.2"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                              http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd
                              http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>{course.title}</title>
      <item identifier="ITEM-1" identifierref="RES-1">
        <title>{course.title}</title>
        <adlcp:masteryscore>{course.pass_threshold}</adlcp:masteryscore>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
      <!-- enumerate every file in package -->
    </resource>
  </resources>
</manifest>
```

### 6.3 SCORM 1.2 runtime API surface

`scorm_runtime.js` must call (and gracefully degrade if API absent):

- `LMSInitialize("")` on load
- `LMSSetValue("cmi.core.lesson_status", "incomplete" | "completed" | "passed" | "failed")`
- `LMSSetValue("cmi.core.score.raw", "0".."100")`
- `LMSSetValue("cmi.core.lesson_location", "{slide_id}")`
- `LMSSetValue("cmi.core.session_time", "HH:MM:SS")`
- `LMSCommit("")` after each significant change
- `LMSFinish("")` on unload

Player tracks:
- Slide visited (sets lesson_location)
- Quiz attempt (updates score.raw, status)
- Completion = pass_threshold reached OR all slides visited if no quiz

### 6.4 SCORM service signature

```python
# backend/services/scorm_service.py

class ScormPackager:
    def __init__(self, db: Session, storage: StorageBackend):
        ...

    def export(self, course_id: int, exported_by: int) -> ScormPackage:
        """Build SCORM 1.2 zip, store, return DB record."""
        # 1. Load course + modules + lessons + slides + theme + media
        # 2. Resolve all media references, copy into package
        # 3. Compile theme tokens to CSS
        # 4. Render slides to slide_NNN.json
        # 5. Generate imsmanifest.xml
        # 6. Bundle scorm_runtime.js + player.js (from static templates)
        # 7. Zip + store at storage.put(...)
        # 8. Insert ScormPackage row
        # 9. Return record
```

### 6.5 Validation

Test packages against:
- ADL SCORM 1.2 Test Suite (https://adlnet.gov/projects/scorm/)
- SCORM Cloud import test
- Local Reload editor validation

Acceptance: all 3 must pass before merge.

---

## 7. AI Quiz Generation Toggle

Extend existing `services/script_service.py` (it already does Claude calls).

### 7.1 Endpoint behaviour

```
POST /api/courses/{course_id}/ingest
Content-Type: multipart/form-data

file: <bytes>
generate_quiz: true|false   (default false)
quiz_per_lesson: 3          (default 3, max 10)
quiz_difficulty: easy|medium|hard  (default medium)
```

When `generate_quiz=true`:

1. Extract document structure (existing `document_service.py`)
2. Map H1 -> Module, H2 -> Lesson, paragraphs -> slide blocks
3. For each lesson, call Claude with prompt template (Section 7.2)
4. Insert quiz questions as **draft** blocks at end of lesson
5. Mark slide with `metadata.is_ai_draft = true` so editor shows "Review AI questions" banner

### 7.2 Claude prompt template

```
You are creating quiz questions for an LMS course.

Lesson title: {lesson_title}
Lesson content (paraphrased):
{lesson_text}

Generate exactly {N} questions. Mix question types:
- mcq_single: most common
- mcq_multi: where multiple facts must be combined
- tf: where a clear truth/falsehood exists

Difficulty: {difficulty}

Return JSON only:
[
  { "type": "mcq_single", "question": "...", "options": [{"text":"...", "correct": true}, ...], "feedback": "..." },
  ...
]

Constraints:
- mcq_single: exactly one option marked correct
- mcq_multi: at least one, at most 3 options correct
- tf: include a 1-sentence feedback explaining the answer
- Questions must be answerable from the lesson content only
- No trick questions, no ambiguity
- UK English spelling
```

Validate the response. Reject and re-prompt up to 2 times if invalid JSON or constraint violation.

---

## 8. Catalog + Self-Enrol

### 8.1 Catalog endpoint

`GET /api/catalog?q=&category=&page=&limit=`

Returns courses where `catalog_visible = true AND status = published`. Paginated. Include `price_pence`, `estimated_minutes`, `enrolment_count`, `cover_image`.

### 8.2 Self-enrol

If `course.price_pence == 0`: insert `Enrollment` directly.

If `course.price_pence > 0`: redirect to Stripe Checkout. On webhook `payment_intent.succeeded`, insert `Enrollment` and `BillingTransaction`.

### 8.3 Admin enrol

`POST /api/courses/{id}/enrol` body `{ user_ids: [int], due_date?: ISO8601 }`

For each user_id, upsert Enrollment with `assigned_by = current_user.id`, `due_date`, fire `notification: assigned`.

---

## 9. Email Notifications

New service: `backend/services/notification_service.py`

### 9.1 Events

| Event | Trigger | Email subject |
|---|---|---|
| `assigned` | Admin enrols learner | "You've been assigned: {course_title}" |
| `due_soon` | Cron, 7 days before due_date | "Reminder: {course_title} due in 7 days" |
| `overdue` | Cron, daily after due_date | "Overdue: {course_title}" |
| `completed` | Enrollment.completed transitions to true | "Course completed: {course_title}" |

### 9.2 Implementation

- Use Postmark or AWS SES (`MAIL_PROVIDER` env var)
- Templates as Jinja2 in `backend/templates/email/`
- Async via `arq` or `RQ` queue (Redis-backed)
- Cron job for `due_soon` and `overdue` runs hourly via `services/cron.py`
- Notification record created always, email send attempted with retry (3 attempts, exponential backoff)

### 9.3 Per-learner opt-out

Add `User.email_notifications_enabled` boolean (default true). Skip send if false.

---

## 10. CSV Reporting

New router: `backend/routers/reports.py`

### 10.1 Streaming CSV response

```python
def stream_csv(rows: Iterator[dict], headers: list[str]) -> StreamingResponse:
    def generate():
        yield ",".join(headers) + "\n"
        for row in rows:
            yield ",".join(_csv_escape(row.get(h, "")) for h in headers) + "\n"
    return StreamingResponse(generate(), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=report.csv"})
```

Always escape values containing `,`, `"`, or `\n`.

---

## 11. Stripe Billing

### 11.1 Setup

- Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` to `.env`
- Use `stripe-python` package
- Create products in Stripe matching `Course.id` via metadata

### 11.2 Checkout flow

```python
def create_checkout_session(user, course):
    return stripe.checkout.Session.create(
        mode="payment",
        success_url=f"{BASE_URL}/learn/{course.id}?paid=1",
        cancel_url=f"{BASE_URL}/catalog/{course.id}",
        line_items=[{
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": course.title},
                "unit_amount": course.price_pence,
            },
            "quantity": 1,
        }],
        customer_email=user.email,
        metadata={"course_id": course.id, "user_id": user.id},
    )
```

### 11.3 Webhook

Verify signature with `stripe.Webhook.construct_event`. Handle:
- `checkout.session.completed` -> create Enrollment, BillingTransaction (succeeded)
- `payment_intent.payment_failed` -> log, BillingTransaction (failed)
- `charge.refunded` -> mark BillingTransaction (refunded), unenrol if policy

### 11.4 Idempotency

Webhook handler must be idempotent. Use `stripe_payment_intent` unique constraint on BillingTransaction.

---

## 12. Frontend (React)

### 12.1 Structure

```
frontend/src/
├── editor/                  # block-based course editor
│   ├── BlockEditor.jsx      # main canvas
│   ├── BlockPalette.jsx     # sidebar of draggable blocks
│   ├── BlockRenderer.jsx    # renders a single block
│   ├── blocks/              # one component per block type
│   │   ├── HeadingBlock.jsx
│   │   ├── ParagraphBlock.jsx (Tiptap)
│   │   ├── ImageBlock.jsx
│   │   ├── McqSingleBlock.jsx
│   │   └── ...
│   ├── ThemePanel.jsx       # theme picker + token overrides
│   ├── MediaPicker.jsx      # upload + Unsplash + Lucide
│   └── SlideTree.jsx        # left nav: course > module > lesson > slide
├── catalog/
│   ├── CatalogPage.jsx
│   └── CatalogCard.jsx
├── player/
│   ├── PlayerShell.jsx      # learner-facing course player
│   └── BlockViewer.jsx      # read-only block render
├── reports/
│   └── ReportTable.jsx
└── shared/
    ├── api.js               # fetch wrapper with auth
    ├── auth.js
    └── tokens.js            # CSS var injection from theme
```

### 12.2 Drag-and-drop library

Use `@dnd-kit/core` + `@dnd-kit/sortable`. Reasons: keyboard accessible (WCAG critical), no jQuery dependency, modern API.

### 12.3 Rich text

Use Tiptap (`@tiptap/react`, `@tiptap/starter-kit`). Sanitise output with DOMPurify before save.

### 12.4 State management

React context per course-edit session. Persist on slide blur via debounced PATCH (2 second debounce).

### 12.5 Accessibility requirements (WCAG 2.1 AA)

- All draggable items also operable via keyboard (arrow keys + Enter)
- All form fields have visible labels
- Colour contrast min 4.5:1 for body, 3:1 for large text
- Focus indicators visible on all interactives
- ARIA live regions for status updates ("Slide saved")
- Skip-to-content link on player
- Captions/transcripts mandatory on video/audio (validated server-side)
- Run `axe-core` in CI on every PR via `@axe-core/playwright`

---

## 13. Storage Backend

### 13.1 Abstraction

```python
# backend/services/storage.py
class StorageBackend(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def signed_url(self, key: str, expires_s: int = 300) -> str: ...
```

### 13.2 Implementations

- `LocalStorage` for dev (writes to `backend/uploads/`)
- `S3Storage` for prod (boto3, eu-west-2 bucket)

Selected via `STORAGE_BACKEND` env var.

---

## 14. Postgres Migration

### 14.1 Steps

1. Add `psycopg[binary]` to `backend/requirements.txt`
2. Update `database.py` to read `DATABASE_URL` (Postgres in prod, SQLite for unit tests)
3. Add Alembic: `alembic init alembic`, configure env.py to import models
4. Generate baseline migration matching current schema
5. Generate v1 additions migration (Section 2)
6. Add migration runner to startup hook
7. Update Dockerfile to wait for DB

### 14.2 Connection pool

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

---

## 15. GDPR Endpoints

### 15.1 Data export

`POST /api/users/me/data-export`

- Queues async job
- Job collects: User row, Sessions, Enrollments, Notifications, BillingTransactions, AuditLog entries (last 90 days)
- Bundles as JSON, uploads to storage with 7-day signed URL
- Emails URL to user

### 15.2 Deletion

`POST /api/users/me/delete`

- Creates `DataDeletionRequest` (status=pending)
- Admin must process within 30 days (GDPR Art. 12)
- On process: hard-delete User and cascade. Anonymise BillingTransaction (retain for tax records, replace user_id with NULL, replace email with `deleted_<id>@redacted`)

### 15.3 Retention job

Cron weekly:
- Delete Sessions older than 30 days
- Delete LoginAttempts older than 90 days
- Delete Notifications older than 365 days
- Anonymise AuditLog entries older than 730 days (replace user_id with NULL, retain action+resource for compliance)

---

## 16. Audit Log Extensions

Extend writes to `AuditLog` for these new actions:

| Action | Resource type | When |
|---|---|---|
| `slide.create` | slide | POST /api/lessons/.../slides |
| `slide.update` | slide | PATCH /api/slides/{id} |
| `slide.delete` | slide | DELETE /api/slides/{id} |
| `course.publish` | course | status -> published |
| `course.scorm_export` | course | scorm export complete |
| `enrolment.create` | enrollment | self or admin |
| `enrolment.complete` | enrollment | learner finishes |
| `media.upload` | media_asset | upload |
| `notification.send` | notification | email sent |
| `billing.charge` | billing_transaction | webhook |
| `data.export_requested` | user | DSAR |
| `data.deletion_requested` | user | DSAR |
| `data.deletion_processed` | user | admin completes |

---

## 17. Acceptance Criteria

A reviewer must be able to verify each of the following.

### 17.1 Authoring

1. Creator logs in, creates course, adds module, lesson, slide.
2. Creator drags 5 different block types onto a slide, saves, reloads, blocks persist.
3. Creator selects a theme, slide preview updates immediately.
4. Creator overrides primary colour, save, reload, override persists.
5. Creator uploads a JPG, sets alt text, drops into image block, learner sees image.
6. Creator searches Unsplash, picks photo, it appears in course media library.
7. Creator picks a Lucide icon, drops into a heading.
8. Creator uploads a `.docx` with `generate_quiz=true`, draft questions appear in lessons marked for review.
9. Creator marks course `published`, `catalog_visible=true`, `self_enrol_enabled=true`, sets price £9.99.
10. Creator exports SCORM, downloads zip, uploads to SCORM Cloud, course plays and reports completion.

### 17.2 Learner

1. Trainee browses catalog, finds course, pays £9.99 via Stripe test card, lands on player.
2. Player loads first slide, blocks render correctly with theme.
3. Learner navigates next/prev, lesson_location updates server-side.
4. Learner takes quiz, passes, course completes, completion email arrives.
5. Learner refreshes mid-course, resumes at last_slide_id.

### 17.3 Admin

1. Admin assigns course to 3 learners with due_date 14 days out.
2. Each learner gets `assigned` email within 1 minute.
3. 7 days before due_date, each learner gets `due_soon` email.
4. After due_date, daily `overdue` emails until completed or unenrolled.
5. Admin downloads `course_{id}.csv`, opens in Excel, sees all learners with progress.
6. Admin downloads `learner_{id}.csv`, sees all that learner's enrolments.

### 17.4 Compliance

1. axe-core CI run reports zero WCAG 2.1 AA violations on editor, player, catalog.
2. Trainee POSTs to `/api/users/me/data-export`, receives JSON within 5 minutes.
3. Trainee POSTs to `/api/users/me/delete`, sees pending request in account.
4. Admin processes deletion, user record gone, audit trail anonymised.
5. SCORM 1.2 package validates against ADL Test Suite, SCORM Cloud, Reload.
6. Penetration test: no SQL injection, XSS, CSRF, IDOR on new endpoints.

### 17.5 Non-functional

- API p95 latency < 300ms for slide read, < 800ms for slide save
- SCORM export < 30s for a 100-slide course
- Frontend initial load < 3s on 4G simulated
- Player works offline for current slide once loaded (basic service worker not required for V1, but caching headers correct)

---

## 18. Testing

### 18.1 Backend

- pytest unit tests for: block validation, SCORM manifest gen, theme token merge, CSV escape, Stripe webhook idempotency
- pytest integration tests against ephemeral Postgres (testcontainers)
- Coverage target: 80% on new modules

### 18.2 Frontend

- Vitest unit tests for: block reducer, theme apply, validation
- Playwright e2e: full author flow, full learner flow
- @axe-core/playwright on every page

### 18.3 SCORM compliance

- Automated test: build sample course, package, run through ADL Test Suite headless
- Manual test: upload to SCORM Cloud once per release

### 18.4 CI pipeline (GitHub Actions)

```yaml
jobs:
  backend: pytest + coverage + ruff + mypy
  frontend: vitest + eslint + axe-core via playwright
  e2e: playwright suite against staging
  scorm: ADL test suite
```

---

## 19. Environment Variables

Add to `.env.example`:

```
# Database
DATABASE_URL=postgresql://lms:lms@localhost:5432/lms

# Storage
STORAGE_BACKEND=local           # local | s3
S3_BUCKET=lms-media-uk
S3_REGION=eu-west-2
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Email
MAIL_PROVIDER=postmark          # postmark | ses
POSTMARK_TOKEN=
MAIL_FROM=noreply@example.com

# Unsplash
UNSPLASH_ACCESS_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=

# Frontend base URL (for Stripe redirect)
BASE_URL=https://app.example.com

# Queue
REDIS_URL=redis://localhost:6379

# Feature flags (optional overrides)
FEATURE_AI_QUIZ_GEN=true
```

---

## 20. Definition of Done

V1 is done when:

1. All 15 phases (Section 1) merged to main.
2. Acceptance criteria (Section 17) all green.
3. CI pipeline (Section 18.4) green on main.
4. SCORM 1.2 package validated against ADL + SCORM Cloud + Reload.
5. WCAG 2.1 AA pass via axe-core (zero violations on new surfaces).
6. Stripe live mode tested end-to-end (one real £0.30 charge, refunded).
7. Postgres prod migration rehearsed against snapshot.
8. Design partner has authored 1 course end-to-end and exported it.
9. README updated with new env vars + run instructions.
10. CHANGELOG entry written.

---

## 21. Open Questions for User

These need answers before P11 (Stripe) and P9 (Email):

1. Stripe account: existing or new? UK-registered?
2. Email provider preference: Postmark, AWS SES, SendGrid?
3. SCORM destination LMS for design partner testing: which one?
4. Price floor for catalog: any minimum charge (e.g. £1)? Free courses allowed?
5. Tax handling: use Stripe Tax (automated VAT) or manual?

Pause and ask before building those phases. Everything else (P1-P8, P10, P12-P15) can proceed without further input.

---

**End of build spec.**
