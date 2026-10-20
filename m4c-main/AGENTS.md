# M4C — Base44 Development Environment

## Overview
Django + Tornado web project ("Movement for Change"). Uses SQLite (local file), no external database or credentials required.

## Setup
- `docker-compose.base44.yml` runs the app from a `python:3.12-slim` image with the repo bind-mounted at `/app`.
- On startup: installs `requirements.txt`, runs `python manage.py migrate`, then starts Django's dev server (`runserver 0.0.0.0:8000`) with auto-reload.
- Host port 3000 maps to container port 8000.
- `DJANGO_SECRET_KEY` has a dev default in `m4c/settings.py`; no secret configuration needed to boot.

## Verification
- `curl http://localhost:3000/` returns 200 (home page).
- Routes: `/`, `/leadership/`, `/comrades/`, `/counties/`, `/counties/<slug>/` all return 200.
- Static files (CSS, JS, images) served by Django's dev server in DEBUG mode.
- The volunteer API is at `POST /api/volunteers` (JSON body, CSRF-protected for browser submissions).

## Notes
- No custom Django models — only Django's built-in migrations (auth, admin, sessions) run.
- `run_tornado.py` wraps the Django WSGI app for production-style serving; the dev compose uses Django's `runserver` for live reload.
- County directory data is loaded from `static/data/kenya-county-directory.json` at import time in `website/views.py`.
