# 7. Research image corpus uses sourced memes, not stand-in cards

## Status

Accepted, 23 August 2026.

## Deciders

Product owner, on an explicit session decision. Frontend contributor implementing.

## Context

`AGENTS.md` forbids committing real hateful content, real personal data, or
identifiable handles unless there is explicit confirmation. The first pass of
the image datapack therefore stored navy SVG stand-ins and kept the sourced
files with the collector.

The product owner then said the real images matter because Amanah is a research
tool. An image-checking model, and a Reports catalog that claims to show
examples, cannot be evaluated on cards that only name a hate type.

`rules/general.md` §8 allows a deviation with written justification at the
point of deviation. This ADR is that justification.

## Decision

**The fixture corpus stores the sourced meme files.** They live at
`apps/web/public/media/fixtures/memes/img-ex-*.png|jpg`. Metadata lives in
`apps/web/src/fixtures/meme-datapack/`. Checksums for a later database seed
live beside the rows, not inside Postgres as image bytes.

**Pixels still never cross `src/api/`.** Classification requests carry
filename and byte size, plus an optional `example_id`. The browser does not
send base64. Live mode should upload to object storage and classify on the
server.

**Do not store images as base64 in the database.** Object storage holds the
bytes. Postgres holds path, sha256, mime, size, annotation JSON, and
prediction JSON. The API returns a short-lived signed URL plus the
classification object.

**Safeguards stay in force.**

- The catalog is on authenticated Reports, not the public dashboard.
- Harmful media is blurred until a person reveals it.
- Titles, alt text, and form notes describe form. They do not reproduce
  slogans or slurs.
- Dataset annotations stay labeled as annotations.
- Copy still says classified as likely, never is hate.
- This pack is `internal-research-fixture-not-for-redistribution`. It is not
  an open datapack and it is not a training release.

**Person-level features stay out of scope.** Faces that appear in a sourced
meme are part of that artifact. The catalog does not index, search, or rank
people.

## Consequences

Reviewers and judges will see real hostile images after an intentional
reveal. That is the cost of a research observatory that classifies image
memes. Redistribution, a public un-blurred gallery, or a browser call to a
vision API would be a further deviation and needs its own decision.
