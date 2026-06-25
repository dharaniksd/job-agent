# 🤖 AI Job Application Agent

An AI-powered agent that parses your resume, finds matching jobs, auto-fills applications using browser automation, and lets you review anything it can't answer — all in one Docker-based app.

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER / BROWSER                                 │
│                        http://localhost:3000                                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ Next.js 14 + Tailwind + Recharts
                    ┌───────────────▼───────────────┐
                    │         FRONTEND               │
                    │  ┌─────────────────────────┐  │
                    │  │  Dashboard (KPIs/Charts)│  │
                    │  │  Resume Upload          │  │
                    │  │  Job Board + Match %    │  │
                    │  │  Applications Tracker   │  │
                    │  │  Review Queue (HITL)    │  │
                    │  │  LinkedIn OAuth Login   │  │
                    │  └──────────┬──────────────┘  │
                    └─────────────┼─────────────────┘
                                  │ REST API (axios)
                    ┌─────────────▼─────────────────┐
                    │         BACKEND                │
                    │      FastAPI + Python          │
                    │                                │
                    │  /api/auth/linkedin  ──► LinkedIn OAuth2
                    │  /api/resume/upload  ──► Resume Parser
                    │  /api/jobs/search    ──► Job Scraper
                    │  /api/applications/  ──► Auto-Apply Engine
                    │  /api/review/        ──► HITL Queue
                    │  /api/dashboard/     ──► Stats API
                    └──┬──────┬──────┬────┬──────────┘
                       │      │      │    │
          ┌────────────▼┐  ┌──▼──┐  │  ┌─▼──────────────────┐
          │  PostgreSQL  │  │Redis│  │  │   OpenAI GPT-4o     │
          │  (SQLAlchemy)│  │Queue│  │  │  • Resume parsing   │
          │  Users       │  └─────┘  │  │  • Job matching     │
          │  Resumes     │           │  │  • Form Q&A         │
          │  Jobs        │           │  └─────────────────────┘
          │  Applications│           │
          └──────────────┘           │
                    ┌────────────────▼──────────────────────┐
                    │         PLAYWRIGHT CONTAINER           │
                    │   Headless Chromium Browser            │
                    │                                        │
                    │   1. Open job application URL          │
                    │   2. Scan all form fields              │
                    │   3. AI fills known fields from resume │
                    │   4. Unknown fields → Review Queue     │
                    │   5. Submit form (or wait for human)   │
                    └───────────────────────────────────────┘
                                    │
                    ┌───────────────▼───────────────────────┐
                    │        EMAIL NOTIFICATIONS             │
                    │   SendGrid / SMTP                      │
                    │                                        │
                    │   ✅ Application submitted             │
                    │   🧑 Human input needed               │
                    │   ❌ Application failed                │
                    └───────────────────────────────────────┘
```

### Human-in-the-Loop (HITL) Flow

```
  Resume Upload
       │
       ▼
  GPT-4o parses → {name, skills, experience, roles}
       │
       ▼
  Job Scraper (Remotive + SerpAPI/Google Jobs)
       │
       ▼
  GPT-4o-mini scores each job → match % → filter > 50%
       │
       ▼
  User clicks "Auto Apply" on a job
       │
       ▼
  Playwright opens job URL
       │
  ┌────▼──────────────────────────────────┐
  │  For each form field:                  │
  │    AI confident? ──YES──► fill field   │
  │                   └─NO──► flag it     │
  └───────────────────────────────────────┘
       │
  ┌────▼──────────────┐    ┌───────────────────────┐
  │ Pending questions? │─YES─► Review Queue tab     │
  │                   │    │ + Email notification   │
  └────┬──────────────┘    │ User types answers     │
       │ NO                │ AI resumes & submits   │
       ▼                   └───────────────────────┘
  Submit form
       │
       ▼
  ✅ Submitted + Email sent
```

---

## 📁 Project Structure

```
job-agent/
├── docker-compose.yml          # One-command orchestration
├── .env.example                # Environment variable template
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py              # Async Alembic setup
│   │   └── versions/
│   │       └── 0001_initial.py # DB schema migration
│   └── app/
│       ├── main.py             # FastAPI app + routers
│       ├── api/
│       │   ├── auth.py         # LinkedIn OAuth2 + JWT
│       │   ├── resume.py       # Upload + parse resume
│       │   ├── jobs.py         # Search + match jobs
│       │   ├── applications.py # Start auto-apply
│       │   ├── review_queue.py # HITL queue
│       │   └── dashboard.py    # Stats endpoint
│       ├── core/
│       │   ├── auth.py         # JWT create/decode
│       │   ├── config.py       # Settings (pydantic)
│       │   └── database.py     # Async SQLAlchemy session
│       ├── models/
│       │   └── base.py         # User, Resume, Job, Application
│       └── services/
│           ├── resume_parser.py # pdfplumber + GPT-4o
│           ├── job_scraper.py   # Remotive + SerpAPI
│           ├── job_matcher.py   # GPT-4o-mini scoring
│           ├── auto_apply.py    # Playwright form filler
│           └── email.py         # SendGrid / SMTP
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json            # Next.js + recharts + axios
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/app/
│       ├── layout.tsx
│       ├── globals.css
│       └── page.tsx            # Full UI (Dashboard, Upload, Jobs, Review)
│
└── docker/
    └── playwright/
        ├── Dockerfile          # mcr.microsoft.com/playwright
        └── worker.py           # Background apply worker
```

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Step 1 — Clone & configure

```bash
# Copy project files to your machine, then:
cd job-agent

