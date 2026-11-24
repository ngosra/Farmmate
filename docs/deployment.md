# Deployment

This repository can be built and configured for production. Running it here does not mean a production host, backups, or monitoring already exist.

## API process

The image in `Dockerfile` installs GDAL and the Python requirements, then starts gunicorn on port 8000 with `config.settings.production`. Production settings refuse to boot when `DJANGO_SECRET_KEY` is missing or still the development value, and when `DJANGO_ALLOWED_HOSTS` is empty.

```bash
docker compose up -d db redis
docker compose up --build api
```

The Compose API service uses local settings and a PostGIS URL so it can boot without a production secret. For a real host, set:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL=postgis://...`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`
- `FRONTEND_URL`
- `EMAIL_BACKEND` and SMTP settings when password reset must leave the server

Migrate before serving traffic: `python manage.py migrate`.

Celery reads `REDIS_URL`. Run a worker beside the API:

```bash
celery -A config worker --loglevel=info
```

The scheduled certification task is `certification.tasks.flag_expiring_certifications`. It creates one reminder for a certified record expiring within 30 days. Wire it to a beat schedule on the host. Tests run tasks eagerly and do not need Redis.

## Data

PostGIS is the production database. Take filesystem or `pg_dump` backups on the host. This repository does not ship a backup timer.

Uploaded files use Django's local file storage under `MEDIA_ROOT`. Put that directory on durable disk, or add an S3 backend later. `django-storages` is not installed. MinIO in Compose is a local placeholder and is not wired to the file fields.

Serve the web build (`web` → `npm run build`) from a static host that proxies `/api` to gunicorn, or set the web client at a separate origin and list it in `CORS_ALLOWED_ORIGINS`.

## Secrets that stay empty until you have them

| Variable | Empty behavior |
| --- | --- |
| `AI_API_KEY` | Assistant returns database statements only. `narrative_status` is `not_configured`. |
| `SATELLITE_PROVIDER` | Refresh responds 503 and writes no observations. |
| `VITE_MAPBOX_TOKEN` | The console draws field sketches from stored coordinates. It does not call Mapbox. |

Do not put those values in git. A configured AI key sends the grounded statements to that provider.
