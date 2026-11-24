# Development guide

## First run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cp .env.example .env
cd backend
python manage.py migrate
python manage.py runserver
```

In another terminal:

```bash
cd web
npm install
npm run dev
```

The Vite server proxies `/api` to `127.0.0.1:8000`.

Install GDAL, GEOS, and SpatiaLite before migrating. An empty `DATABASE_URL` selects SpatiaLite. Set `SPATIALITE_LIBRARY_PATH` if `mod_spatialite` is not at `/usr/lib/x86_64-linux-gnu/mod_spatialite.so`.

## Sample data

```bash
export FARMMATE_DEMO_PASSWORD='North-plot-demo-1842'
cd backend
python manage.py seed_demo
```

The command is idempotent. It refuses to attach an email that already belongs to a different organization. It does not write NDVI rows and does not mark the sample checklist certified.

## Mobile

```bash
cd mobile
npm install
npx expo start
```

`EXPO_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000`. A physical device needs a reachable host. Activities that fail because the network is down stay in AsyncStorage and are sent by Sync on the home screen. A later validation error stays in the queue and the message is shown, so the record is not discarded silently.

## Checks

```bash
cd backend && ruff check . && pytest
cd web && npm run lint && npm run build
cd mobile && npm run typecheck
```

`pytest` uses `config.settings.test`: in-memory SpatiaLite, locmem email, eager Celery, and no AI key.

## Git

Work on a branch. Keep `main` stable. Do not commit `.env`, `.venv`, `media/`, or `*.sqlite3`. Do not force-push.
