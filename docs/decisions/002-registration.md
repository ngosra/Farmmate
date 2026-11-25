# Registration and roles

Public registration creates an organization and its first administrator. Farmer accounts stay inside the organization because an open farmer signup would make organization ownership ambiguous.

One email cannot join a second organization through registration. The API returns an error instead of attaching the existing user.

Role names match the product language, with `manager` stored for farm manager. Permission sets live in `backend/api/roles.py`.

A platform superuser created by `bootstrap_dev` can use Django admin. API querysets still require a membership and do not treat `is_superuser` as access to every organization.
