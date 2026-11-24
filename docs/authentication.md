# Authentication and permissions

Access tokens last 15 minutes. Refresh tokens rotate. The web app never reads the refresh token from JavaScript. The mobile app opts into a JSON refresh token with `X-FarmMate-Client: mobile`.

Login accepts an email or a FarmerID. Failed logins share a throttle.

## Registration

`POST /api/v1/auth/register/` is organization onboarding. It creates the organization and one `org_admin`, then signs that person in. It does not create a farmer. An email that already belongs to a user is rejected, so one address cannot silently join a second organization.

Farmer and staff logins are created by an organization administrator through `POST /api/v1/members/`. A farmer login requires a FarmerID. There is no public `/api/v1/users/` list.

Password reset emails use `EMAIL_BACKEND`. Locally that is the console backend. The confirm step hashes the token at rest and blacklists outstanding SimpleJWT refresh tokens for that user.

## Roles

Membership roles: `org_admin`, `field_officer`, `manager` (shown as Farm manager), `farmer`, `inspector`, `certification_officer`.

| Capability | Roles |
| --- | --- |
| Create farms and register farmers | Organization admin, field officer, farm manager |
| Field mapping, land use, documents, activities, harvests, manual NDVI on own farms | Those roles, plus farmer |
| Stock and inputs | Organization admin, field officer, farm manager |
| Official certification decision | Organization admin, certification officer |
| Inspections | Organization admin, inspector |
| Training, traceability edits, satellite refresh | Staff roles listed in `backend/api/roles.py` |
| Members and audit | Organization admin |

Farmers can read and write their own farm operations. They can declare a compliance item. They cannot verify an item or mark a certification certified. Inspectors and certification officers can read the organization records their work needs.

Object checks reject a field, harvest, or farmer id from another organization. Cross-organization access returns 404 rather than the other tenant's data.
