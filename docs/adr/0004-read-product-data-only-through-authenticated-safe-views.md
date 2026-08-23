# 0004. Read product data only through authenticated-safe views

* **Status**: accepted
* **Date**: 2026-08-23
* **Deciders**: Project Amanah team

## Context and Problem Statement

`spec.md` section 16 requires that authenticated base-role users receive only
authenticated-safe projections, and that raw or encrypted content, author
identifiers, internal evidence, reviewer context, and admin state stay separately
authorized. `AGENTS.md` adds that Supabase row-level security must deny anonymous
access to every product table, view, function, and storage object — including the
safe projections.

`content_items` holds the encrypted original text, the normalized model input,
the private storage key, the opaque provider payload, and the provider-side item
identifier. All five are things a reader must never receive. The question is what
stops them being returned: the discipline of the person writing each query, or
the shape of what a query can reach at all.

Two consumers read this data. The backend connects as the database owner. A
Supabase client in the browser would connect as `anon` or `authenticated` through
PostgREST. Both paths need the same answer.

## Decision Drivers

* A new endpoint must be safe by default. "Remember not to select that column" is
  not a control.
* Anonymous denial has to hold for every relation, not for the ones someone
  remembered to lock.
* The API's own queries should be scoped by the same predicate a direct client
  would face, so ownership is not enforced in one place and assumed in another.
* Row-level security alone does not hide *columns*; column-level grants do not
  compose well across twenty-one tables.

## Considered Options

* Repositories select explicit column lists from base tables, with row-level
  security for row scoping.
* `security_invoker` views over base tables, with row-level security evaluated as
  the caller.
* Views owned by the schema owner, granted to `authenticated`, with base tables
  granted to nobody.

## Decision Outcome

**Chosen option**: views owned by the schema owner, granted to `authenticated`,
with base tables granted to nobody.

Migration `0003` creates one `authenticated_*` view per read surface and grants
`SELECT` on those views only. No base table is granted to `anon` or to
`authenticated`, and default privileges are revoked so a table added later is not
granted by accident. Row-level security is enabled *and forced* on all twenty-one
product tables, with owner, reviewer, and administrator policies; no policy names
`anon`.

Identity comes from `request.jwt.claims`, the session setting PostgREST populates
from a verified token. `Database.session_for` sets the same value with
`SET LOCAL` for each request, from the `AuthenticatedUser` the server already
verified. Every view additionally refuses to return rows when no identity is
present, so a query issued without that step fails closed.

`security_barrier` is set on the views whose predicate is row-discriminating —
the owner-scoped views and the published-only resource catalogue. It is
deliberately *not* set on the shared projections, whose only predicate is "a
verified identity exists": the same answer for every row, so a barrier would hide
nothing while preventing the planner from using the ordering index that makes
cursor pagination cheap.

`security_invoker` views were rejected because the invoker would then need
`SELECT` on the base tables, which is exactly the grant this decision removes.

### Positive Consequences

* A column that is absent from a projection is unreachable from an endpoint. The
  encrypted text, normalized text, storage key, provider payload, and provider
  item identifier have no column in any `authenticated_*` view, and a test
  asserts that for every view rather than for a sample.
* Anonymous denial is provable per relation. The row-level-security tests
  `SET LOCAL ROLE anon` and confirm refusal on all twenty-one tables and all ten
  views.
* Because the API publishes the verified caller into the session, its own
  owner-scoped reads are filtered by the database, not only by application code.
* Adding an endpoint means choosing a projection, which is a visible decision.

### Negative Consequences / Trade-offs

* Views run with the owner's rights, so a mistake in a view's `WHERE` clause is
  not caught by row-level security on the base tables. The predicates are
  therefore small, uniform, and covered by tests that seed two users and assert
  the second one's rows are absent.
* Every new read surface needs a view and a migration, which is slower than
  adding a column to a query.
* Enum columns are published as `text` so that a client without the enum types
  can decode them and so parameters compare cleanly; parsing back into the
  controlled vocabulary happens once, in the response models.
* Repositories are coupled to view column names. `amanah.db.views` declares them
  and a test compares each declaration against the live view, so drift fails
  loudly rather than at runtime.

## Links

* Governing requirements: [`../spec.md`](../spec.md) sections 14, 15.2, and 16
* Access boundary: [`0001-require-authentication-for-application-access.md`](./0001-require-authentication-for-application-access.md)
* Implementation: `backend/migrations/versions/0003_projections_and_rls.py`,
  `backend/src/amanah/db/views.py`, `backend/src/amanah/db/session.py`
* Verification: `backend/tests/db/test_row_level_security.py`,
  `backend/tests/db/test_authenticated_projections.py`
