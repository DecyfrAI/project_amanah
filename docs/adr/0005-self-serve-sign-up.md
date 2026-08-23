# 5. Self-serve sign-up, against the planning documents

## Status

Accepted, with the deviation recorded below

## Date

2026-08-22

## Deciders

Product owner, on an explicit session decision. Frontend contributor implementing.

## Context and Problem Statement

Three planning documents close registration for this build:

- `PROJECT_AMANAH_DATA_API_DASHBOARD_BLUEPRINT.md` 1.1: "For the hackathon,
  disable open registration and create one invited demo/reviewer account."
- `PROJECT_AMANAH_BRAND_DESIGN_SYSTEM.md` 7: "Open registration is disabled for
  the hackathon."
- `PROJECT_AMANAH_PROJECT_SPECIFICATION.md` 18: "invite-only login".

The product owner asked for a self-serve sign-up screen anyway, was shown the
conflict, and chose to accept the deviation. `AGENTS.md` permits a deviation
only with written justification at the point of deviation, and requires an ADR
for a significant one. This is that ADR.

## Decision

The frontend ships `/login` and `/signup`. Both are real forms with validation,
a pending state, and an error state.

The reason this does not create the risk the planning documents were guarding
against is that **no account is created anywhere**. In fixture mode the form
starts a local demo session and nothing leaves the browser. Specifically:

- No credential is stored anywhere, and nothing is transmitted. The session holds
  a display name, the address given at sign-in, and a profile picture if one was
  chosen, in `sessionStorage`, which the browser discards when the tab closes.
  The picture is a data URL capped at 256 KB, so it cannot become a storage
  problem, and there is no upload endpoint for it to reach.
- The password field is never stored, logged, or included in any state that
  outlives submission.
- The screen says plainly that it opens a demo workspace over synthetic data
  rather than registering a user, so a visitor cannot mistake it for an account.
- Nothing here weakens the access rules on real collected content. The
  authenticated surfaces still read fixtures, and `FixtureBanner` stays visible.

`/app/profile` edits the same session. Display name, email and picture are
editable because they are local to the tab. The password section is inert and
says so: there is no credential to change, and a form that appeared to change one
would be the kind of false affordance this ADR exists to avoid.

When live mode arrives with Supabase Auth (FE-03), the invite constraint is
enforced server-side. At that point sign-up either redeems an invite or is
removed, and the profile screen reads and writes the real user record instead of
`sessionStorage`. The decision to open registration for real is a backend and
policy decision, and this ADR does not make it.

## Consequences

The "Login / Sign up" wording already on the marketing page becomes accurate
rather than a leftover.

The risk we are carrying is that the demo implies a product where anyone can
watch this data. That is the opposite of the stated model, so the copy on both
screens has to keep saying what the session actually is. If a reviewer decides
the risk is not worth it, reverting means deleting `/signup`, its page and test,
and restoring the invite-only copy on `/login`.

Live mode still refuses access in `AuthGuard`, so this cannot become a real
authentication path by accident.
