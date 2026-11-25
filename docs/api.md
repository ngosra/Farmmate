# API

Base path: `/api/v1/`. Trailing slashes are required. Authenticated list endpoints from `OrgViewSet` return `{count, next, previous, results}` with a page size of 25. `GET /organizations/` stays a plain array.

Send `Authorization: Bearer <access>`. Send `X-Organization-Id` when the user belongs to more than one organization. The web client stores the refresh token in the HttpOnly cookie `farmmate_refresh`. The mobile client sends `X-FarmMate-Client: mobile` and receives the refresh token in JSON.

## Authentication

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/auth/register/` | Creates an organization and its administrator, then returns an access token |
| POST | `/auth/login/` | Email or FarmerID plus password |
| POST | `/auth/refresh/` | Rotates the refresh token |
| POST | `/auth/logout/` | Revokes the refresh token |
| GET, PATCH | `/auth/me/` | Profile |
| POST | `/auth/password/` | Change password |
| POST | `/auth/password-reset/` | Emails a link. The stored token is a SHA-256 hash |
| POST | `/auth/password-reset/confirm/` | Sets the password and blacklists outstanding refresh tokens |
| GET | `/health/` | Public health check |

Login, registration, and password reset are throttled.

## Records

| Area | Paths |
| --- | --- |
| Organizations | `/organizations/`, `/members/`, `/audit/` |
| Farmers | `/farmers/`, `/declarations/`, `/identifications/` |
| Farms | `/farms/`, `/fields/`, `/fields/{id}/satellite-refresh/`, `/land-use/`, `/farm-documents/` |
| Crops | `/crops/`, `/plantings/` |
| Production | `/activities/`, `/harvests/`, `/storage/` |
| Inventory | `/suppliers/`, `/inputs/`, `/input-approvals/`, `/stock-movements/` |
| Certification | `/standards/`, `/certifications/`, `/certifications/{id}/decision/`, `/compliance-items/`, `/compliance-items/{id}/evidence/`, `/corrective-actions/` |
| Inspections | `/inspections/`, `/inspection-checks/` |
| Training | `/training-sessions/`, `/training-materials/`, `/attendance/` |
| Traceability | `/batches/`, `/batches/{id}/movements/`, `/batches/{id}/qr/`, `/trace/{public_code}/` |
| NDVI | `/observations/` |
| Reports | `/dashboard/`, `/reports/`, `/reports/{kind}/?format=csv` |
| Assistant | `/assistant/` |

CSV kinds are `farms`, `production`, `yield`, `inventory`, `compliance`, and `traceability`. Traceability also needs `?batch=`.

`POST /observations/` stores `source=manual` even if the client sends another source. Satellite refresh returns 503 while `SATELLITE_PROVIDER` has no implementation, and it inserts no rows.

`POST /assistant/` returns `answer`, `statements`, `sources`, `narrative`, and `narrative_status`. Statements are labeled as recorded, calculated, missing, or external. `narrative_status` is `not_configured` unless `AI_API_KEY` is set.

Trace lookup requires authentication and the same organization as the batch. The QR image encodes `farmmate:batch:{public_code}`.
