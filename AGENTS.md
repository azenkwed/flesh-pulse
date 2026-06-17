# Repository Guidelines

## Project Structure & Module Organization

Flesh Pulse is a FastAPI news archive with an automated collection pipeline and a separate admin UI. `main.py` creates the public app, mounts `frontend/static`, and includes routes from `backend/routes.py` and `backend/auth/routes.py`. Core backend code lives in `backend/`: collectors in `backend/collectors/`, AI curation in `backend/processors/curator.py`, scheduling in `backend/scheduler.py`, database setup/models in `backend/database/`, and auth/email helpers under `backend/auth/` and `backend/notifications/`. Public Jinja templates and assets are in `frontend/templates/` and `frontend/static/`; admin templates and CSS are in `admin/`. Documentation is in `docs/`, utility scripts in `scripts/`, and generated local data belongs in `data/`.

## Build, Test, and Development Commands

- `make install`: create `.venv` and install `requirements.txt`.
- `make run`: start the public app on `PORT` or `8000` with reload.
- `make admin`: start the admin app at `http://127.0.0.1:8001`.
- `make trigger`: POST to `/api/trigger-collection` on the local app.
- `make reset`: delete `data/flesh-pulse.db`; stop servers first.
- `./run.sh` / `run.bat`: platform launchers that bootstrap dependencies.
- `make icons`: regenerate PWA/favicon assets from `frontend/static/icons/master.png`.

Copy `.env.example` to `.env` before running. `ANTHROPIC_API_KEY` is required for curation; `NEWSAPI_KEY` is optional. Use `DISABLE_NEWSAPI=true` for faster collector testing.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation, type hints where they clarify route or helper contracts, and concise module docstrings. Prefer async functions for I/O-heavy routes and collectors. Collector modules should expose `collect_all()` returning article dictionaries with keys such as `url`, `title`, `description`, `content`, `source_name`, `published_at`, and `image_url`. Keep category display names synchronized between `backend/processors/curator.py` and `backend/routes.py`.

## Testing Guidelines

No formal test suite is currently checked in. Before opening a PR, run `make run`, verify key pages (`/`, `/api/stats`, article/category pages), and use `make trigger` with realistic `.env` settings. For pipeline-only checks, set `DISABLE_NEWSAPI=true` to exercise RSS plus curation without NewsAPI.

## Commit & Pull Request Guidelines

Recent history uses short imperative Conventional Commit prefixes, for example `feat: add privacy policy page` and `fix: distinguish API errors from rejections`. Keep commits scoped and descriptive. PRs should explain behavior changes, list manual verification commands, link issues when relevant, and include screenshots for UI/template/CSS changes.

## Security & Configuration Tips

Never commit `.env`, API keys, OAuth secrets, or generated SQLite data. Windows SSL behavior is intentionally handled with `verify=False` in collectors and curation; do not remove it without testing RSS feeds and a live curation call on Windows.
