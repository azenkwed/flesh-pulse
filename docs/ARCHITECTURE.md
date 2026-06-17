# Flesh Pulse — Architecture

Two FastAPI processes, one SQLite database, one AI pipeline.

---

## Process 1 — Main app (port 8000, public)

Entry point: `main.py` → starts FastAPI + registers routers + fires the APScheduler.

Three concerns:

### 1. Pipeline (automated)

`backend/scheduler.py` drives the full loop on startup then every N minutes:

```
rss_collector.collect_all()        ─┐
newsapi_collector.collect_all()    ─┴─► deduplicate by URL + CurationRecord
                                        │
                                        ▼
                               curator.curate_batch()   ← Claude Haiku
                                        │
                               accepted articles ──► Article table
                               all evaluated URLs ──► CurationRecord table
                                        │
                               featured articles ──► TweetLog (optional)
```

Curation semaphore: max 5 concurrent Claude API calls per pipeline run.

Newsletter jobs are separate scheduler entries:
- `send_newsletters("daily")` — 07:00 UTC daily
- `send_newsletters("weekly")` — 07:00 UTC Mondays

### 2. Web layer

`backend/routes.py` serves Jinja2 HTML pages and a small REST API.

| Route | Purpose |
|---|---|
| `GET /` | Home feed (paginated, 24/page) |
| `GET /category/{slug}` | Category feed |
| `GET /article/{id}` | Article detail |
| `POST /article/{id}/save` | Toggle bookmark (auth required) |
| `GET /search` | Full-text search |
| `GET /saved` | Saved articles (auth required) |
| `GET /contact` | Contact form |
| `GET /privacy`, `/terms` | Static pages |
| `GET /sitemap.xml`, `/robots.txt` | SEO |
| `GET /api/articles` | REST — list articles |
| `GET /api/stats` | REST — counts + last run |
| `POST /api/trigger-collection` | REST — manual pipeline trigger |

The `_enrich()` helper converts ORM `Article` objects to template-ready dicts, adding:
- `tags_list` — parsed from JSON
- `severity_color` — CSS class based on severity level
- `category_slug` — URL-safe category string
- `default_image_url` / `display_image_url` — category fallback images
- `reading_time` — word count ÷ 200 wpm
- `body_html` / `body_text` — sanitized content
- `display_datetime` — ISO string for JS; `display_date` — server-side fallback

### 3. Auth

`backend/auth/` handles all user authentication:

- **Email/password** — PBKDF2-SHA256 (480k iterations). Registration sends a verification email.
- **JWT cookies** — 30-day `access_token` httponly cookie, HS256-signed.
- **Password reset** — signed timed token (itsdangerous), 1-hour expiry.
- **OAuth** — Google, LinkedIn, Microsoft. Enabled only if both CLIENT_ID and CLIENT_SECRET are set.
- **LinkedIn quirk** — handled manually (authlib rejects LinkedIn's id_token — missing nonce claim).
- **Sessions** — Starlette session middleware for OAuth state/nonce storage.

---

## Process 2 — Admin app (port 8001, localhost only)

Entry point: `admin/app.py`. Bound to `127.0.0.1` — never exposed publicly.

| Route | Purpose |
|---|---|
| `GET /` | Dashboard — stats, logs, users, DB info |
| `GET /articles` | Article list with search/filter |
| `GET /articles/{id}` | Article detail + inline edit |
| `POST /articles/{id}` | Update category/severity/featured/summary |
| `POST /articles/{id}/delete` | Delete one article |
| `POST /articles/bulk-delete` | Bulk delete |
| `GET /logs` | Collection log history |
| `GET /curation-records` | All evaluated URLs (accepted + rejected) |
| `GET /users` | User list |
| `GET /settings` | Pipeline settings (reads/writes `.env`) |
| `POST /trigger` | Fire pipeline immediately |
| `GET /newsletter-preview` | Preview digest HTML |

---

## Category slug resolution

Categories are defined in two places and must stay in sync:

1. `backend/processors/curator.py` — `CATEGORIES` dict: uppercase key → display name  
   e.g. `"SEXUAL_HEALTH": "Sexual Health & Education"`

2. `backend/routes.py` — `CATEGORIES` list of display names

URL slugs: spaces → `-`, `&` → `and`, lowercased.

Reverse lookup **must** use the slug-matching pattern — do not use naive `.replace("-", " ")` which fails to restore `&`:

```python
next((c for c in CATEGORIES if c.replace(" ", "-").replace("&", "and").lower() == slug), None)
```

---

## Full-text search

PostgreSQL `tsvector` column (`search_vector`) on the `articles` table, with a GIN index and a `BEFORE INSERT OR UPDATE` trigger that keeps it current. Indexed on `title`, `description`, `ai_summary`, and `tags`.

`init_db()` creates the column, GIN index, and trigger function on startup (`CREATE IF NOT EXISTS` — safe to re-run).

Search queries use `plainto_tsquery('english', :q)` with `ts_rank` for relevance ordering. See `DATA_MODEL.md` for the full SQL and the `routes.py` query pattern.

---

## Database connection

`backend/database/db.py` reads `DATABASE_URL` from the environment and creates an async SQLAlchemy engine with `asyncpg`:

```python
engine = create_async_engine(os.environ["DATABASE_URL"], echo=False, pool_pre_ping=True)
```

`pool_pre_ping=True` detects stale connections — important for Supabase which closes idle connections after a timeout.

For Supabase production with multiple Fly.io instances, use the pgBouncer Transaction mode pooler (port 6543) to avoid exhausting the Postgres connection limit. See `ENV_VARS.md` for the URL format.

## SSL on Windows

All outbound HTTP calls use `verify=sys.platform != "win32"` (i.e., `verify=False` on Windows only):

- `backend/collectors/rss_collector.py`
- `backend/collectors/newsapi_collector.py`
- `backend/processors/curator.py` (httpx.Client passed to Anthropic SDK)
- `backend/auth/routes.py` (LinkedIn OAuth token + userinfo)

Do not remove without testing all RSS feeds, a live curation call, and LinkedIn OAuth on Windows.
