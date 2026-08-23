# Context news stream: RSS allowlist and API contract

Last reviewed: 23 August 2026.

Hand-off for the backend track (B-S9, bounded news ingestion). The frontend
mock already validates this shape at `apps/web/src/api/contracts.ts`
(`NewsItemSchema`, `NewsListSchema`) and renders it on Overview.

## Spec status

This is **not** an invented surface. Specification v2.0 already requires it:

- §5.3 and §6.1: the public dashboard displays current news alongside
  freshness and figures.
- §7.1: `/news` is a filterable listing and **MAY be integrated into the
  dashboard for P0**. This repo does that. There is no new nav tab.
- §13.1: `GET /v1/news` is the public list.
- §10.4: store headline, publisher, canonical URL, short permitted excerpt,
  publication time, retrieval time, language, scope, and explicit location.
  Do not store full article text unless a licence says so.
- §3.3: news may **coincide** with a change. Amanah **MUST NOT** say it
  caused one.

F-S7.1 and F-S8.2 are a different surface: classified news *item cards* with
model summaries and review state. This stream is context only. Do not attach
a hate label, model score, or review state to an ingested article.

## Purpose

Ingest public RSS and Atom feeds to populate a **context news stream** on
Overview (workspace `/app` and public `/dashboard`). Items are published
news, not Amanah classifications. A reader follows the canonical URL to the
publisher. The frontend never fetches YouTube, Reddit, Gemini, or a feed
URL from the browser.

## Proposed API

`GET /v1/news`

Query fields (snake_case):

| Field | Meaning |
| --- | --- |
| `from` | Inclusive UTC calendar date (`YYYY-MM-DD`) |
| `to` | Inclusive UTC calendar date |
| `cursor` | Opaque cursor; omit on the first page |

The frontend scopes the list to the **same date window as the dashboard
figures** so headlines can coincide with the charts. Platform, hate-type,
severity, and review filters do **not** apply.

### Item (`NewsItemSchema`)

```json
{
  "id": "news_bbc_0815",
  "source_name": "BBC News",
  "source_homepage": "https://www.bbc.co.uk/news",
  "title": "Commons hears questions on mosque safety after vandalism in a northern city",
  "summary": "Plain text excerpt. HTML stripped. Not the full article.",
  "url": "https://www.bbc.co.uk/news/uk-politics-2026-08-15-mosque-safety-commons",
  "published_at": "2026-08-15T10:28:00+00:00",
  "retrieved_at": "2026-08-16T23:41:00+00:00",
  "language": "en",
  "scope": "local",
  "location": "United Kingdom"
}
```

`scope` is `local` or `global`. `location` is nullable. Skip images in this
version: do not store or hotlink enclosures until there is a reviewed
cache policy.

### List (`NewsListSchema`)

```json
{
  "window": { "from": "2026-07-18", "to": "2026-08-16", "timezone": "UTC" },
  "applied": { "from": "2026-07-18", "to": "2026-08-16" },
  "coverage": {
    "sources": ["BBC News", "CBC News"],
    "items_retrieved": 10,
    "last_successful_run": "2026-08-16T23:41:00+00:00",
    "warnings": []
  },
  "data_mode": "fixture",
  "next_cursor": null,
  "items": []
}
```

`data_mode` is one of `fixture`, `live`, `fallback`, `stale`,
`unavailable`. A failed ingest is a **gap** (empty list plus a warning),
never a fabricated zero that implies nothing happened.

Timestamps are UTC ISO-8601 with an explicit offset. Ids are stable. Cursor
pagination is required by spec §13 even if the first page is small; the
fixture returns `next_cursor: null`.

The frontend Zod contract uses these snake_case names as-is. Other
dashboard contracts still use camelCase internally; do not reshape news to
match them.

## Verified feeds

Fetched over HTTPS on 23 August 2026. A URL that 404s or requires
credentials is **not** listed. Prefer this short allowlist over a guessed
one.

### Mainstream wire and public-affairs

