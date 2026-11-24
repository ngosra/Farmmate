# Module layout

Django apps follow the product modules: accounts, organizations, farmers, farms, crops, production, inventory, certification, inspections, training, traceability, ndvi, reports, and ai.

Two exceptions keep the schema stable:

- `Farmer` remains on the organizations app from the scaffold. Declarations and identification documents live in the farmers app.
- Compliance items, evidence, and corrective actions live in the certification app rather than a second app with the same foreign keys.

Reports and the assistant are apps because they own HTTP endpoints and, for the assistant, a query log. They do not own a parallel copy of farm data.
