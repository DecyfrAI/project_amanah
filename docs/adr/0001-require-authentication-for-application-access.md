# 0001. Require authentication for application access

* **Status**: accepted
* **Date**: 2026-08-22
* **Deciders**: Project Amanah team

## Context and Problem Statement

The earlier product direction allowed anonymous access to dashboard, item, news, methodology, and resource views while authenticating only contribution and reporting actions. For a 48-hour hackathon, maintaining parallel anonymous and authenticated product-data paths adds routing, API, RLS, caching, testing, and disclosure complexity that does not strengthen the core demonstration.

## Decision Drivers

* Deliver a coherent research workflow within the hackathon window.
* Reduce frontend route-state and backend authorization branches.
* Prevent accidental anonymous disclosure of monitored content or analytical data.
* Preserve a clear public explanation of the product before sign-in.

## Considered Options

* Public read-only dashboard with authentication for actions.
* Public marketing homepage with authentication for the complete application.

## Decision Outcome

**Chosen option**: Public marketing homepage with authentication for the complete application.

Only the marketing homepage and authentication entry, callback, and recovery routes are anonymous product surfaces. Operational health and readiness endpoints remain unauthenticated. Dashboard, items, news, methodology, resources, forum, reports, contributions, reviewer/admin routes, and every `/v1` product endpoint require a valid session.

Frontend route guards restore the session before resolving protected routes and prevent protected requests while authentication is unresolved. Backend `/v1` routers require server-verified authentication by default. Supabase RLS denies anonymous access to product tables, views, functions, and storage objects.

### Positive Consequences

* One application access model is easier to implement and demonstrate.
* Anonymous product-data exposure is denied at frontend, API, and database boundaries.
* The first-sign-in path naturally leads through onboarding to the dashboard.
* Authorization tests have a simple default-deny invariant.

### Negative Consequences / Trade-offs

* Researchers cannot preview dashboard data before creating or receiving an account.
* Resource and methodology content are less discoverable to anonymous visitors.
* Demo reliability depends on a working authentication path or pre-created demo account.

## Pros and Cons of the Options

### Public read-only dashboard

* Good: visitors can evaluate the data experience immediately.
* Bad: requires separate anonymous projections, route behavior, RLS grants, cache rules, and test coverage.
* Bad: increases the chance of unintentionally exposing sensitive monitored content.

### Authenticated application

* Good: reduces access-control branches and supports a safer default-deny posture.
* Good: simplifies the hackathon narrative from marketing to sign-in to onboarding to dashboard.
* Bad: introduces authentication friction before product value is visible.

## Links

* Governing requirements: [`spec.md`](../../spec.md)
* Frontend plan: [`frontend-implementation-plan.md`](../../frontend-implementation-plan.md)
* Backend plan: [`backend-implementation-plan.md`](../../backend-implementation-plan.md)