| Outlet | Homepage | Feed URL | Format | Why in scope | Backend filter | Licence / TOS notes |
| --- | --- | --- | --- | --- | --- | --- |
| BBC News | https://www.bbc.co.uk/news | https://feeds.bbci.co.uk/news/rss.xml | RSS 2.0 | UK and world headlines; religion and public-affairs coverage | Keep UK/US/CA and religion, hate-crime, mosque, Islam, protest, court, election terms; drop sport and celebrity | BBC RSS is for personal, non-commercial use. Store title, link, and a short excerpt. Attribute. Do not archive full text. |
| BBC News UK | https://www.bbc.co.uk/news/uk | https://feeds.bbci.co.uk/news/uk/rss.xml | RSS 2.0 | Domestic UK public affairs | Same topical filter | Same as BBC News. |
| BBC News World | https://www.bbc.co.uk/news/world | https://feeds.bbci.co.uk/news/world/rss.xml | RSS 2.0 | International events that can coincide with a monitoring window | Same topical filter | Same as BBC News. |
| BBC News Politics | https://www.bbc.co.uk/news/politics | https://feeds.bbci.co.uk/news/politics/rss.xml | RSS 2.0 | Policy, parliament, and court-adjacent politics | Prefer home affairs, equalities, and religious-liberty stories | Same as BBC News. |
| The Guardian UK news | https://www.theguardian.com/uk-news | https://www.theguardian.com/uk-news/rss | RSS 2.0 | UK public affairs | Same topical filter | Guardian content is copyrighted. RSS is a discovery feed. Store metadata and a short excerpt. Link back. Do not republish the article. |
| The Guardian World | https://www.theguardian.com/world | https://www.theguardian.com/world/rss | RSS 2.0 | International reporting | Same topical filter | Same as Guardian UK news. |
| The Guardian Islam | https://www.theguardian.com/world/islam | https://www.theguardian.com/world/islam/rss | RSS 2.0 | Religion desk; relevant without treating Muslim vocabulary as harm | Keep reporting; drop lifestyle listicles if they appear | Same as Guardian UK news. Neutral reporting is in scope. |
| CBC News Canada | https://www.cbc.ca/news/canada | https://www.cbc.ca/webfeed/rss/rss-canada | RSS 2.0 | Canadian public affairs (initial geo focus) | Same topical filter | CBC requires attribution. Store snippet and link. Check current RSS terms before any full-text use. |
| CBC News World | https://www.cbc.ca/news/world | https://www.cbc.ca/webfeed/rss/rss-world | RSS 2.0 | International desk from a Canadian public broadcaster | Same topical filter | Same as CBC Canada. |
| CBC News Politics | https://www.cbc.ca/news/politics | https://www.cbc.ca/webfeed/rss/rss-politics | RSS 2.0 | Federal and provincial policy | Prefer rights, hate-crime statistics, and religious-accommodation stories | Same as CBC Canada. |
| CBC Top Stories | https://www.cbc.ca/news | https://www.cbc.ca/webfeed/rss/rss-topstories | RSS 2.0 | Front-page mix; use as a fallback, not the only Canada source | Same topical filter, or skip if the topic feeds already cover the item | Same as CBC Canada. Dedupe by canonical URL. |
| NPR News | https://www.npr.org | https://feeds.npr.org/1001/rss.xml | RSS 2.0 | US public-radio headlines | Same topical filter | NPR asks for attribution and a link. Metadata and short excerpt only. |
| PBS NewsHour | https://www.pbs.org/newshour/ | https://www.pbs.org/newshour/feeds/rss/headlines | RSS 2.0 | US public-affairs headlines | Same topical filter | Public-media RSS. Store title, link, excerpt. No full-text archive. |
| The New York Times World | https://www.nytimes.com/section/world | https://rss.nytimes.com/services/xml/rss/nyt/World.xml | RSS 2.0 | US paper of record, world desk | Same topical filter | All rights reserved. RSS is discovery. Metadata and link only. Respect robots and paywall. |
| The New York Times Politics | https://www.nytimes.com/section/politics | https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml | RSS 2.0 | US policy and court reporting | Prefer religious-liberty, DOJ, and campus-speech stories | Same as NYT World. |
| Al Jazeera English | https://www.aljazeera.com | https://www.aljazeera.com/xml/rss/all.xml | RSS 2.0 | Global English reporting, including Canada and religion | Same topical filter; English only for P0 | Copyrighted. Snippet and canonical link. No full-text scrape. |
| The Globe and Mail | https://www.theglobeandmail.com | https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/canada/ | RSS 2.0 | Canadian national paper, Canada section | Same topical filter | Copyrighted / metered. Metadata and link only. |
| Global News | https://globalnews.ca | https://globalnews.ca/feed/ | RSS 2.0 | Additional Canadian broadcast desk | Same topical filter; dedupe against CBC | WordPress RSS. Excerpt and link. Do not store `content:encoded` full HTML. |
| Sky News | https://news.sky.com | https://feeds.skynews.com/feeds/rss/home.xml | RSS 2.0 | UK broadcast headlines | Same topical filter | Copyrighted. Metadata and link. |
| The Independent UK | https://www.independent.co.uk | https://www.independent.co.uk/news/uk/rss | RSS 2.0 | UK news desk | Same topical filter | Copyrighted. Metadata and link. |

### Civil-society and monitoring orgs (already in the product resource list)

These publish official WordPress RSS. They are **press and research
updates**, not a substitute for classified social items.

