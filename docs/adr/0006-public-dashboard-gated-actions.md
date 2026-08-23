# 6. A public dashboard, with authentication gating actions

## Status

**Superseded on 23 August 2026 by
[ADR 0001](./0001-require-authentication-for-application-access.md).** Kept as a
record of the reasoning, not as guidance.

ADR 0001 weighed the two options directly, "public read-only dashboard with
authentication for actions" against "public marketing homepage with
authentication for the complete application", and chose the second. `spec.md`
agrees: FR-HOME-005 and FR-HOME-006 require every application route to hold a
session, and no `/v1` product endpoint is anonymous.

The shipped frontend follows ADR 0001. `/app/*` sits behind `AuthGuard`, and
marketing leads to Log in and Sign up rather than to a dashboard. What survives
from this document is the redaction requirement, which ADR 0001 does not
weaken: anything rendered to a reader is public-safe and redacted, whether or
not a session exists.

Accepted 22 August 2026, superseded 23 August 2026.

## Context

Specification v2.0 arrived mid-build and states that it supersedes conflicting
assumptions in the earlier planning documents. Its central change is who may look:

> Open registration MAY be enabled for the demo.

and, more consequentially, the dashboard moves out from behind the login. In v2
authentication gates **actions**, submitting a URL, disputing a classification,
preparing a platform report, reviewing, exporting, while **reading is open to
anyone**.

The repository had been built to v1.1, where a visitor met a marketing page and a
login form, and every figure lived behind `/app`. That is now the wrong shape. An
observatory whose whole argument is that this harm goes undocumented cannot make
the documentation conditional on having an account.

v2 also renames the surface: `/dashboard` rather than `/app`, `/items/:id` rather
than an Explorer, `/v1/dashboard` and `/v1/items` rather than `/v1/overview` and
`/v1/search`, and F-S step identifiers rather than FE-.

## Decision

**The dashboard is public.** `/dashboard` renders coverage, the metric cards, and
the daily series with no session. The marketing page's primary call to action is
"View dashboard". Logging in is offered, not required, and is described by what it
adds rather than as a gate.

**Authentication gates actions only.** Review, dispute, submission, export, and
the reviewer queue stay behind `AuthGuard`. A logged-out reader sees that those
exist and what they are for, which is honest, rather than seeing a route that
pretends not to exist.

**Whatever is public is public-safe.** The projection a stranger receives is
redacted at the source, not hidden by a component. Blur-by-default and deliberate
reveal apply to an anonymous reader exactly as they do to a reviewer.

**The migration is incremental, and the old surface is not broken.** `/app`
continues to work and keeps the authenticated tabs. `/dashboard` is the public
route and shares one implementation with the authenticated Overview: the same
hook, the same components, the same fixtures. There is one dashboard, rendered in
two chromes, so the numbers cannot diverge between them.

Endpoint renaming is **deferred**. `src/api/` still asks for `/v1/overview`
because that is what the backend contributor is building this weekend against the
Blueprint. Changing the path in the frontend before the backend changes it would
break the fallback mode for no gain. When the backend adopts `/v1/dashboard`, only
`live-provider.ts` changes, which is the whole point of the provider seam.

## Consequences

The route map now reads:

| Route | Session | Notes |
| --- | --- | --- |
| `/` | none | Marketing, leading to the dashboard |
| `/dashboard` | none | Coverage, metrics, daily series |
| `/methodology` | none | How the figures are produced |
| `/login`, `/signup` | none | Offered, not required |
| `/app` and below | required | Review, reports, connections, settings, profile |

What this ADR does **not** decide, and what still needs a decision:

- Whether Explorer becomes `/items/:id` plus dashboard filters, as v2 has it, or
  survives as a search surface. Currently a stub either way.
- Whether user contributions, URL submission, disputes, and assisted reporting
  enter this build. v2 makes them P0; nothing is built.
- Whether an avatar persists. **v2 specifies `display_name` on `user_profile` and
  no avatar field anywhere**, and neither backend plan provides storage for one.
  The picture on `/app/profile` is therefore tab-local by necessity, not by
  design. Either the contract gains an avatar or the feature stays a demo
  affordance, and that is a conversation with the backend contributor.

## Revert path

The public dashboard is one route entry and one layout. Moving it back behind
`AuthGuard` restores v1.1 behaviour without touching a component.
