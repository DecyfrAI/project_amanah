# Reviewed collection and policy configuration

These files decide what this product is allowed to collect from, and which
platform rules the reporting assistant may offer. Nothing else does. A source
that is absent here cannot run, a seed that is absent — or present but not
`approved` — cannot run either, and a policy that is not `published` here is
never shown to a user.

| File | Holds |
|---|---|
| `sources.example.yml` | Every configured origin of content: the fixture source, YouTube, user submissions, the single controlled open-datapack row, and each reviewed news outlet |
| `source-seeds.example.yml` | Every feed, query, or seed a source may actually collect from, with its approval and sampling provenance |
| `platform-policies.yml` | The reviewed platform rules the reporting assistant may offer, each with its official link, catalogue version, review date, and reporting channel (FR-TOS-010) |

They are named `.example.yml` to match the repository layout, but they are the
real, reviewed configuration and are loaded directly. They contain **no secrets**:
provider credentials live in the environment, and a connector with no credential
disables itself whatever these files say. Point a deployment at a different copy
with `SOURCE_CONFIG_DIRECTORY`.

## What must be true of an entry

- **It was reviewed by a person.** `PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` and
  `docs/news-rss-sources.md` are human reference documents. No runtime code parses
  either of them, and appearing in one activates nothing.
- **Its identity is stable.** `registry_key` plus `config_version`, never a
  heading position in a Markdown file.
- **It is approved and attributed.** `approval_status: approved` with an
  `approved_by`. An entry that is `pending` or `rejected` is loaded, seen, and
  refused.
- **It is inside the evaluated language scope.** English only for P0. A reviewed
  non-English entry stays here and stays disabled until the classifier and its
  evaluation set cover that language.
- **It is capped.** `item_cap` bounds what one run may take.
- **It says why it was sampled.** `query_family`, `query_purpose`, and
  `sampling_stratum` travel onto every item collected under it.

That last one is not bookkeeping. The hackathon seed sample is deliberately
*enriched* — chosen to contain relevant material — so a rate computed over it
describes the sample and nothing else. Keeping the stratum attached to every row
is what stops it being pooled into a sentence that sounds like prevalence.

## The topical filter

`topical_filter` selects **subject matter**. Its keep terms name what a feed is
monitored for — religion, hate crime, public affairs, courts, elections — and its
drop terms remove the sport and celebrity desks that share a general feed.

Muslim-related vocabulary appears in the keep list. That means an article is *on
topic* and nothing more. Relevance and hate are separate, staged decisions made
later by the classifier, and neutral reporting is deliberately in scope.

## Changing these files

1. Review the source or feed by hand: does it resolve, what do its terms permit,
   what language and geography does it cover?
2. Add the entry with its approval, purpose, stratum, and cap.
3. Bump `config_version` in `sources.example.yml`,
   `source-seeds.example.yml`, and `datapacks.example.yml`. They are one reviewed
   dispatch artifact; validation refuses to run when their versions disagree.
4. Run `uv run --project backend --env-file backend/.env amanah-etl sync-config`
   to project the approved entries into the database.

Do not re-add a feed `docs/news-rss-sources.md` recorded as checked and rejected
— Reuters, AP, the old CTV path — and do not invent a replacement for one.

The current YouTube demo projection maps five video IDs from
`docs/planning/PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` into stable runtime keys:
four enriched discussion seeds and one boundary/control counterspeech seed. Each
is capped at 100 items and was preflighted through the official API on
24 August 2026. This is a purposive hackathon sample, not a representative frame.