| Outlet | Homepage | Feed URL | Format | Why in scope | Backend filter | Licence / TOS notes |
| --- | --- | --- | --- | --- | --- | --- |
| Bridge Initiative | https://bridge.georgetown.edu | https://bridge.georgetown.edu/feed/ | RSS 2.0 | Georgetown research already cited in `/resources` | Keep research notes and explainers; drop events spam if noisy | Site content is copyrighted. Store title, link, short excerpt. Attribute Georgetown / Bridge. |
| Tell MAMA | https://tellmamauk.org | https://tellmamauk.org/feed/ | RSS 2.0 | UK monitoring and support org already in the resource catalog | Prefer research and incident-context posts; never ingest casework or identifiable victims | Copyrighted. No personal data. No full report PDFs unless the licence is reviewed. |
| CAIR | https://www.cair.com | https://www.cair.com/feed/ | RSS 2.0 | US civil-rights press listed in spec § resources | Press releases and public statements only | Copyrighted advocacy content. Snippet and link. Not an Amanah finding. |
| CAIR California | https://ca.cair.com | https://ca.cair.com/feed/ | RSS 2.0 | State-level press already linked from lessons | Same as CAIR | Same as CAIR. |
| NCCM | https://nccm.ca | https://nccm.ca/feed/ | RSS 2.0 | Canadian council already cited in spec resources | Publications and public statements | Copyrighted. Snippet and link. |

### Academic / commentary

| Outlet | Homepage | Feed URL | Format | Why in scope | Backend filter | Licence / TOS notes |
| --- | --- | --- | --- | --- | --- | --- |
| The Conversation UK | https://theconversation.com/uk | https://theconversation.com/uk/articles.atom | Atom | Creative Commons explainers; good for methods language | Religion, media, law, and methods tags | Many articles are CC BY-ND. Still store excerpt plus canonical URL, not a rewritten full text, unless legal review says otherwise. |
| The Conversation Canada | https://theconversation.com/ca | https://theconversation.com/ca/articles.atom | Atom | Same, Canadian desk | Same | Same as Conversation UK. |
| The Conversation US | https://theconversation.com/us | https://theconversation.com/us/articles.atom | Atom | Same, US desk | Same | Same as Conversation UK. |
| Pew Research Center | https://www.pewresearch.org | https://www.pewresearch.org/feed/ | RSS 2.0 | Stable official research feed | Religion, internet, and hate-crime reports | Pew terms restrict republication. Metadata and link. |

## Feeds checked and rejected

| URL | Result on 23 August 2026 | Action |
| --- | --- | --- |
| https://feeds.reuters.com/reuters/worldNews | Host did not resolve | Do not list. Reuters withdrew most public RSS. Use GDELT or a licensed Reuters product later, not a guessed feed. |
| https://www.reutersagency.com/feed/ | HTTP 404 | Do not list. |
| https://apnews.com/index.rss | HTTP 401, "Invalid client credentials" | Do not list. AP is not a free public RSS for this demo. |
| https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009 | HTTP 404 | Do not list. The old CTV public RSS path is gone. |

Do not invent replacements.

## Ingestion notes

1. Fetch on the server only. Never from the React app. Never call YouTube,
   Reddit, or Gemini from the browser.
2. Strip HTML from `description` / `content:encoded` / Atom `summary`.
   Store plain text. Cap the excerpt (suggested 400 characters).
3. Store the canonical `link` (or Atom `rel=alternate`). Normalize trailing
   slashes and tracking query params before dedupe.
4. Dedupe by canonical URL, then by normalized `(source_name, title)`.
5. Refresh with the spec cadence: every eight hours, non-round minute
   (`17 */8 * * *`), plus manual dispatch. Show `last_successful_run`.
   Do not promise exact clock time in the UI.
6. Timeouts, size limits, and per-host rate limits belong on the adapter.
   A host outage is a coverage warning and a gap, not a zero.
7. `fixture` and `live` must stay distinguishable all the way to the
   screen. Never silently substitute fixtures for live data.
8. Images: skip for v1. If added later, cache under first-party storage.
   Do not hotlink publisher CDNs from the dashboard.
9. Language: English only for P0 (`language: "en"`). Drop other items.
10. Geo focus: Canada, United States, United Kingdom, plus clearly global
    religion / hate-crime reporting.

## Out of scope

- Scraping 4chan, 8chan, or any hate forum.
- Aggregating offender lists, author search, or repeat-offender views.
- Automated takedown or auto-submitted platform reports.
- Full-article reproduction.
- Treating a news article as classified anti-Muslim hate.
- Causal claims ("this headline caused the rate to rise").

GDELT remains an allowed discovery path in spec §10.4. This allowlist is
the curated RSS path. Both emit the same `NewsItem` contract.

## How the frontend renders

Section heading on Overview: **In the news**.

Each row shows outlet, absolute UTC date plus a relative phrase, headline
as an outbound link (`target="_blank"`, `rel="noopener noreferrer"`), a
visible "Opens article on {outlet}" cue, and the short summary. Empty,
error, and loading states are separate from the figures. Copy says the
articles **coincide** with the window and are **not** classifications.

Fixture catalog: `apps/web/src/fixtures/news.json` (12 items). Default
dashboard window (2026-07-18 to 2026-08-16) returns 10 of them.
