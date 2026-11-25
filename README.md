# FarmMate

FarmMate is a multi-tenant farm management and certification-preparation platform. Organizations keep farmer, farm, field, production, inventory, inspection, training, and traceability records. Compliance readiness is calculated from checklist evidence. A readiness score is not a certificate.

This repository is the source of truth. The earlier full product was not recovered. The connected repository, [ngosra/Farmmate](https://github.com/ngosra/Farmmate), already contained an authentication and organization scaffold. That scaffold was kept and extended. See `docs/decisions/001-recovery.md`.

Google Drive UI references were not in this workspace and were not inspected.

## Applications

- `backend/` — Django, Django REST Framework, Celery, GeoDjango
- `web/` — React and TypeScript manager console
- `mobile/` — Expo field app for login, activities, GPS notes, QR lookup, and the assistant
- `compose.yaml` — local PostGIS, Redis, MinIO, and the API

## Requirements

- Python 3.12
- Node.js 22
- GDAL, GEOS, and SpatiaLite for local geometry
- Docker, only when you want PostGIS, Redis, MinIO, or the API container

On Debian or Ubuntu:

```bash
sudo apt-get install -y python3.12-venv gdal-bin libgdal-dev libgeos-dev libsqlite3-mod-spatialite
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

With `DATABASE_URL` unset, Django uses a SpatiaLite file at `backend/db.sqlite3`. That file is gitignored. PostGIS is the production database:

```bash
docker compose up -d db redis
# DATABASE_URL=postgis://farmmate:local-dev-only@localhost:5432/farmmate
```

Health check: `GET http://127.0.0.1:8000/api/v1/health/`.

Create the first organization from the web registration form, or from the API:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H 'Content-Type: application/json' \
  -d '{"organization_name":"North Cooperative","email":"admin@example.com","password":"North-coop-pass-1842","first_name":"Admin","last_name":"User"}'
```

That creates the organization and an organization administrator, then signs them in. Farmer and staff accounts are created inside the organization. There is no public user directory.

A local platform superuser, for Django admin only, still comes from:

```bash
export FARMMATE_BOOTSTRAP_EMAIL=admin@example.com
export FARMMATE_BOOTSTRAP_PASSWORD='choose-a-local-password'
export FARMMATE_BOOTSTRAP_ORG='FarmMate'
python manage.py bootstrap_dev
```

A superuser does not bypass organization isolation on the API.

Optional labeled sample data, with no satellite readings and no certified decision:

```bash
export FARMMATE_DEMO_PASSWORD='North-plot-demo-1842'
python manage.py seed_demo
```

Sign in as `demo-admin@farmmate.example` or `farmer@farmmate.example` / `FM-DEMO-001`.

## Web

```bash
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dev server proxies `/api` to port 8000.

## Mobile

```bash
cd mobile
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_URL` when the phone cannot reach `http://127.0.0.1:8000`. The app sends `X-FarmMate-Client: mobile`.

## Tests

```bash
cd backend && ruff check . && pytest
cd web && npm run lint && npm run build
cd mobile && npm run typecheck
```

## What is not connected yet

Mapbox, an external satellite provider, an external language model, S3 storage, and SMTP are configuration slots. Empty values do not invent map tiles, NDVI readings, certificates, or narrative facts. File uploads stay on local disk. See `docs/deployment.md`.
