# 4. Insight discussion is not a public forum

## Status

Accepted

## Date

2026-08-22

## Deciders

Frontend contributor

## Context and Problem Statement

A request arrived to add a forum where users share screenshots, comment on
insights, and like each other's notes. A public screenshot board would
redistribute harmful material, invite identifiable handles, and create a
reputation system. Those outcomes conflict with the product's standing rules:
no raw hate on public surfaces, no person-level ranking, and no vanity
leaderboards.

## Decision

Discussion is attached to an Insight (and later a report), not a free-floating
board. Participation is invite-only. Attachments are first-party dashboard
captures of Amanah figures, stored with a filter hash and an Explorer deep
link. Reactions are Useful and Needs context. They may show a count on a post.
They never rank authors.

Retracting a note leaves the row in place. The body is replaced and the capture
is removed. Nothing is silently deleted.

A signed-in viewer may start a snapshot insight from any collected day, any
breakdown row, or any key figure that already carries a numerator and
denominator. The claim is the sentence the figure already states. Creating is
an authenticated action: the public dashboard never offers it. The resulting
thread is the place colleagues attach notes, not a free-floating forum. A
viewer's own notes also appear on their profile so they can return to a thread
without walking every insight.

## Consequences

The FE-02 contract reserves `/v1/insights/{id}/discussion`, post, reaction,
capture, and retract endpoints. The UI ships as FE-15 on `/app/insights/:id`.
Education and Resources (§12.9) remains a separate editorial surface.
