#!/bin/sh
# Start main app and admin dashboard on the same machine (shared SQLite)
/app/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8080 &
/app/.venv/bin/python -m uvicorn admin.app:app --host 0.0.0.0 --port 8001
