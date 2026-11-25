# Testing

## Backend

```bash
cd backend
ruff check .
pytest
```

The suite covers login by email and FarmerID, refresh rotation, logout, mobile refresh JSON, throttling, FarmerID uniqueness, bootstrap, organization isolation, the absence of a public user list, organization registration, farm geometry, farmer isolation, readiness math (a verified weight of 3 and a declared weight of 1 is 75, not a fixed 72), the farmer's inability to certify, expiry reminders, an empty dashboard, satellite refresh with zero stored rows, manual NDVI source, batch mass balance, QR PNG, trace lookup, prohibited stock movements, assistant answers for missing data and unknown farms, password reset invalidating refresh tokens, member administration, and the demo seed.

GeoDjango tests use in-memory SpatiaLite. CI installs `libsqlite3-mod-spatialite`.

## Web

```bash
cd web
npm run lint
npm run build
```

Lint is oxlint. The build is `tsc -b` plus Vite. Exercise registration, the dashboard, a farmer and farm, a checklist, and the assistant in a browser against the API. A production bundle is not a substitute for that.

## Mobile

```bash
cd mobile
npm run typecheck
```

Typecheck covers the field screens. Camera and GPS need a device or simulator; they are not executed in CI.

## Not covered here

Load tests, a penetration test, and an end-to-end browser runner are not in the pipeline. Django's GIS check may warn that GDAL 3.8.4 cannot block network-based drivers (`gis.W001`). The packaged GDAL on this environment is 3.8.4.
