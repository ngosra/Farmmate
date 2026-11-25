# Database

Production uses PostgreSQL with PostGIS (`postgis://` in `DATABASE_URL`). Local development and CI use SpatiaLite so geometry tests do not need Docker. The area shown for a polygon is a spherical shoelace approximation in hectares, rounded to 0.01. It is not a surveyed area in a local projected CRS.

## Main relationships

```text
Organization
  ├─ Membership → User (role)
  ├─ Farmer → User (optional login)
  │    └─ Farm → Field → LandUse
  │                 ├─ Planting → Crop
  │                 ├─ Harvest → StorageRecord
  │                 ├─ Activity
  │                 └─ Observation
  ├─ Certification → Standard → Requirement
  │    ├─ ComplianceItem → Evidence
  │    ├─ CorrectiveAction
  │    └─ Reminder
  ├─ Inspection → InspectionCheck
  ├─ TrainingSession → Attendance, TrainingMaterial
  ├─ Batch → BatchInput (harvest) → Movement
  ├─ InputProduct → StockMovement, InputApproval
  └─ AuditLog
```

Identifiers on new records are UUIDs. Farm codes and field codes are unique inside their parent. FarmerID is unique inside the organization and, when a login exists, unique on the user.

## Geometry

- `Farm.location` is a Point, SRID 4326, kept in sync with latitude and longitude.
- `Field.boundary` is a Polygon, SRID 4326.
- `Observation.ndvi_mean` is constrained to -1 through 1.

## Integrity choices

- A harvest quantity must be positive.
- A stock OUT is rejected when an active input approval for a certification standard marks the product prohibited.
- A batch movement is rejected when process, ship, and loss quantities would make the remaining quantity negative. Store and transport do not consume quantity unless a loss is entered.
- Deleting a certified record is limited to an organization administrator, and protected deletes surface as validation errors.

Migrations live in each app. `certification/migrations/0002_seed_catalog.py` loads the starter standards. Those texts are preparation checklists, not the legal standard.
