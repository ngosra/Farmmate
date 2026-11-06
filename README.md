# FarmMate

FarmMate is an agricultural operations console for farm records, certification, traceability, and field work. This repository is the foundation scaffold: a Django API, a Vite React manager console, and an Expo farmer app.

Farmers cannot create their own accounts. An administrator adds them.

Later phases (fields, certification, harvests, reports, AI, and production release) are not in this scaffold.

## What is included

- `backend/` — Django API with accounts, organizations, and invite-only login
- `web/` — manager console shell
- `mobile/` — farmer app shell
- `compose.yaml` — local PostGIS, Redis, and MinIO

## Requirements

- Python 3.12
- Node.js 22
- GDAL and GEOS (needed by GeoDjango)
- Docker, only if you want PostGIS, Redis, and MinIO

On Debian or Ubuntu:

```bash
sudo apt-get install -y python3.12-venv gdal-bin libgdal-dev libgeos-dev
```

## API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cp .env.example .env
cd backend
python manage.py migrate
python manage.py runserver
```

Health check: `GET http://127.0.0.1:8000/api/v1/health/` returns `{"status": "ok"}`.

Create a local administrator (the password stays in your environment, not in git):

```bash
export FARMMATE_BOOTSTRAP_EMAIL=admin@example.com
export FARMMATE_BOOTSTRAP_PASSWORD='choose-a-local-password'
export FARMMATE_BOOTSTRAP_ORG='FarmMate'
python manage.py bootstrap_dev
```

Sign in with that email, or with a FarmerID on the user record. There is no `/api/v1/auth/register/` route.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/health/` | Health check |
| POST | `/api/v1/auth/login/` | Email or FarmerID plus password |
| POST | `/api/v1/auth/refresh/` | Rotate the refresh token |
| POST | `/api/v1/auth/logout/` | Revoke the refresh token |
| GET | `/api/v1/auth/me/` | Current user, organization, and role |
| GET | `/api/v1/organizations/` | Organizations the caller belongs to |

The web app keeps the refresh token in an HttpOnly cookie. The mobile app sends `X-FarmMate-Client: mobile` and receives the refresh token in the JSON body.

To use PostGIS instead of SQLite, start Docker and set `DATABASE_URL` in `.env`:

```bash
docker compose up -d
# DATABASE_URL=postgis://farmmate:local-dev-only@localhost:5432/farmmate
```

Then run `python manage.py migrate` again.

## Web

```bash
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dev server proxies `/api` to `http://127.0.0.1:8000`.

## Mobile

```bash
cd mobile
npm install
npm start
```

Set `EXPO_PUBLIC_API_URL` when the phone cannot reach `http://127.0.0.1:8000` (an Android emulator often uses `http://10.0.2.2:8000`).

## Tests

```bash
cd backend && ruff check . && pytest
cd web && npm run lint && npm run build
cd mobile && npm run typecheck
```
