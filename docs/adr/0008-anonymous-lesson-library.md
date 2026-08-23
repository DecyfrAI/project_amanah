# 8. The lesson library is a public marketing surface

## Status

Accepted, 23 August 2026.

## Deciders

Product owner, resolving reconciliation gap G11
(`docs/frontend-backend-reconciliation.md`).

## Context and Problem Statement

The shipped frontend serves the education lesson library anonymously at
`/resources` and `/resources/:lessonId` (`LessonsPage` framed for marketing).
Spec v2.1 §7.2 and `AGENTS.md` placed Resources behind authentication, so the
route map diverged from the documented boundary. The pages are static
editorial content: they call no `/v1` product API, and the backend
`/v1/resources` catalog correctly denies anonymous access.

## Decision

The static lesson library is public product content, treated like the
marketing homepage. Spec v2.2 §7.1 records the route as unauthenticated with
one binding constraint: it MUST NOT fetch any `/v1` product API. The reviewed
resource catalog served by `/v1/resources` remains authenticated and is
surfaced inside the workspace only.

## Consequences

- No frontend or backend code change is required; the shipped behavior is now
  the documented behavior.
- FE-GATE-SEC-09 extends to the lesson pages: tests must prove they render
  without a session and issue no protected request.
- If a lesson page ever needs catalog data, that feature moves behind the
  session rather than opening the API.
