# Milestones

## v0.1 — LMS Foundation

**Shipped:** 2026-05-08
**Phases:** 1–8 (pre-GSD, tracked manually)

**What shipped:**
- FastAPI backend with JWT auth, role-based access (admin/creator/trainee)
- Admin panel: users, courses, audit logs, security, white-label, dev tools
- Basic course management with AI generation (topic + document)
- Course player (iframe-based)
- Learner portal at `/learn` — catalogue, course detail
- Creator portal at `/creator` — dashboard, course list, learner enrollments
- Path-prefix routing at `buildbench.uk/lms` via Traefik
- Deployed on Coolify with nixpacks staticfile provider

**Last phase:** 8 (creator portal)
