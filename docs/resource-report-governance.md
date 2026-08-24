# Resource and research-report governance

Last reviewed: 2026-08-23

This reference records the Milestone 6 governance and integrity boundaries implemented by the
backend. The product specification remains authoritative.

## Curated resources

Every managed resource is created as `draft`. A reviewer or administrator may revise it, but
cannot set lifecycle state through the general update request. Publication is a separate action
requiring an explicit `reviewed_summary: true` confirmation; the server records the authenticated
reviewer and UTC review time. Revising published wording or its link invalidates the prior review
and returns the entry to `draft`. Archiving removes it from the authenticated base-role catalog.

Accepted links must use HTTPS, contain no credentials, use the standard HTTPS port, and not name
localhost or a private/reserved literal address. Country scope is controlled to `global`, `CA`,
`US`, or `GB`, and titles, organizations, and summaries have bounded lengths. Candidate sources
listed in the specification are not seeded by this milestone because no reviewed approval record
was available; they remain candidates rather than implied endorsements.

Each create, update, publish, and archive action appends a safe catalog snapshot to
`resource_audit_events`. The database rejects update or deletion of those audit rows.

## Research reports

`POST /v1/research-reports` accepts the same bounded filters as the authenticated dashboard plus
an allow-listed selection of aggregate metrics and deterministic findings. Generation freezes:

- the exact validated filter document and its SHA-256 hash;
- a fingerprint of the visible data state and the current methodology version;
- coverage, window, source scope, denominators, selected metrics and findings;
- citation records, model/methodology disclosures, and limitations; and
- whether aggregate CSV was included in the snapshot scope.

No report section contains raw or normalized source text, author identifiers, private object keys,
or item-level bulk rows. Both supported redaction modes are aggregate-safe. A database trigger
rejects every update or deletion after status becomes `ready`; regeneration always inserts a new
report ID.

The CSV columns are `metric_key`, `value`, `numerator`, `denominator`, `window_start`,
`window_end`, `source_scope`, `coverage_score`, `data_version`, `methodology_version`,
`data_mode`, and `redaction_mode`. CSV is serialized from the stored report snapshot and never
recomputes live queries. Formula-shaped text cells are escaped.

Owners may read and export their reports. Reviewers and administrators may read/export for
authorized review; other base-role users receive no row. Generation and download each append a
request-correlated audit event, and the database rejects mutation of that audit history.
