# Movement for Change (M4C)

M4C is a Django website served either by Django's development server or by Tornado wrapping the Django WSGI application.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
```

## Run

Run Django directly:

```sh
python manage.py runserver 0.0.0.0:8000
```

Or run the same Django application through Tornado:

```sh
python run_tornado.py
```

Tornado listens on `0.0.0.0:8000` by default. Set `HOST` or `PORT` to change its bind address.

## Render deployment

Use a persistent PostgreSQL database for production. Add the database's internal connection URL as the Render service environment variable `DATABASE_URL`; when that variable is present Django uses PostgreSQL, while local development continues to use SQLite. Install dependencies with `pip install -r requirements.txt` and set `DJANGO_SECRET_KEY` in Render. `DJANGO_DEBUG` defaults to `false` on Render.

The web start command must run migrations before serving: `python manage.py migrate --noinput && python run_tornado.py`. The repository Procfile uses this command, but an explicit Render dashboard Start Command overrides the Procfile and must be updated to match. This ensures `auth_user` and the member profile tables exist before `/register/` handles requests. Django also trusts Render's forwarded HTTPS scheme so CSRF protection recognizes secure login and registration posts behind Render's TLS proxy.

The volunteer registration endpoint accepts JSON at `POST /api/volunteers`. Browser submissions include Django's CSRF token.

User accounts are stored in the configured SQLite database and managed by Django authentication. Run `python manage.py migrate` to create the auth tables. The homepage's Join M4C form and `/register/` both create the same member account. Members can sign in from the homepage's join section or at `/login/`, view their profile at `/profile/`, and verify contacts at `/verify/`; administrators can also manage accounts through `/admin/`.

Registration sends email and WhatsApp verification codes immediately and keeps the member signed in while verification is pending. Members can sign in with their username or registered email address and request a password reset from `/login/`. Configure production SMTP with `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`; the default sender is `Movement for Change <noreply@movementforchange.co.ke>`. The SMTP provider must authorize that sender/domain and have SPF and DKIM configured for reliable delivery. Configure WhatsApp Cloud API with `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, and an approved authentication template named by `WHATSAPP_TEMPLATE_NAME` (default `m4c_verification`) with one body code parameter. `WHATSAPP_TEMPLATE_LANGUAGE` defaults to `en`; `WHATSAPP_GRAPH_API_VERSION` defaults to `v23.0`. Keep provider credentials in deployment secrets, not source control. Codes expire after 10 minutes, are limited to five attempts, and can be resent once per minute.