# Sex Health News

Independent reporting on sexual health, rights, and wellness for all.

Live at **[sexhealthnew.com](https://sexhealthnew.com)**

An automated news archive that continuously collects articles from global sources, curates and categorizes them, and publishes them through a clean editorial web interface.

---

## What it does

- **Collects** news from 16+ RSS feeds and NewsAPI every hour
- **Curates** each article using Claude AI — scoring relevance, assigning a category, severity level, and a one-line summary
- **Stores** qualifying articles in a SQLite database
- **Publishes** them on a live web interface with categories, search, pagination, related articles, and dark mode
- **Authenticates** users via email/password or OAuth (Google, LinkedIn, X)

## Categories tracked

| Category | Examples |
|---|---|
| Sexual Health & Wellness | Sexual function, sexual satisfaction, menstrual health, fertility, PCOS, endometriosis |
| Reproductive Health & Policy | Abortion access, contraception regulation, family planning laws |
| Maternal & Child Health | Pregnancy care, childbirth, postpartum care, maternal mortality, child sexual health |
| Infectious Diseases & STIs | HIV/AIDS, STI testing and treatment, viral infections, prevention strategies |
| Mental Health & Sexuality | Body image, anxiety, depression, sexual dysfunction, relationships |
| LGBTQ+ Rights & Issues | Legal rights, discrimination, same-sex marriage, trans healthcare, gender identity |
| Sex Education & Literacy | School curriculum, public awareness campaigns, misinformation |
| Sexual Violence & Consent | Assault, harassment, survivor support, consent education |
| Sex Workers & Adult Industry | Sex work legalization, labor protections, content creators, industry safety |

## Quick start

```bash
# 1. Clone and enter the project
cd sexhealthnews

# 2. Configure API keys
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY (required) and NEWSAPI_KEY (optional)

# 3. Run
run.bat           # Windows
./run.sh          # Linux / macOS
make run          # any platform with make
```

Open `http://localhost:8000` — the pipeline starts automatically on launch.

## Admin dashboard

A separate local-only admin interface runs on port 8001:

```bash
run_admin.bat     # Windows
make admin        # Linux / macOS / make
```

Open `http://127.0.0.1:8001` to:
- Browse and edit articles
- View collection logs and failure alerts
- Adjust curation settings (relevance threshold, collection interval, retention)
- Monitor database size and stats
- Manually trigger the pipeline (auto-refreshes when done)

## API keys

| Key | Where to get it | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Yes — powers curation |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) (free tier) | No — adds keyword search on top of RSS |
| `RESEND_API_KEY` | [resend.com](https://resend.com) | No — enables email verification and password reset |
| `JWT_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | Yes in production |

## Project structure

```
sexhealthnews/
├── main.py                          # App entry point, scheduler startup
├── admin/                           # Local admin dashboard (port 8001)
├── run.bat / run_admin.bat          # Windows launchers
├── run.sh / Makefile                # Linux / macOS launchers
├── fly_secrets.ps1                  # Push .env secrets to Fly.io
├── requirements.txt
├── .env                             # Your keys (git-ignored)
├── .env.example                     # Key template
├── backend/
│   ├── collectors/
│   │   ├── rss_collector.py         # RSS feeds
│   │   └── newsapi_collector.py     # NewsAPI keyword queries
│   ├── processors/
│   │   └── curator.py               # Claude Haiku scoring + categorization
│   ├── database/
│   │   ├── models.py                # SQLAlchemy models (Article, CollectionLog, User)
│   │   └── db.py                    # Async SQLite engine
│   ├── auth/                        # JWT + OAuth (Google, LinkedIn, X)
│   ├── scheduler.py                 # Hourly pipeline (collect → curate → store → prune)
│   └── routes.py                    # FastAPI routes + REST API
├── frontend/
│   ├── templates/                   # Jinja2 HTML templates
│   └── static/
│       ├── css/main.css             # Stylesheet
│       └── js/main.js               # Minimal frontend JS
└── data/
    └── sexhealthnews.db               # SQLite database (auto-created, git-ignored)
```

## REST API

| Endpoint | Description |
|---|---|
| `GET /api/articles?limit=20&category=...` | List articles as JSON |
| `GET /api/stats` | Archive statistics |
| `POST /api/trigger-collection` | Manually trigger the pipeline |
| `GET /sitemap.xml` | Sitemap for SEO |

## Configuration

All settings live in `.env`:

```env
ANTHROPIC_API_KEY=...
NEWSAPI_KEY=...

APP_HOST=0.0.0.0
APP_PORT=8000
APP_URL=http://localhost:8000

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change-me-in-production

COLLECTION_INTERVAL_MINUTES=60
MIN_RELEVANCE_SCORE=0.65

# Set to 0 to keep articles forever
ARTICLE_RETENTION_DAYS=0

# Email (Resend — leave empty to disable)
RESEND_API_KEY=
FROM_EMAIL=Sex Health News <noreply@sexhealthnew.com>

# OAuth (leave empty to disable a provider)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
```

See `docs/OAUTH_SETUP.md` for step-by-step OAuth provider setup.

## Deployment (Fly.io)

```bash
# Install Fly CLI (Windows)
pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"

# Login
fly auth login

# Push .env secrets to Fly.io
.\fly_secrets.ps1

# Deploy
fly deploy
```

For subsequent deploys after pushing changes to GitHub:

```bash
fly deploy
```

### Custom domain

```bash
# Add certs
fly certs add sexhealthnew.com -a sexhealthnews
fly certs add www.sexhealthnew.com -a sexhealthnews

# Update APP_URL secret
fly secrets set APP_URL=https://sexhealthnew.com -a sexhealthnews
```

In your DNS provider add:
- `A` record: `@` → your Fly.io v4 IP (`fly ips list -a sexhealthnews`)
- `AAAA` record: `@` → your Fly.io v6 IP
- `CNAME` record: `www` → `sexhealthnews.fly.dev.`

See `docs/OAUTH_SETUP.md` → Production checklist for updating OAuth redirect URIs after deploying.
