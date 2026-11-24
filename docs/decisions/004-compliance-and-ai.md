# Compliance, satellite data, and the assistant

Starter standards are EU organic, EUDR, and USDA NOP preparation checklists. Their descriptions say they are not legal text and not a certificate. More standards can be added as rows, including an organization-specific standard.

Readiness uses verified weight only. Declared answers and uploaded files change the item state, and they do not become verified on their own. The official status is a decision with a certificate number. The interface tells a farmer when their role cannot make that decision.

The assistant classifies a question and reads the caller's farms, checklists, yields, inventory, batches, and NDVI rows. Unknown quoted farm names stay unknown. An optional chat model may rephrase the statements. It does not add facts, and a failed call leaves the statements in place.

Satellite refresh has the same rule. Until a provider implementation exists, the endpoint fails and stores zero observations. A person can enter a manual NDVI value, and that row is labeled manual.
