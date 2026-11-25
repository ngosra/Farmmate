# Architecture

FarmMate is one API with two clients.

```text
React console  ─┐
                ├─ /api/v1 ─ Django REST ─ PostgreSQL/PostGIS (SpatiaLite in local dev and tests)
Expo field app ─┘                │
                                 ├─ Celery tasks (Redis broker)
                                 ├─ local media files
                                 ├─ optional OpenAI-compatible chat
                                 └─ optional satellite provider
```

## Apps

| App | Responsibility |
| --- | --- |
| accounts | User, password reset |
| organizations | Organization, membership, farmer profile, audit log |
| farmers | Declarations and identification files |
| farms | Farm, field polygon, land use, documents |
| crops | Crop catalog and plantings |
| production | Activities, harvests, storage |
| inventory | Suppliers, inputs, approvals, stock |
| certification | Standards, checklists, evidence, decisions, reminders |
| inspections | Visits and checks |
| training | Sessions, materials, attendance |
| traceability | Batches, inputs, movements, QR |
| ndvi | Observations and the satellite provider boundary |
| reports | Dashboard and CSV |
| ai | Permission-scoped assistant |

The `Farmer` model stays in `organizations` because the original scaffold owned it. The `farmers` app adds records around that profile. Compliance lives in `certification` so a requirement, its evidence, and the official decision stay in one place.

## Tenancy

Every operational row belongs to one organization. ViewSets take the caller's membership. `X-Organization-Id` selects among the caller's memberships. A header for an organization the caller does not belong to returns 404. Farmer-role queries are also limited to that farmer's own farms, except organization-wide records that have no farmer and no farm.

A Django superuser does not skip those filters on the API. Django admin is the platform tool.

## Readiness and official status

Readiness is verified requirement weight divided by applicable weight. `not_applicable` items leave the denominator. Declared items and attached evidence are not verified. The percent is null when nothing applies. `Certification.status = certified` is a separate decision and requires a certificate number plus the certification-officer or organization-admin role.

## External systems

`ndvi.providers.SatelliteProvider` returns no rows unless a provider is implemented. `POST /fields/{id}/satellite-refresh/` responds 503 and writes nothing in that case. Manual observations are stored with `source=manual`.

`ai.engine.narrate` calls an OpenAI-compatible endpoint only when `AI_API_KEY` is set. The facts in the response are the database statements. If the call fails, `narrative_status` is `unavailable` and the facts stay.

Uploads accept PDF, JPG, PNG, and WEBP up to 10 MB. They are stored under `backend/media` and are not synced to S3 yet.
