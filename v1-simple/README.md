# LMS Course Builder

AI-powered learning management system that converts uploaded documents (PDF/DOCX) into fully structured, interactive video-based learning courses using Claude.

## Quick Start

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# Install dependencies
pip install -r requirements.txt

# Run on port 8500
bash start.sh
```

Open `http://localhost:8500` in your browser.

## How It Works

**Creator flow:** Upload a PDF or DOCX document → Claude analyses the content and generates a structured course with modules, lessons (each containing a summary, video script, and quiz) → Review, rename, or delete modules/lessons → Publish the course for trainees.

**Trainee flow:** Select a published course → Work through lessons sequentially (gated progression) → Read the summary → Review the video script → Complete the quiz → Track your progress.

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `DATABASE_URL` | No | `sqlite:///data/lms.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `HOST` | No | `0.0.0.0` | Bind host |
| `PORT` | No | `8500` | Bind port |

## Docker

```bash
docker build -t lms-course-builder .
docker run -p 8500:8500 -e ANTHROPIC_API_KEY=sk-ant-... lms-course-builder
```

## White-Labelling

Override CSS custom properties to rebrand:

```css
:root {
    --color-primary: #2563eb;
    --color-primary-hover: #1d4ed8;
    --color-bg: #f8fafc;
    --color-surface: #ffffff;
    --color-text: #1e293b;
    --color-text-secondary: #64748b;
    --font-family: 'Inter', system-ui, sans-serif;
    --logo-url: url('/static/logo.png');
}
```

## ATLAS Integration

This application conforms to the ATLAS Integration Standard:

- `GET /health` — health check (returns `{status, version, uptime_seconds}`)
- `GET /ready` — readiness probe
- `atlas.yml` — service manifest
- Structured JSON logging to stdout
- All config via environment variables

## Tech Stack

- **Backend:** Python / FastAPI
- **Frontend:** React (single-file SPA)
- **Database:** SQLite
- **AI:** Anthropic Claude API
- **Container:** Docker

## v1 Limitations

- No authentication (planned for v2)
- Video scripts only — no actual video rendering
- No payment processing
