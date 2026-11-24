# FarmMate roadmap

Status is what is in this repository, not a promise that every screen is finished product polish.

| Phase | State | What is in the repository |
| --- | --- | --- |
| 0 Discovery | Done | The old full product was not found. `ngosra/Farmmate` is the connected repository and already had the auth scaffold. |
| 1 Foundation | Done | Django apps, SpatiaLite locally, PostGIS when `DATABASE_URL` is `postgis://`, React console, Expo app, design tokens, CI. |
| 2 Accounts and organizations | Done | Registration of an organization, login, refresh, logout, password reset, roles, members, audit log, org isolation. |
| 3 Farmers, farms, fields | Done | Profiles, declarations, identification files, farms, polygons, land use, documents, crops and plantings. |
| 4 Certification | Done | EU organic, EUDR, and USDA NOP starter checklists. Readiness from verified weight. Official status is a separate decision. |
| 5 Inventory and production | Done | Inputs, approvals, stock, activities, harvests, storage, yield rows. |
| 6 Traceability | Done | Batches, movements, remaining quantity, QR PNG, authenticated trace lookup. |
| 7 Inspections and training | Done | Schedules, checks, sessions, materials, attendance. |
| 8 Reports and NDVI | Partial | Dashboard and CSV reports are implemented. NDVI stores manual rows. Satellite refresh returns 503 until a provider is configured. It stores nothing on that failure. |
| 9 Assistant | Partial | Answers are built from database statements. An external model is optional and cannot replace those statements. |
| 10 Mobile | Partial | Login, dashboard, activity capture, GPS note, offline queue, farm list, QR scan or typed code, assistant. Offline replay covers saved activities. Photos, maps, and a full offline catalog are not in the app yet. |
| 11 Quality | Partial | Backend pytest, ruff, web lint and build, mobile typecheck, and GitHub Actions. Browser checks are part of development. Load tests and a dedicated security audit are not. |
| 12 Deployment preparation | Partial | Production settings refuse the dev secret. Dockerfile and Compose can run the API on PostGIS. Object storage, SMTP, monitoring, and backups are documented and not operated from here. |

## Next work

- A real satellite provider behind `ndvi/providers.py`, still unable to fabricate a reading.
- S3-compatible storage for evidence and farm files.
- Mobile photo capture and a fuller offline catalog.
- PDF reports in addition to CSV.
- Operated backups, metrics, and a staging deploy once hosting credentials exist.
