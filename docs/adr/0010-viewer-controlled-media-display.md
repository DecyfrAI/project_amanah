# 10. The viewer controls media display; images are visible by default

## Status

Accepted, 24 August 2026. Amends [ADR 0007](./0007-research-image-corpus.md).

This ADR changes exactly one safeguard in ADR 0007 — "Harmful media is blurred
until a person reveals it" — and leaves every other clause of that decision in
force. ADR 0007's original decision text is not edited.

## Deciders

Product owner, in the partner adjustment register recorded as `PA-01` in
[`completion-guide.md`](../completion-guide.md). Implementing contributor.

## Context

ADR 0007 blurred all research media by default and required a deliberate reveal
on every image. That rule was written for a public-facing gallery risk: an
unauthenticated reader stumbling onto hostile imagery.

The product as built does not have that surface. Every image lives behind
authentication, on a research workspace a person opened deliberately, having
signed in to study anti-Muslim material. In practice blur-by-default meant a
researcher clicked "Reveal" on every row of a 42-image corpus before doing any
work, which taught the reflex of dismissing the safety control rather than
reading it.

The partner asked for images to be visible by default, with blurring available
as a preference the person chooses.

Against that, the reason for blurring has not disappeared: a person may be
working in a shared room, may be returning to material they find distressing, or
may simply want the choice. Removing blurring outright would take away a real
protection.

## Decision

**Images are visible by default on authenticated image surfaces.** A signed-in
viewer sees research media without an interstitial reveal.

**Blurring becomes a viewer preference, off by default.** Settings offers "Blur
media by default". When enabled, media renders blurred everywhere until shown.

**The preference is stored on the authenticated profile,** in
`content_safety_preferences` through `GET`/`PATCH /v1/me` — not in page-local
state and not in browser storage. It survives a refresh and a new session, and
it applies to Explorer, Review, Insights, Reports, the image catalogue, and
uploaded-image results at once. A change reaches already-rendered images
immediately, without a reload.

**Every image keeps an accessible per-image Show/Hide control,** so one item can
be overridden in either direction without changing the global preference. The
control is a real button with an accessible name and is keyboard-operable.

**Blur is a display treatment and never an access control.** A blurred image and
a visible one are fetched over the same authenticated path with the same
short-lived signed URL. Nothing about this preference changes authorization,
ownership checks, RLS, or signed-URL lifetime.

**Everything else in ADR 0007 stands unchanged:** the catalogue stays behind
authentication, alt text and form notes still describe form rather than
reproducing slogans, dataset annotations stay labelled as annotations, copy
still says "classified as likely" rather than "is hate", the pack remains
`internal-research-fixture-not-for-redistribution`, and person-level indexing,
search, and ranking stay out of scope.

**Text redaction is untouched.** This preference governs images only. Stored
wording is never masked or profanity-filtered (reconciliation item 3), and
report-snapshot redaction is a separate control.

## Consequences

A signed-in researcher sees hostile imagery immediately on opening an image
surface. That is the intended outcome for a research observatory whose subject
is that imagery, and it is reached only after authentication.

A viewer who wants the previous behaviour enables one checkbox and gets it
across every surface, persistently — which is stronger than the per-page,
per-image reveal it replaces.

A public or anonymous image gallery remains prohibited and would need its own
decision. So would any change that made this preference weaken an authorization
or signing control rather than a display one.