# Create your .env from the template
cp .env.example .env
```

Open `.env` and set at minimum:
```env
OPENAI_API_KEY=sk-...your-key-here...
SECRET_KEY=any-random-string-32-chars
```

### Step 2 — Build & start

```bash
docker compose up --build
```

> First build takes ~3–5 minutes (downloads Playwright + Node modules).
> Subsequent starts take ~15 seconds.

### Step 3 — Open the app

| Service | URL |
|---|---|
| **Frontend UI** | http://localhost:3000 |
| **API docs (Swagger)** | http://localhost:8000/docs |
| **API docs (ReDoc)** | http://localhost:8000/redoc |

---

## 🧪 Testing the App

### Manual test flow

**1. Upload resume**
```
→ Open http://localhost:3000
→ Click "upload" tab
→ Upload any PDF/DOCX resume
→ Wait ~10s for GPT-4o to parse it
→ Should see: name, skills, education extracted
```

**2. Find matching jobs**
```
→ Click "Find Matching Jobs" button
→ AI searches Remotive (free remote jobs, no API key needed)
→ Each job gets a match % score against your resume
→ Should see 5–20 jobs sorted by match score
```

**3. Auto-apply**
```
→ Click "Auto Apply" on any job
→ Playwright opens the job URL in headless Chrome
→ AI fills form fields from your resume
→ If AI is confident → submits automatically
→ If not → you land on "Review" tab with flagged questions
```

**4. Review queue**
```
→ Open "review" tab
→ Answer any flagged questions (e.g. "Why do you want this job?")
→ Click "Submit & Continue Application"
→ AI re-opens the form, fills everything, submits
```

**5. Dashboard**
```
→ Open "dashboard" tab
→ See: total apps, success rate, daily bar chart, status donut
```

### API testing (curl)

```bash
# Health check
curl http://localhost:8000/health

# Upload a resume
curl -X POST http://localhost:8000/api/resume/upload \
  -F "file=@/path/to/your-resume.pdf"

# Search jobs (replace RESUME_ID with the id from above)
curl "http://localhost:8000/api/jobs/search?resume_id=RESUME_ID"

# Get dashboard stats
curl http://localhost:8000/api/dashboard/stats

# Get pending review queue
curl http://localhost:8000/api/review/pending
```

---

## 🔑 Optional Features Setup

### 📧 Email Notifications

**Option A — SendGrid (recommended)**
1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier: 100 emails/day)
2. Create an API key → Sender Authentication → verify your domain/email
3. Add to `.env`:
```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxx
EMAIL_FROM=you@yourdomain.com
```

**Option B — Gmail SMTP**
1. Enable 2FA on your Google account
2. Generate an App Password: myaccount.google.com → Security → App Passwords
3. Add to `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=you@gmail.com
```

### 🔗 LinkedIn OAuth Login

1. Go to [linkedin.com/developers](https://www.linkedin.com/developers/apps)
2. Click **Create App** → fill in name, LinkedIn Page, logo
3. Under **Auth** tab → add Redirect URL:
   ```
   http://localhost:8000/api/auth/linkedin/callback
   ```
4. Copy **Client ID** and **Client Secret** to `.env`:
```env
LINKEDIN_CLIENT_ID=86xxxxxxxxxx
LINKEDIN_CLIENT_SECRET=xxxxxxxxxxxxxxxx
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/auth/linkedin/callback
```
5. Restart: `docker compose restart backend`

### 🔍 Google Jobs Search (SerpAPI)

Without SerpAPI, the app uses Remotive (free, remote jobs only).  
SerpAPI unlocks Google Jobs search across all job boards:

1. Sign up at [serpapi.com](https://serpapi.com) (100 free searches/month)
2. Add to `.env`:
```env
SERPAPI_KEY=your-serpapi-key
```

---

## ☁️ Deployment

### Railway (easiest — 1 click)
```bash
# 1. Push to GitHub
git init && git add . && git commit -m "Initial commit"
gh repo create job-agent --public --push

# 2. Go to railway.app → New Project → Deploy from GitHub
# 3. Set env vars in Railway dashboard
# 4. Railway auto-detects docker-compose.yml
```

### Fly.io
```bash
fly launch --name job-agent
fly secrets set OPENAI_API_KEY=sk-...
fly secrets set SECRET_KEY=your-secret
fly deploy
```

### DigitalOcean / Any VPS
```bash
# SSH into your server, then:
git clone https://github.com/you/job-agent.git
cd job-agent
cp .env.example .env && nano .env   # set your keys
docker compose up -d
```

---

## 🛡️ Important Notes

1. **Rate limits** — The app adds a delay between applications to avoid triggering bot detection
2. **Terms of Service** — Check each job site's ToS before using automated applications. LinkedIn and Indeed prohibit bots via their APIs/scraping
3. **Recommended job boards** — Remotive, Greenhouse, Lever, Workable (all support programmatic applications)
4. **Data privacy** — Your resume is stored locally in PostgreSQL inside Docker. Nothing is sent to third parties except: OpenAI (resume/job text) and SendGrid/LinkedIn (if configured)

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| `docker compose up` fails | Run `docker compose down -v` then `up --build` again |
| Backend can't connect to DB | Wait 10s for postgres to be healthy, then `docker compose restart backend` |
| Resume parse fails | Check `OPENAI_API_KEY` is set and has credits |
| No jobs found | Remotive API may be slow; try again. Add `SERPAPI_KEY` for more results |
| Playwright fails to submit | Many job sites use CAPTCHAs; apply manually via the "View" button |
| Email not sending | Check `SENDGRID_API_KEY` or SMTP settings; see backend logs: `docker compose logs backend` |

**View logs:**
```bash
docker compose logs -f backend    # Backend errors
docker compose logs -f frontend   # Next.js errors
docker compose logs -f playwright # Browser automation
```

