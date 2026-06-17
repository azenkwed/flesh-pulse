# Flesh Pulse — Data Model

PostgreSQL via SQLAlchemy async ORM (`backend/database/models.py`). Seven tables.

**Database**: Supabase (production) / Postgres 15 via Docker (local dev).
**Driver**: `asyncpg` — connection string prefix `postgresql+asyncpg://`.

---

## Key differences from Panoptiqa (SQLite)

| Aspect | Panoptiqa (SQLite) | Flesh Pulse (Postgres) |
|---|---|---|
| Full-text search | FTS5 virtual table | `tsvector` column + GIN index + trigger |
| JSON fields | `Text` + `json.loads()` | `JSONB` — native indexable JSON |
| Auto-increment | `AUTOINCREMENT` | `SERIAL` / `BIGSERIAL` (SQLAlchemy handles) |
| WAL mode | `PRAGMA journal_mode=WAL` | Built into Postgres — not needed |
| Connection | File path | `DATABASE_URL` env var |
| Migrations | Manual `ALTER TABLE` in `init_db()` | Alembic (recommended) |

---

## Article

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `url` | `VARCHAR(2048)` UNIQUE | Deduplication key |
| `title` | `VARCHAR(512)` | |
| `description` | `TEXT` | Feed summary |
| `content` | `TEXT` | Full body if available |
| `source_name` | `VARCHAR(256)` | e.g. `"XBIZ"`, `"Rewire News"` |
| `source_country` | `VARCHAR(64)` | ISO 2-letter or `"INT"` |
| `author` | `VARCHAR(256)` | |
| `published_at` | `TIMESTAMPTZ` | UTC |
| `collected_at` | `TIMESTAMPTZ` | UTC, pipeline run time |
| `relevance_score` | `FLOAT` | 0.0–1.0 from Claude |
| `category` | `VARCHAR(128)` | Display name |
| `tags` | `JSONB` | Array of tag strings — replaces `dystopian_tags` |
| `ai_summary` | `TEXT` | One sentence from Claude |
| `severity` | `VARCHAR(32)` | `low` / `medium` / `high` / `critical` |
| `featured` | `BOOLEAN` | True if `relevance_score >= 0.90` |
| `image_url` | `VARCHAR(2048)` | |
| `search_vector` | `TSVECTOR` | Auto-updated by DB trigger — do not write manually |

Indexes: `category`, `published_at`, `relevance_score`, `collected_at`, GIN on `search_vector`, GIN on `tags`.

### Full-text search setup

`init_db()` runs this once on startup:

```sql
-- Add search_vector column
ALTER TABLE articles ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

-- GIN index for fast FTS queries
CREATE INDEX IF NOT EXISTS idx_articles_search ON articles USING GIN(search_vector);

-- Trigger keeps search_vector current on insert/update
CREATE OR REPLACE FUNCTION update_articles_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    coalesce(NEW.title, '') || ' ' ||
    coalesce(NEW.description, '') || ' ' ||
    coalesce(NEW.ai_summary, '') || ' ' ||
    coalesce(NEW.tags::text, '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER articles_search_vector_update
  BEFORE INSERT OR UPDATE ON articles
  FOR EACH ROW EXECUTE FUNCTION update_articles_search_vector();
```

Search query (replaces SQLite FTS5 `MATCH`):

```python
# In routes.py search handler:
results = await session.execute(
    select(Article)
    .where(Article.search_vector.op("@@")(func.plainto_tsquery("english", query)))
    .order_by(func.ts_rank(Article.search_vector, func.plainto_tsquery("english", query)).desc())
)
```

---

## CurationRecord

Every evaluated URL (accepted and rejected). Prevents re-evaluation.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `url` | `VARCHAR(2048)` UNIQUE | |
| `title` | `VARCHAR(512)` | |
| `source_name` | `VARCHAR(256)` | |
| `status` | `VARCHAR(32)` | `accepted` or `rejected` |
| `relevance_score` | `FLOAT` | |
| `category` | `VARCHAR(128)` | |
| `evaluated_at` | `TIMESTAMPTZ` | |

---

## User

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `email` | `VARCHAR(256)` UNIQUE | |
| `password_hash` | `VARCHAR(256)` | PBKDF2-SHA256, 480k iterations |
| `display_name` | `VARCHAR(128)` | |
| `email_verified` | `BOOLEAN` | Must be True to log in |
| `newsletter_frequency` | `VARCHAR(16)` | `daily` / `weekly` / `never` |
| `categories` | `JSONB` | Array of selected category display names |
| `password_reset_token_version` | `INTEGER` | Increment to invalidate reset tokens |
| `created_at` | `TIMESTAMPTZ` | |
| `last_login` | `TIMESTAMPTZ` | |

---

## SavedArticle

User bookmarks. Unique on `(user_id, article_id)`.

| Column | Type |
|---|---|
| `id` | `SERIAL` PK |
| `user_id` | FK → users.id |
| `article_id` | FK → articles.id |
| `created_at` | `TIMESTAMPTZ` |

---

## OAuthAccount

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `user_id` | FK → users.id | |
| `provider` | `VARCHAR(32)` | `google` / `linkedin` / `microsoft` |
| `provider_user_id` | `VARCHAR(256)` | |
| `provider_email` | `VARCHAR(256)` | |
| `created_at` | `TIMESTAMPTZ` | |

Unique on `(provider, provider_user_id)`.

---

## CollectionLog

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `ran_at` | `TIMESTAMPTZ` | |
| `source` | `VARCHAR(256)` | Always `"pipeline"` |
| `articles_fetched` | `INTEGER` | Raw count before dedup |
| `articles_accepted` | `INTEGER` | After curation |
| `articles_rejected` | `INTEGER` | Evaluated but below threshold |
| `error` | `TEXT` | Exception message if run failed |

---

## NewsletterLog

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL` PK | |
| `user_id` | FK → users.id | |
| `frequency` | `VARCHAR(16)` | `daily` / `weekly` |
| `period_key` | `VARCHAR(16)` | `"2026-06-17"` or `"2026-W24"` |
| `subject` | `VARCHAR(256)` | |
| `article_count` | `INTEGER` | |
| `sent_at` | `TIMESTAMPTZ` | |

Unique on `(user_id, frequency, period_key)`.

---

## Migrations

Use **Alembic** for schema changes after the initial deploy:

```bash
pip install alembic
alembic init alembic
# Edit alembic/env.py to import Base from backend.database.models
# and read DATABASE_URL from env

alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Supabase also has a built-in SQL editor and migration history — either approach works. Do not use raw `ALTER TABLE` in `init_db()` as Panoptiqa did; use Alembic instead.

---

## Supabase-specific notes

- **Row Level Security (RLS)**: Supabase enables RLS by default on new tables. Since the app uses a single service-role connection (not per-user Supabase Auth), either disable RLS on all tables or add a blanket `USING (true)` policy.
- **Realtime**: Not used — disable it on all tables to reduce overhead.
- **Storage**: Not used — images are direct URLs, not stored in Supabase Storage.
- **Auth**: Not used — the app has its own auth system. Do not mix Supabase Auth with the app's JWT auth.
- **Connection pooler**: For production on Fly.io (multiple instances), use the Transaction mode pooler (port 6543) to avoid exhausting Postgres connections.
