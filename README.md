# Customer Research Agent

An internal tool for qualitative research teams. Upload interview recordings or transcripts, get structured AI analysis, and synthesize findings across your entire interview library into a living research board.

---

## What it does

**Per interview**
- Accepts audio, video, or text transcript files
- Transcribes media via OpenAI Whisper (multilingual)
- Extracts structured insights using Claude: pain points, goals, objections, feature requests, workarounds, emotional moments, and strong quotes
- Generates an executive summary and themed report
- Builds an interviewee profile from the transcript (role, age range, industry, tech level, location, financial context) and prompts you to fill in anything it couldn't find

**Across a project**
- Manually trigger cross-interview synthesis at any time
- Claude reads every interview's insights and profiles together and produces a Research Board:
  - Recurring themes (with frequency bars and strength ratings)
  - Top pain points (with supporting quotes)
  - Non-obvious patterns (behavioural, demographic, contextual, emotional)
  - Unique one-off insights worth noting
  - Demographic breakdown of who you talked to
  - Open questions and data gaps

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│              React + Vite + TailwindCSS                 │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP  /api/*
┌──────────────────────▼──────────────────────────────────┐
│                    FastAPI (Python)                      │
│  /api/projects    /api/interviews    /api/interviews/:id │
│                                                          │
│  BackgroundTasks ──► board synthesis (same process)      │
└──────┬───────────────────────────┬───────────────────────┘
       │ asyncpg                   │ arq (Redis queue)
┌──────▼──────┐          ┌─────────▼────────────────────┐
│ PostgreSQL  │          │        arq Worker             │
│             │          │  1. Transcribe (Whisper API)  │
│  projects   │          │  2. Parse transcript          │
│  interviews │          │  3. Extract insights (Claude) │
│  analyses   │          │  4. Synthesize report (Claude)│
│  reports    │          │  5. Build interviewee profile │
│  profiles   │          └──────────────────────────────┘
│  boards     │
└─────────────┘
```

**Key design decisions**
- Interview processing runs in a Redis-backed worker queue (arq) so large files don't block the API
- Board synthesis runs as a FastAPI BackgroundTask — it's user-triggered and infrequent, so a full queue is overkill
- The Anthropic client is async throughout to avoid blocking the event loop
- Files are stored locally by default (`./uploads`); swap in S3 credentials to use object storage instead
- The frontend polls for status changes (every 3s while processing) — no websockets needed

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, TailwindCSS, React Query |
| Backend | FastAPI, SQLAlchemy (async), asyncpg |
| Worker | arq (async Redis queue) |
| Database | PostgreSQL 16 |
| Queue | Redis 7 |
| Transcription | OpenAI Whisper API |
| AI analysis | Anthropic Claude (Haiku for profiles, Sonnet for analysis + board synthesis) |
| File storage | Local disk / S3 |
| Serving (prod) | nginx reverse proxy → FastAPI |

---

## Running locally

**Prerequisites:** Python 3.12+, Node 20+, Docker (for Postgres + Redis)

```bash
# 1. Start Postgres and Redis
docker compose up -d db redis

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in API keys
uvicorn app.main:app --reload --port 8000

# 3. Worker (separate terminal)
cd backend && source venv/bin/activate
arq app.workers.pipeline.WorkerSettings

# 4. Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

App runs at `http://localhost:5173`. API docs at `http://localhost:8000/docs`.

Or use the convenience script:
```bash
bash scripts/dev.sh
```

---

## Deploying to EC2

```bash
# On your EC2 instance (Ubuntu, Docker installed)
git clone https://github.com/scorpus658/customerresearchagent.git
cd customerresearchagent

cp .env.example .env
nano .env   # set OPENAI_API_KEY and ANTHROPIC_API_KEY

docker compose up -d --build
```

The app is served on port 80. Open your EC2's public IP in a browser.

**To deploy updates:**
```bash
git pull && docker compose up -d --build
```

Make sure your EC2 security group allows inbound TCP on port 80.

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Whisper transcription |
| `ANTHROPIC_API_KEY` | Yes | Claude analysis and synthesis |
| `DATABASE_URL` | Auto (Docker) | Set by docker-compose |
| `REDIS_URL` | Auto (Docker) | Set by docker-compose |
| `S3_BUCKET` | No | Leave blank to use local disk |
| `AWS_ACCESS_KEY_ID` | No | Required if using S3 |
| `AWS_SECRET_ACCESS_KEY` | No | Required if using S3 |
| `UPLOAD_DIR` | No | Default: `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | No | Default: 500 |
