# Project Amanah — Data, API & Dashboard Blueprint

**Version:** 1.2 — 48-hour hackathon edition  
**Brand:** Project Amanah — Monitoring Anti-Muslim Hate Online  
**Purpose:** Define what is collected, how it becomes model-ready, what the application API exposes, and exactly what the dashboard presents.

> **Open-datapack addendum (2026-08-22):** Reviewed CSV/JSONL datapacks from Kaggle and other open repositories are first-class inputs. Public source/platform is `N/A`; a separate Dataset field/filter and full package/version/license/import/row provenance are required. See the authoritative root [`spec.md`](../spec.md).

> **Seed-registry addendum (2026-08-22):** Use [`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`](../PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md) as the human-reviewed candidate catalog for initial Reddit/YouTube seeds and queries. Runtime jobs use only approved stable keys in versioned configuration, preserve sampling strata and caps, and never treat this enriched set as representative prevalence evidence.

> **Authentication-scope addendum (2026-08-22):** The dashboard and all product-data APIs are authenticated. Only the static marketing homepage, authentication entry/callback routes, and health/readiness endpoints remain anonymous. Anonymous requests must not receive even redacted dashboard, item, resource, methodology, or connector data; see the authoritative root [`spec.md`](../spec.md).

## 1. Build decision in one page

The hackathon system should support two ways to choose source content:

1. **Discovery mode:** search YouTube by maintained queries, retrieve matching video IDs, then collect their comments.
2. **Seed mode:** accept known YouTube video IDs/URLs and process them directly. This is the reliable demo fallback.

Reddit is an optional adapter. It can search **submissions**, globally or within named subreddits, then collect each submission’s comment tree. Do not promise global keyword search across Reddit comments. Bluesky and GDELT should remain prepared-data or stretch integrations until the YouTube vertical slice works.

X, Threads, Instagram/Facebook, TikTok and Mastodon are documented adapter targets, not 48-hour promises. Use official APIs only. Show `Not configured`, `Access required` or `Fixture only` in Connections rather than scraping a website or implying live coverage.

The hackathon demo defaults to synthetic, redacted or controlled material. Live collection and third-party AI inference are separate permissions: even if a source API permits collection, do not send real hateful content or personal data to Gemini/another hosted model without explicit authorization covering that transfer.

Recommended deployed flow:

```text
query registry / seed URLs
          │
          ▼
 source discovery and collection
          │
          ▼
 canonical raw content records
          │
          ▼
 deterministic normalization
          │
          ▼
 cheap Muslim-relevance filter
          │
          ▼
 structured ML/API classification
          │
          ▼
 Supabase predictions + daily metrics
          │
          ▼
 Render FastAPI → Netlify dashboard
```

### 1.1 User journey

```text
Public marketing site
  → Log in
  → Supabase Auth session
  → Protected application shell
      1. Overview
      2. Explorer
      3. Insights
      4. Narratives
      5. Meme Signals
      6. Review
      Utility: Reports · Sources & Coverage · Connections · Settings · Methodology · Log out
```

Use one Netlify React application with public and protected route groups. The marketing page is public; every raw-content, search, review and AI route requires authentication. For the hackathon, disable open registration and create one invited demo/reviewer account.

### 1.2 Marketing page

Recommended flow:

1. Navigation: Project Amanah wordmark, Why Amanah, How it works, Responsible use, Methodology, Log in.
2. Hero: overline “A trust we carry together”; headline “Understand how anti-Muslim hate moves online.” Supporting line: “Turn authorized public signals into trends, narratives, context and reviewable reports—without profiling people.” Show “See how it works” and “Log in.”
3. Meaning of Amanah: explain that *amanah* is a trust and that care for one another calls for truthful, wise and just response to harm. Connect mutual care, enjoining good, forbidding wrong and **ghayrah**—disciplined protective concern for the deen—to the refusal to normalize hate.
4. Human problem: isolated incidents vanish into feeds; repeated exposure can create fatigue, numbness and normalization while the cumulative pattern remains invisible.
5. Capability gap: communities need longitudinal evidence, not another feed of harmful posts.
6. Three questions: how much in the monitored sample, what kind, and what changed around it.
7. How it works: Capture → Classify → Contextualize → Route to human review → Learn and report. Describe the workflow as a trust made operational.
8. Product proof: click a synthetic/redacted spike, drill into filtered evidence, review an item, and generate a scoped report.
9. Community/news context: approved communities, reviewable discovery candidates, and local/global news overlays.
10. Responsible use: justice in classification, restraint in collection, authorized access, sample limitations, no automated enforcement, no identity inference, correlation-not-causation and no unapproved third-party AI transfer.
11. Methodology/disclosure: AI tools, datasets, licenses, earlier work, evaluation and known limitations.
12. Footer/close: privacy, security, accessibility, contact, “Carry the trust with care” and log in.

Define Arabic/Islamic terms once in plain English. Do not frame ghayrah as anger, possessiveness or permission to police people, and do not frame “forbidding wrong” as coercion, vigilantism or automated punishment. The product is not a religious authority; the faith framing should receive scholar/community-advisor review before production use.

Do not show real hateful comments, raw user identities or unblurred memes on the public page.

## 2. Source capability matrix

| Source | How content is discovered | What can be collected | Must links be supplied? | Important limitation | 48-hour recommendation |
|---|---|---|---|---|---|
| YouTube | `search.list` with keyword query, date, region/language, order, and `type=video`; or curated channel/upload lists | Video ID and metadata, statistics, top-level comments, replies, timestamps, authors/channel IDs, likes | No. Queries discover videos. Seed IDs/URLs are still valuable for a reliable demo. | Search is quota-limited; disabled comments and omitted/deleted replies create coverage gaps. No general public transcript download through the Data API. | Primary live source: 3–5 queries, 5–10 videos/query, capped comments/video, plus 5 seed videos. |
| Reddit/PRAW | Search submissions through `r/all` or named/combined subreddits; monitor new submissions/comments in named subreddits | Submission title/body/URL/score/time/subreddit and nested thread comments/replies | No for submission search. Seed post URLs are useful. Named subreddits are recommended for scope. | No equivalent public API for global keyword search over all comments. API approval/terms may block the demo; very large comment trees need expansion requests. | Adapter interface or prepared fixture only unless credentials already work. |
| Bluesky | `app.bsky.feed.searchPosts` for search; `getPostThread` for context; Jetstream/firehose for live events | Post text, URI/CID, author identifiers, timestamps, reply/quote/embed references, interaction counts and labels | No for search. Seed post URIs can guarantee examples. | Jetstream filters by collections/repos, not arbitrary hate keywords; application must filter locally. Full stream volume is unnecessary for the demo. | Stretch search adapter or cached fixture; do not run the full firehose. |
| X | Official recent/full-archive post search with keyword, phrase, language, reply/repost and media operators | Post/conversation IDs, text, timestamps, referenced posts, public metrics and requested expansions/fields | No for search; developer project/app and bearer token are required. | Recent search covers seven days; full archive is pay-per-use/Enterprise. Access, pricing and retention rules can change. | Disabled adapter/fixture unless working access and budget are confirmed; never scrape X. |
| Threads | Official keyword search with `TOP`/`RECENT` and `threads_keyword_search` permission | Public matching Threads fields granted by the API, including text, permalink, owner/username, timestamp and media metadata | No for keyword search; Meta app/token/permission required. | App configuration, permission review, tokens and rate limits must be verified; owner fields must be pseudonymized/not exposed. | Stretch adapter only if credentials already work; otherwise fixture. |
| Instagram/Facebook | Instagram professional-account/hashtag capabilities or Meta Content Library/API for qualified researchers | Scope-dependent public media/comments/metadata in approved products/research environment | Generally no, but access/app/institutional approval is required. | Instagram API is not a general public-comment firehose; Meta Content Library access is application-gated. | Not a hackathon dependency; document future connector only. |
| TikTok | Approved Research API video queries, then comment/reply retrieval by `video_id`/`comment_id` | Public video metadata and comment text/likes/replies/timestamps within approved fields | Query can discover videos after research access; a video ID is required for comment retrieval. | Research access is limited to approved qualifying researchers and scopes. A public URL alone is insufficient. | Not live in 48 hours; use a disclosed fixture and no scraping. |
| Mastodon | Per-instance hashtag/public timelines and instance-configured search | Status text/HTML, IDs/URLs, timestamps, account IDs, replies/reblogs/favourites and media metadata | Instance/hashtag must be selected; some search requires a user token. | No global fediverse search; full-text status search depends on the instance/backend and federation visibility. | Optional later adapter for named instances; lower priority than YouTube/Bluesky. |
| GDELT DOC 2.0 | Keyword/Boolean news search with time window, sort and result cap | Article title, URL, domain/source metadata, language/country fields when available, seen time, social image | No. Queries discover articles. | Discovery metadata is not a licensed full-text article corpus; coverage and volume do not imply causation. | Query only after a detected/prepared spike; cache 5–10 candidate articles. |
| NewsAPI (optional) | `/v2/everything` for article discovery and `/v2/top-headlines` for breaking headlines | Source, author when supplied, title, description, URL, image URL, publication time and truncated content field | No. Queries discover articles; an API key is required. | Plan/licensing/production-use limits must be checked; returned content is not a complete article archive. | Add only if a key already works and a second provider materially improves the demo; GDELT alone is enough for the MVP. |
| RSS/curated web | Maintained feed/page allowlist | Feed title, URL, published time, summary/excerpt, publisher | Feed URLs must be configured. | Terms, robots, paywalls and unstable HTML; avoid general scraping during the hackathon. | Defer or use one curated RSS feed for event context. |

Current authoritative references:

- [YouTube `search.list`](https://developers.google.com/youtube/v3/docs/search/list)
- [YouTube `videos.list`](https://developers.google.com/youtube/v3/docs/videos/list)
- [YouTube `commentThreads.list`](https://developers.google.com/youtube/v3/docs/commentThreads/list)
- [YouTube API reference](https://developers.google.com/youtube/v3/docs) — a comment thread may not contain every reply; use `comments.list` for complete replies.
- [PRAW subreddit/search documentation](https://praw.readthedocs.io/en/latest/code_overview/models/subreddit.html)
- [PRAW comment extraction](https://praw.readthedocs.io/en/stable/tutorials/comments.html)
- [Reddit Data API Terms](https://redditinc.com/policies/data-api-terms)
- [Bluesky firehose and Jetstream](https://docs.bsky.app/docs/advanced-guides/firehose)
- [X post search](https://docs.x.com/x-api/posts/search/introduction)
- [Official Meta Threads keyword-search request](https://www.postman.com/meta/threads/request/m9j4i2x/search-for-threads-posts)
- [Official Meta Instagram API workspace](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta Content Library/API access overview](https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/)
- [TikTok Research Tools](https://developers.tiktok.com/docs/en/about-research-api) and [video-comment endpoint](https://developers.tiktok.com/doc/research-api-specs-query-video-comments)
- [Mastodon search API](https://docs.joinmastodon.org/methods/search/)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [NewsAPI endpoints](https://newsapi.org/docs/endpoints)

## 3. YouTube data requirements

### 3.1 Discovery configuration

Store searches as records rather than hard-code them:

```yaml
- id: yt-broad-muslim-context-en-ca
  source: youtube
  enabled: true
  query_purpose: broad_relevance
  sampling_stratum: ordinary_monitoring
  query: 'Muslim|Islam'
  published_after: '2026-08-09T00:00:00Z'
  order: date
  region_code: CA
  relevance_language: en
  max_videos: 10
  max_comments_per_video: 100

- id: yt-local-event-context-en-ca
  source: youtube
  enabled: true
  query_purpose: event_context
  sampling_stratum: event_window
  query: 'Muslim|Islam REVIEWED_EVENT_TERM'
  event_id: REPLACE_WITH_NEWS_EVENT_ID
  published_after: '2026-08-09T00:00:00Z'
  order: date
  region_code: CA
  relevance_language: en
  max_videos: 10
  max_comments_per_video: 100

- id: yt-seed-hackathon
  source: youtube
  enabled: true
  query_purpose: controlled_seed
  sampling_stratum: demo_fixture
  seed_video_ids:
    - REPLACE_WITH_APPROVED_VIDEO_ID
```

Use several narrow queries instead of one enormous expression. Keep a `query_version` so the dashboard can explain which terms produced the sample.

#### How to search for videos likely to contain hateful comments

Do not put the entire hate lexicon into YouTube search. The defensible workflow is:

1. Discover videos with neutral Muslim-relevance terms, approved public-event terms and selected channels/time windows.
2. Fetch comments from those videos within fixed per-video caps.
3. Apply the relevance and hate classifiers locally to comment text/context.
4. Use any explicit high-risk search only as a separately labelled `oversampled_high_risk` stratum for finding test/review cases—not for ordinary prevalence metrics.

This reduces selection bias and captures counterspeech/neutral discussion needed to estimate false positives. Store `query_purpose` and `sampling_stratum` with every item; dashboards may compare strata but must not silently combine them.

### 3.2 API sequence

1. `search.list(part=snippet,type=video,q=...,publishedAfter=...,order=date,maxResults<=50)` returns candidate video IDs, title/channel snippets, publish time and thumbnails.
2. `videos.list(part=snippet,statistics,status,id=...)` enriches candidates with canonical title/description/channel, view/like/comment counts, and status.
3. `commentThreads.list(part=snippet,replies,videoId=...,order=time,maxResults=100,textFormat=plainText)` returns top-level comments and possibly some replies.
4. When `totalReplyCount` exceeds included replies, call `comments.list(parentId=...,maxResults=100,textFormat=plainText)` until its page token is exhausted or the configured cap is reached.

Store `nextPageToken` only while a bounded run is active. For repeat runs, upsert by YouTube comment ID and fetch recently updated/new videos rather than assuming page tokens remain a permanent cursor.

### 3.3 Fields to retain

**Video:** `video_id`, `channel_id`, channel title, title, description, published time, thumbnail URL, tags when returned, category, default language, view count, like count, comment count, collection query ID, retrieved time.

**Comment:** `comment_id`, `video_id`, `parent_comment_id`, text display/plain text, author channel ID pseudonym, author display name only if truly needed for source fidelity, published time, updated time, like count, reply count, moderation/public status when available, retrieved time.

Do not treat author display name as an analytic dimension. Do not expose author rankings. Counts are collection-time snapshots and should have an `observed_at` timestamp.

### 3.4 Sampling policy

For the demo:

- Maximum 5 queries.
- Maximum 10 videos per query.
- Maximum 100 top-level comments per video.
- Maximum 100 additional replies per video.
- English only, with non-English items stored as `unsupported_language` rather than classified.
- Record videos with disabled comments as `comments_unavailable`, not zero comments.

The denominator is **comments successfully collected from monitored videos**, not “all YouTube comments.”

## 4. Reddit data requirements

### 4.1 Define the subreddit registry first

The administrator must explicitly approve the subreddits used for monitoring. Store:

- subreddit name and opaque ID when available;
- public URL, topical/geographic category and language;
- inclusion rationale and who approved it;
- query set and sampling stratum;
- `candidate`, `active`, `paused` or `rejected` state;
- start/end and next-review dates;
- terms/policy snapshot and known access limitations.

Choose a balanced initial sample: 2–3 public topical or local-news communities, 1–2 general-discussion communities and approved seed threads. Do not select only communities believed to be hostile and then generalize the results. Never describe an entire subreddit as hateful because some sampled items were classified that way.

### 4.2 Discovery modes

PRAW supports submission search in a particular subreddit, a combined set such as `canada+worldnews`, or the special `all` view:

```text
reddit.subreddit("all").search(query)
reddit.subreddit("canada+worldnews").search(query)
reddit.submission(url=seed_url)
```

Recommended production-research mode: maintain an approved subreddit registry and search submissions within it. Recommended hackathon mode: use 2–3 seed threads or a redacted cached fixture if credentials/access are uncertain.

### 4.3 What search does and does not do

- Submission search returns matching posts; it does not provide a dependable global search across all comment bodies.
- Once a matching submission is found, PRAW can traverse its `CommentForest` and expand `MoreComments` placeholders within configured request and item limits.
- A subreddit comment stream can monitor new comments prospectively, but high-volume streams may drop items and require a continuously running process.
- A seed submission URL or ID can be opened directly and its thread collected.

#### Community scouting

A bounded `r/all` **submission** search may record the subreddit attached to each matching post. Aggregate candidates by distinct matching submissions, distinct threads, change against their own observed baseline and narrative novelty. Require minimum counts and send the result to a Community Discovery Queue. Monitoring begins only after an analyst approves the candidate; the system never follows individual users, joins identities across communities or autonomously expands scope.

### 4.4 Fields to retain

**Submission:** base36/fullname ID, subreddit, title, selftext, canonical permalink, outbound URL/domain, created UTC, edited state/time, score snapshot, upvote ratio, number-of-comments snapshot, flair/NSFW/spoiler flags, collection query ID.

**Comment:** ID/fullname, submission ID, parent fullname, body, created UTC, edited state/time, score snapshot, depth, distinguished/stickied flags, retrieved time, author pseudonym.

Do not store profile histories or build author-level behavioral records. Reddit content must follow approved API access, terms, retention and deletion rules.

### 4.5 PRAW credentials and access

For a server-side, public read-only PRAW client, configure:

```python
import os
import praw

reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    user_agent=os.environ["REDDIT_USER_AGENT"],
)
reddit.read_only = True
```

The required runtime values are:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`, using a descriptive format such as `web:project-amanah:0.1 (by u/youraccount)`

PRAW handles the application-only OAuth token exchange. A Reddit username/password is not required for public read-only queries. User-authorized/private/write operations require the applicable OAuth flow and scopes/refresh token.

Possessing an old client ID and secret is not, by itself, authorization to collect data. Reddit currently requires OAuth, explicit approved access under its Responsible Builder Policy, and compliance with the Developer/Data API terms. Test old credentials from the backend; if Reddit returns unauthorized/forbidden, do not scrape HTML as a fallback. Keep the secret only on Render, never in Netlify or browser code.

Reddit’s Data API terms also restrict using User Content to train an ML/AI model without express rightsholder permission. Treat Reddit content as approved-use monitoring input only, not training data, unless the required permissions and approved use explicitly cover training.

## 5. Additional social sources and current-events/news requirements

### Bluesky

Use search for the MVP-style adapter and store post URI + CID as the source key. Retain post text, created/indexed time, reply/quote references, embed type/thumbnail reference, author DID pseudonym, and counts observed at collection. Fetch a thread only for selected results or review context.

Jetstream is a later ingestion strategy:

```text
subscribe to app.bsky.feed.post
 → checkpoint stream time
 → decode JSON event
 → apply local relevance filter immediately
 → retain candidates only
```

It is not a server-side keyword-search feed.

### X

Adapter configuration: bearer token, reviewed query, start/end time, requested fields/expansions, maximum pages and sampling stratum. Use recent search only for the initial adapter; store conversation/reply references for context. Full-archive access is a separate commercial/access decision. Return `access_required` when credentials/plan do not permit the request and never fall back to browser scraping.

### Threads

Adapter configuration: Meta app ID, server-held long-lived token, `threads_keyword_search` permission, `TOP` or `RECENT`, reviewed keyword query and hard result cap. Pseudonymize owner IDs and do not expose usernames. Verify the official API response/limits with the actual app before enabling; otherwise use `fixture_only`.

### Instagram/Facebook

Do not create a generic Graph API scraper. The ordinary Instagram API is suitable for approved professional-account/hashtag workflows, not arbitrary platform-wide comments. Meta Content Library/API belongs behind an institutional-access connector with its own data-governance review. In Connections, use `institutional_approval_required` rather than asking for a consumer login.

### TikTok

The future adapter uses Research API video discovery followed by comment requests keyed by `video_id`; replies use `comment_id`. Required configuration includes an approved research client, token/scopes, fields, reviewed query/date range and hard caps. If research access is absent, the connector is disabled. Do not use headless browsers or unofficial endpoints.

### Mastodon

The adapter takes an allowlist of instance base URLs and optionally an instance-specific user token. Discovery uses approved hashtags/public timelines or the instance search endpoint. Every item retains `instance_host`; coverage is reported per instance because no call represents the whole fediverse.

### GDELT

Store each event-search execution and its exact query/window. For each result retain provider ID if any, title, canonical URL, domain, seen/published time as supplied, language/source country when supplied, social-image URL, and retrieval timestamp. Keep only permitted excerpts. Cache the result used in the demo so the event card does not disappear if ranking changes.

GDELT is the recommended hackathon provider because it supports full-text article discovery, Boolean queries, time windows, JSON results and timeline views without adding another product dependency. It supplies reporting context—not verified causation and not necessarily the underlying real-world event record.

Configure news queries in two groups:

- `local`: named city/province/state/country terms, local outlet allowlist and Islamophobia/anti-Muslim context terms;
- `global`: reviewed major-event terms, broad outlet/domain diversity and language/region filters.

Store the assigned scope with each result. A single story may be both locally and globally relevant; this is a query tag, not inferred user geography.

### Optional NewsAPI/RSS adapter

Use NewsAPI only as a swappable second `NewsProvider` implementation. `/v2/everything` supports query-based article discovery; `/v2/top-headlines` supports recent headline discovery. Keep the API key on Render/GitHub Actions. Store provider metadata and permitted snippets, never assume the response contains or licenses full article text.

All providers emit one canonical `NewsEventCandidate`:

```json
{
  "provider": "gdelt",
  "provider_item_id": "optional-stable-id",
  "query_id": "news-query-uuid",
  "title": "Article headline",
  "canonical_url": "https://publisher.example/article",
  "source_domain": "publisher.example",
  "published_at": "2026-08-16T10:00:00Z",
  "observed_at": "2026-08-16T11:00:00Z",
  "language": "en",
  "description": "Permitted short description",
  "metadata": {}
}
```

Deduplicate providers by normalized canonical URL first, then conservative title similarity. Retain all provider observations for provenance. Do not ingest full publisher pages during the hackathon.

## 6. Canonical data contract

All collectors emit the same shape before ML:

```json
{
  "id": "internal-uuid",
  "source": "youtube",
  "source_item_type": "comment",
  "source_item_id": "Ug...",
  "thread_id": "youtube-video-id",
  "parent_source_id": null,
  "canonical_url": "https://www.youtube.com/watch?v=...&lc=...",
  "author_pseudonym": "hmac:v1:...",
  "published_at": "2026-08-16T12:34:56Z",
  "updated_at": "2026-08-16T12:34:56Z",
  "observed_at": "2026-08-16T13:00:00Z",
  "language": "en",
  "text_raw": "source text",
  "text_normalized": "model-neutral normalized text",
  "context": {
    "thread_title": "video or submission title",
    "parent_text": null,
    "source_container": "channel or subreddit"
  },
  "engagement": {
    "likes_or_score": 3,
    "reply_count": 0
  },
  "collection": {
    "run_id": "uuid",
    "query_id": "yt-islam-muslim-en",
    "query_version": 1
  },
  "media": [],
  "raw_metadata": {}
}
```

Required for every row: source, type, source ID, published/observed time, collection run/query, raw or source-faithful text, normalization version, deletion state, and a uniqueness constraint on `(source, source_item_id)`.

## 6A. Cross-source field normalization

Collectors must not pass source-specific objects directly into classification or dashboard code. Each adapter converts its source response into a versioned canonical `ContentItem`. Keep the untouched permitted source response separately for debugging/provenance; the canonical row is the stable application contract.

### Data layers

```text
Layer 1 — Source payload
  Exact permitted API response or minimal retained subset
  Source-specific and access-controlled

Layer 2 — Canonical content
  Common fields shared by every source
  Used by search, API, dashboard and job orchestration

Layer 3 — Derived analysis
  Normalized/model input, filter matches, embeddings and predictions
  Reproducible and versioned

Layer 4 — Aggregates
  Daily/hourly counts, rates, narratives, coverage and signals
  Used by dashboard metrics and Gemini fact bundles
```

### Canonical content types

Use one controlled enum:

- `video`
- `submission`
- `post`
- `comment`
- `reply`
- `news_article`
- `meme`

`comment` is a top-level response to a root item; `reply` has another comment/post as its direct parent. A YouTube video, Reddit submission or Bluesky root post provides thread context but does not need to enter the hate-classification queue unless its own text is intentionally monitored.

### Source-to-canonical mapping

| Canonical field | YouTube | Reddit | Bluesky | GDELT/news |
|---|---|---|---|---|
| `source` | `youtube` | `reddit` | `bluesky` | `gdelt` or `news` |
| `content_type` | video → `video`; top-level comment → `comment`; child → `reply` | link/submission → `submission`; top-level comment → `comment`; child → `reply` | root record → `post`; reply record → `reply` | `news_article` |
| `source_item_id` | video ID or comment ID | base36 ID/fullname | AT URI; retain CID separately | provider ID when stable, otherwise hash of canonical URL |
| `thread_id` | video ID | submission fullname/ID | root post URI | canonical article URL or event/query grouping ID |
| `root_id` | video ID | submission ID | root post URI | canonical article URL |
| `parent_source_id` | parent comment ID; null for top level | parent fullname; submission fullname for top-level comment | reply parent URI; null for root post | null |
| `title` | video title for video; null on comment row | submission title; null on comment row | null unless generated for display, never source-attributed | article title |
| `text_raw` | video description or comment `textOriginal`/plain-text value | submission `selftext` or comment `body` | post record `text` | permitted excerpt/description, not assumed full article body |
| `canonical_url` | watch URL with video ID and optional comment ID | permalink | resolvable post URL derived from handle/URI when available | article URL |
| `container_id` | channel ID or approved video cohort | subreddit fullname/name | approved feed/list/query-cohort ID; never silently substitute author DID | domain/publisher ID or news-scope ID |
| `container_label` | channel/cohort title | subreddit display name | feed/list/query label | publisher/domain or `local`/`global` scope |
| `author_source_id` | author channel ID | Reddit account name/ID when returned | author DID | publisher, not journalist identity unless explicitly needed |
| `published_at` | `publishedAt` | `created_utc` | record `createdAt` | published/seen time supplied by provider |
| `updated_at` | `updatedAt` when supplied | edited timestamp when present | indexed/record update metadata when supplied | updated time when supplied |
| `observed_at` | collector retrieval time | collector retrieval time | collector retrieval/index time | GDELT/query retrieval time |
| `language` | metadata language or detected from text | detected from text | record language tags plus detection | provider language plus detection if excerpt exists |
| `like_count` | comment likes or video likes | null; Reddit score is not a like count | post like count | null |
| `score` | null | submission/comment score snapshot | null | null |
| `reply_count` | thread/comment reply count | submission/comment descendants when available | reply count snapshot | null |
| `view_count` | video view count | null | null | null |
| `repost_count` | null | crosspost metadata remains source-specific | repost count snapshot | null |
| `media` | video thumbnail or attached image reference | preview/media/linked image when permitted | image/embed references | social-image URL when supplied |

Additional adapters use the same contract:

- **X/Threads:** post → `post`, reply → `reply`; conversation/root ID → `thread_id`; approved query/list/cohort → `container_id`; platform user ID remains `author_source_id`, never the community key.
- **Instagram/Facebook:** media/post → `post`, comment/reply hierarchy preserved; professional account, hashtag/query cohort or approved research collection → `container_id`.
- **TikTok:** video → `video`, top-level video comment → `comment`, comment response → `reply`; search cohort/approved creator collection → `container_id`.
- **Mastodon:** status → `post` or `reply`; root status → `thread_id`; instance plus approved hashtag/list cohort → `container_id`; retain `instance_host` in source metadata.

Every content row may reference `community_registry_id`. A community is a source-scoped sampling container, not a person. Never use `author_source_id` as `community_registry_id` unless the approved research design explicitly monitors an organization-owned public channel and documents that choice.

### Canonical `ContentItem` fields

```text
Identity and hierarchy
  id                    internal UUID
  source                controlled source enum
  content_type          controlled content type enum
  source_item_id        source-native stable identifier
  thread_id             source-native discussion/thread identifier
  root_id               root item identifier
  parent_source_id      direct parent or null
  community_registry_id approved source-scoped sampling container or null

Content and context
  title                 source title or null
  text_raw              source-faithful text or null
  text_normalized       derived text or null
  canonical_url         permitted source link or null
  container_id          channel/subreddit/publisher/feed identifier or null
  container_label       display label or null
  root_title            copied thread title for model/search context
  parent_text           bounded parent text snapshot when permitted
  language              normalized language code or `und`

Actor
  author_pseudonym      source-scoped keyed HMAC or null
  author_display        encrypted/restricted source display name only if required

Time
  published_at          source creation/publication time in UTC
  updated_at            source edit/update time in UTC or null
  observed_at           collector retrieval time in UTC

Engagement snapshots
  like_count            nullable integer
  score                 nullable integer
  reply_count           nullable integer
  view_count            nullable integer
  repost_count          nullable integer
  engagement_observed_at timestamp for the snapshot

Collection and provenance
  source_query_id
  collection_run_id
  adapter_version
  canonical_schema_version
  raw_payload_object_key or permitted raw payload JSON
  source_status          active/deleted/unavailable/removed
  deletion_observed_at
  raw_metadata           small source-specific remainder only
```

### Null, zero and unavailable semantics

- `0` means the source explicitly reported zero.
- `null` means not applicable, not returned, not permitted or unknown; add a status/reason when the distinction matters.
- Never convert a missing count into zero.
- Never convert deleted/removed text into an empty string. Set `source_status` and preserve only the permitted tombstone/provenance fields.
- Keep `published_at` distinct from `observed_at`; a newly discovered item can be old.
- Store all timestamps as timezone-aware UTC while retaining the original source value in the raw payload where permitted.

### Engagement is not directly comparable

YouTube likes, Reddit score and Bluesky likes are different platform constructs. Store them in separate nullable canonical columns and label charts by source. Do not create a cross-platform “engagement score” for the MVP. If a later normalized measure is needed, calculate a clearly versioned within-source percentile and never present it as an absolute platform comparison.

### Author normalization

Generate `author_pseudonym = HMAC(secret, source + ':' + source_author_id)` on the backend. This provides stable within-platform grouping without exposing raw handles. Use a source prefix so identities are never joined across platforms. If a source does not return a stable author identifier, leave it null rather than hashing a display name.

### Adapter interface

Every collector implements the same boundary:

```python
class SourceAdapter(Protocol):
    source: SourceName
    adapter_version: str

    def discover(self, query: SourceQuery) -> Iterable[DiscoveredItem]: ...
    def fetch(self, item: DiscoveredItem) -> SourcePayload: ...
    def to_canonical(self, payload: SourcePayload, run: CollectionRun) -> list[ContentItem]: ...
```

`to_canonical` is deterministic: the same payload, run metadata and adapter version must produce the same canonical identity and field values. Source pagination, retries and credentials stay outside the canonical model.

### Mapping validation and tests

For each adapter, keep redacted recorded fixtures and assert:

- source IDs and parent/root relationships map correctly;
- timestamp units/timezones are correct;
- HTML entities/source markup decode once, not twice;
- deleted/unavailable items use status rather than empty text;
- missing engagement remains null;
- author pseudonyms are stable within a source and different across sources;
- a repeated collection upserts instead of duplicating;
- source edits update the appropriate fields while preserving audit/provenance;
- unexpected source fields do not break the canonical parser;
- canonical schema and adapter versions are recorded.

The ML pipeline accepts only validated canonical `ContentItem` objects. The dashboard API accepts canonical/derived views only; it never reads YouTube, Reddit, Bluesky or GDELT payload shapes directly.

## 7. Text normalization for NLP/ML

### 7.1 Keep three representations

1. **`text_raw`:** source-faithful text, access-controlled; used for review/evidence.
2. **`text_normalized`:** minimally and deterministically cleaned; used for filtering, duplicate detection and most models.
3. **`model_input`:** task/model-specific assembly and truncation created at inference time; reproducible from raw/normalized fields and configuration.

Never overwrite the raw value with cleaned text. Record `normalization_version` and `model_input_hash`.

### 7.2 Recommended normalization order

```text
source text
 → decode source HTML entities / select plain-text field
 → normalize line endings
 → Unicode NFKC normalization
 → remove control and zero-width characters except meaningful whitespace
 → collapse repeated whitespace
 → canonicalize URLs to <URL>
 → canonicalize explicit user mentions to <USER>
 → retain hashtag words, emoji, punctuation, casing and negation
 → trim
```

Optional secondary features—not destructive edits—include emoji descriptions, domain extracted from URL, hashtag segments, repeated-character count, all-caps ratio, and slur-pattern match IDs.

### 7.3 Do not do these

- Do not remove stopwords: words such as “not,” pronouns, and group references affect hate meaning.
- Do not stem or lemmatize model text by default: transformer tokenizers handle surface forms and morphology.
- Do not remove emoji, punctuation, hashtags, quotes, or casing globally.
- Do not translate every item before classification without evaluating translation bias.
- Do not map Muslim/Islam identity terms to a generic placeholder; the relevance stage needs them and the hate stage needs target context.
- Do not strip quoted hateful language: mark quotation/counterspeech and preserve context instead.
- Do not run the hate model only on keyword-matched fragments; classify the complete bounded statement.

### 7.4 Context assembly

Recommended text-model input:

```text
[SOURCE_TITLE] {video title or Reddit submission title}
[PARENT] {direct parent text, if short and available}
[CONTENT] {comment/post body}
```

For relevance filtering, use content plus source title. For hate classification, make the content segment primary and include a bounded parent/title context. Never include usernames. If model length is exceeded, preserve the entire focal comment when possible; truncate context first. If the focal comment itself is too long, use a reproducible head+tail strategy and set `was_truncated=true`.

For memes:

```text
[POST_CONTEXT] caption/post text
[OCR_TEXT] text extracted from the image
```

The multimodal model must still receive the image; concatenating OCR and caption is not multimodal reasoning.

### 7.5 Language and duplicate handling

- Detect language after minimal Unicode cleanup; store language and confidence.
- In the English MVP, classify only high-confidence English. Queue unknown/mixed language rather than translating silently.
- Exact duplicate: SHA-256 of normalized text plus source/thread scope.
- Near duplicate: SimHash/MinHash or embedding similarity, recorded as a cluster suggestion rather than deletion.
- Keep repost/quote metadata; duplicate propagation is analytically meaningful even when only one item is sent to an expensive model.

### 7.6 Normalization test cases

The test suite must cover HTML entities, smart quotes, Arabic script and RTL marks, combining characters, zero-width evasion, emojis, URLs, mentions, hashtags, repeated punctuation, quoted speech, censored slurs, empty/deleted content, and strings containing HTML/JavaScript. Rendering must escape content even after normalization.

## 8. Classification input and output contract

Run relevance before the more expensive hate classifier:

```json
{
  "muslim_relevant": true,
  "relevance_confidence": 0.94,
  "stance": "anti_muslim_hate",
  "hate_confidence": 0.87,
  "types": ["derogation", "collective_blame"],
  "severity": 2,
  "narrative": "collective blame / security threat",
  "rationale": "The statement assigns criminal intent to Muslims as a group.",
  "evidence_spans": ["bounded excerpt"],
  "requires_review": true,
  "abstain_reason": null
}
```

Allowed stance values: `anti_muslim_hate`, `non_hateful_discussion`, `counterspeech_or_quotation`, `uncertain`, `not_relevant`.

Allowed types for the demo: `animosity`, `derogation`, `dehumanization`, `exclusion`, `threat`, `collective_blame`. Severity: 0 non-hateful, 1 derogatory/animosity, 2 dehumanization/exclusion/collective incitement, 3 credible or explicit threat/incitement. A model output is always labeled `model_only` until reviewed.

Validate hosted-model JSON with Pydantic. On validation failure, retry once with the same idempotency key, then store `inference_failed`; do not invent default labels.

Before any hosted inference, enforce a data-policy gate:

```text
synthetic | redacted | controlled-and-authorized → hosted model allowed
real harmful/personal content without explicit transfer authorization → local model or fixture only
```

Set `ALLOW_THIRD_PARTY_CONTENT_INFERENCE=false` by default. Record `data_class`, `transfer_authorization_id` when applicable and `inference_location=local|hosted|fixture` with each prediction. Never rely on a prompt instruction alone to enforce this boundary.

## 9. Is an application API needed?

**Yes.** Netlify serves browser code, so any value sent there is public. The browser must not contain the YouTube key, Reddit secret, hosted-model token, Supabase service-role key, evidence-signing logic, or unrestricted database access.

The Render FastAPI service should:

- hold server secrets;
- trigger bounded collection and classification;
- validate filters and structured model output;
- expose safe aggregates and redacted content;
- enforce review transitions and audit history;
- protect the browser from raw source-specific schemas.

The frontend may use Supabase Auth directly with its public anon key, then send the user JWT to FastAPI. FastAPI verifies the JWT and performs role-aware queries. For the simplest private hackathon demo, a single reviewer login is sufficient.

## 9A. Full-text search and autocomplete

The protected **Explorer** should provide full-text search over authorized content. Use Postgres/Supabase full-text search rather than loading rows into the browser. Supabase documents native [Postgres full-text search](https://supabase.com/docs/guides/database/full-text-search), and Postgres provides `websearch_to_tsquery` for forgiving web-style queries including quoted phrases, `OR`, and exclusions.

### Search index

Add a stored/generated `search_vector` to `content_item` built from fields with different weights:

```sql
setweight(to_tsvector('english', coalesce(context_json->>'thread_title', '')), 'A') ||
setweight(to_tsvector('english', coalesce(text_normalized, '')), 'B') ||
setweight(to_tsvector('simple',  coalesce(prediction.narrative, '')), 'C')
```

In a real migration, prediction-derived fields are denormalized into an authorized search document or joined through a controlled SQL function; a generated column cannot directly reference another table. Create a GIN index on the vector. Use `websearch_to_tsquery` for user input and `ts_rank_cd` for relevance ranking. Always combine the search with role, date, source and content-safety filters.

### Autocomplete

Autocomplete should suggest:

- approved taxonomy/narrative labels;
- monitored video/thread titles;
- configured query terms;
- recent searches belonging to the current user;
- optional high-frequency normalized terms only after minimum-count and safety checks.

Do **not** autocomplete author identifiers or expose rare raw phrases that could reveal a person or harmful content. Use prefix matching and, if enabled, `pg_trgm` similarity for safe suggestion fields. Debounce browser requests around 250 ms, require 2 characters, return at most 8 suggestions, and cancel stale requests.

### Search behavior

- Plain words imply AND.
- Quoted text requests a phrase.
- `OR` combines alternatives.
- A leading `-` excludes a term.
- Empty query returns the current filtered collection, not every raw row without limits.
- Search snippets highlight matches but remain redacted/escaped and behind content warnings.
- Results use cursor pagination and stable secondary sorting by `(published_at, id)`.

### Explorer table

Columns:

- Content preview (redacted by default)
- Published time
- Source and video/thread
- Stance
- Severity
- Hate type(s)
- Narrative
- Confidence
- Review state
- Actions: inspect/review/open permitted source

Filters: date, platform/source, approved community/channel/subreddit, source query/video/thread, sampling stratum, language, relevance, stance, severity, hate type, narrative, confidence band, model version and review state. Functions: sortable time/confidence/severity columns, column visibility, saved filter view if time permits, clear filters, aggregate CSV/report export and item detail drawer. Do not include a public author column.

## 10. Minimal FastAPI surface

### Hackathon endpoints

| Method and path | Purpose | Minimum response |
|---|---|---|
| `GET /healthz` | Netlify/Render smoke test | `{ "status": "ok" }` |
| `GET /v1/overview?from=&to=&source=` | KPI cards and overview charts | window, coverage, totals, rates, daily series, severity and narrative summaries |
| `GET /v1/items?...` | Filtered drill-down list | redacted items, prediction/review state, cursor |
| `GET /v1/items/{id}` | Review/detail drawer | content/context, source metadata, predictions, evidence/provenance, review history |
| `POST /v1/reviews` | Confirm/reject/correct a prediction | appended review event and effective label |
| `POST /v1/admin/runs` | Start a bounded source/query run | run ID and accepted status |
| `GET /v1/admin/runs/{id}` | Show progress/coverage/errors | stage counts, timestamps, safe error codes |
| `GET /v1/signals` | Spike/event and narrative signal cards | magnitude, baseline, time, support count, event candidates |
| `GET /v1/forecasts?metric=&horizon_days=&...` | Deterministic short-horizon forecast | point/range, direction, model/version, coverage, backtest metrics, abstention reason |
| `POST /v1/analysis/spikes/{signal_id}` | Generate or retrieve a bounded spike investigation | observed facts, ranked event candidates, alternatives, citations, review state |
| `GET /v1/communities?source=&status=` | Approved monitored communities and reviewable candidates | source-scoped container, rationale, coverage, status; no member identities |
| `POST /v1/admin/community-candidates/{id}/decision` | Approve/dismiss/request context | append-only analyst decision and optional registry change |
| `GET /v1/search?q=&...` | Full-text Explorer results | redacted rows, applied filters, cursor, result estimate |
| `GET /v1/search/suggestions?q=` | Safe autocomplete | taxonomy/query/title suggestions with type |
| `GET /v1/insights?from=&to=&...` | Cached grounded trend brief | summary sections, fact citations, generation metadata |
| `POST /v1/assistant/query` | Ask Amanah analytics question | answer, internal citations, tool calls used, limitations |
| `POST /v1/reports` | Create immutable report snapshot from validated filters | report ID, filter/coverage hash, status, redaction mode |
| `GET /v1/reports/{id}` | View report and provenance | sections, charts/tables, citations, methodology/version, safe export links |
| `GET /v1/reports/{id}/summary.csv` | Download aggregate/filter-scoped data | authorized CSV; no raw content or author identifiers by default |
| `GET /v1/connections` | Cached integration health | service, configured state, last success/check, safe status |

### Example overview response

```json
{
  "window": {"from": "2026-08-09", "to": "2026-08-16", "timezone": "UTC"},
  "coverage": {
    "sources": ["youtube"],
    "videos_monitored": 22,
    "comments_collected": 1483,
    "last_successful_run": "2026-08-16T13:00:00Z",
    "warnings": []
  },
  "kpis": {
    "observed": 1483,
    "relevant": 312,
    "likely_hate": 74,
    "hate_rate_among_relevant": 0.237,
    "reviewed": 31,
    "confirmed_hate": 22
  },
  "daily": [
    {"date": "2026-08-15", "observed": 214, "relevant": 51, "likely_hate": 13, "hate_rate": 0.255}
  ],
  "severity": [
    {"label": "derogation", "count": 34},
    {"label": "collective_blame", "count": 21}
  ],
  "narratives": [
    {"label": "collective blame / security threat", "count": 19, "change_pct": 72}
  ]
}
```

All rate responses include numerator, denominator, date window, filter state, and collection coverage. Use cursor pagination for items, never page-number pagination on changing source data.

## 11. Database subset for the 48-hour build

Keep only these tables initially:

```text
source_query(
  id, source, name, query_text, seed_ids, config_json,
  version, enabled, created_at
)

community_registry(
  id, source, source_community_id, name, canonical_url,
  category, language, region_scope, inclusion_rationale,
  sampling_stratum, approval_status, approved_by,
  active_from, active_until, policy_snapshot_json, last_reviewed_at
)

community_candidate(
  id, source, source_community_id, name, discovery_run_id,
  reason, aggregate_features_json, status, decided_by, decided_at
)

collection_run(
  id, source_query_id, status, started_at, completed_at,
  discovered_count, collected_count, candidate_count,
  classified_count, error_count, safe_error
)

content_item(
  id, source, source_item_type, source_item_id, thread_id,
  parent_source_id, published_at, observed_at, language,
  text_raw, text_normalized, context_json, engagement_json,
  source_query_id, community_registry_id, collection_run_id, normalization_version,
  canonical_url, search_vector, deleted_at, created_at
)

prediction(
  id, content_item_id, model_name, model_version,
  relevance_label, relevance_confidence, stance, hate_confidence,
  type_labels, severity, narrative, rationale,
  requires_review, model_input_hash, created_at
)

review_event(
  id, prediction_id, reviewer_id, decision,
  corrected_stance, corrected_types, note, created_at
)

news_query(
  id, provider, query_text, window_start, window_end,
  config_json, requested_at, status
)

news_event(
  id, provider, provider_item_id, news_query_id, title, url,
  source_domain, scope, location_names, published_at, observed_at, language,
  description, content_hash, metadata_json, created_at
)

event_association(
  id, signal_id, news_event_id, temporal_score,
  semantic_score, corroboration_score, concentration_penalty,
  total_score, rationale, review_status, created_at
)

forecast_snapshot(
  id, metric, filter_hash, generated_at, horizon_start, horizon_end,
  point_estimate, lower_bound, upper_bound, direction,
  model_version, training_window_json, coverage_json,
  backtest_metrics_json, actual_outcome_json
)

insight_snapshot(
  id, filter_hash, window_start, window_end,
  model_name, prompt_version, input_facts_json,
  summary_json, citation_ids, generated_at, expires_at
)

analysis_run(
  id, analysis_type, user_id, filter_hash, window_start, window_end,
  model_name, prompt_version, input_fact_ids, tool_audit_json,
  output_json, citation_ids, validation_status, created_at
)

assistant_message(
  id, session_id, user_id, role, text,
  citation_ids, tool_audit_json, created_at
)

report_snapshot(
  id, requested_by, filter_hash, filters_json, coverage_json,
  sections_json, redaction_mode, methodology_version,
  citation_ids, status, object_key, generated_at, expires_at
)
```

Add unique constraints on `(source, source_item_id)`, `(content_item_id, model_name, model_version)`, and `(source, source_community_id)` for active registry records. `review_event` and community decisions are append-only. Report snapshots are immutable after `ready`; regeneration creates a new ID. For a demo-sized dataset, calculate overview aggregates in SQL/API; do not build materialized metric tables unless queries become slow.

## 12. Dashboard information architecture

Use six research tabs. Overview, Explorer and Insights are the strongest demo sequence. Meme Signals may use prepared examples; Review can be simple. Connections and Settings sit behind a utility/profile menu so the main navigation remains focused.

### 12.1 Overview

**Question answered:** What is happening now, and can I trust the sample?

Top coverage bar:

- Monitoring window
- Active source: YouTube
- Videos monitored
- Comments collected
- Last successful run
- Any coverage warning

KPI row:

- **Observed comments** — all successfully collected items
- **Muslim-related comments** — relevance-stage positives
- **Likely anti-Muslim** — model-only count, visibly labeled
- **Likely hate rate** — likely hate / Muslim-related
- **Reviewed/confirmed** — human-review status, not mixed into model count
- **Change vs 7-day baseline** — absolute and percentage change

Charts:

1. **Daily likely anti-Muslim rate** — line chart; x-axis date, y-axis percentage; show relevant-item denominator in tooltip; annotate spike dates.
2. **Daily volume** — stacked columns for non-relevant, relevant non-hateful and likely hate; never place count and rate on an unlabeled dual axis.
3. **Hate type distribution** — horizontal bars for the six types; show count and share.
4. **Top narratives** — ranked horizontal bars with change vs prior window and review-status badge.
5. **Latest signals** — compact list: magnitude, supporting items, associated news candidate and “temporal association only.”
6. **Experimental outlook** — next one to three days: up/down/stable/insufficient, prediction range, model version and coverage warning. Keep it visually secondary to observed metrics.
7. **Community/channel comparison** — optional horizontal bars for approved source-scoped containers with numerator, denominator and coverage. Title it “Monitored sample comparison,” never “worst communities.”

Interactions: global date range; platform, community/channel and query/video filters; click any chart element or “View supporting records” to open Explorer with the exact filters encoded in the URL; “Run collection” visible only to admin; “Show model-only” toggle. The browser Back button restores the prior chart/filter state.

Place **Ask Amanah** behind a clearly labeled button that opens a right-side panel. It can receive the active date/filter context, but must not obscure the overview or make an automatic claim before the user asks.

### 12.2 Explorer

**Question answered:** Which records support these metrics, and can I find a particular phrase or pattern?

Layout:

- Full-width search input with safe autocomplete.
- Filter bar beneath it with active-filter chips and reset.
- Result count/estimate, current coverage disclosure and sort control.
- Filterable table defined in Section 9A.
- Detail/review drawer opened from a row.

Selecting a chart segment anywhere else in the app navigates to Explorer with the corresponding filters encoded in the URL.

### 12.3 Insights

**Question answered:** What changed, what evidence supports that conclusion, and what should an analyst inspect next?

The Insights tab combines two Gemini-powered features:

1. **Generated trend brief:** one cached, structured summary for the selected period and filters.
2. **Ask Amanah:** an analyst chatbot that answers questions by calling safe data tools.

Trend brief sections:

- What changed
- Experimental outlook: deterministic forecast, range and uncertainty
- Dominant narratives and severity
- Source/coverage qualification
- Temporally associated local and global news candidates, visibly separated
- Items requiring human review
- Limitations

Every quantitative sentence cites a metric/query result ID. Every example cites an authorized content item ID. The UI shows generated time, Gemini model identifier, prompt version, input window/filters, and a “Machine-generated analysis” badge. Analysts can regenerate only when the cache expires or filters change.

Do not use vector RAG as the first implementation for numerical trend analysis. Numbers should come from deterministic SQL/API tools. Add embeddings only for semantic retrieval of representative items or methodology documents. The assistant receives tool outputs, not a raw database dump.

Allowed assistant tools:

- `get_coverage(from, to, filters)`
- `get_observed_metrics(from, to, filters)`
- `compare_periods(metric, current_window, comparison_window, filters)`
- `get_trend_series(metric, interval, filters)`
- `get_forecast(metric, horizon_days<=7, filters)`
- `get_top_narratives(from, to, filters)`
- `search_content(query, filters, limit<=20)`
- `get_signal(signal_id)`
- `search_news_events(query, from, to, provider, limit<=20)`
- `get_news_event(news_event_id)`
- `get_review_stats(from, to, filters)`
- `get_methodology(section)`

Disallowed: arbitrary SQL, unrestricted raw exports, author/profile searches, claims about causation, legal conclusions and automated enforcement actions.

### 12.4 Trends and history

**Question answered:** Is the rate or volume changing over time?

Controls: date window, daily/hourly interval, collection query/video, severity, narrative, review state.

Charts:

- **Rate over time:** line plus 7-day rolling median/baseline; count denominator in tooltip.
- **Observed vs relevant volume:** grouped or stacked columns.
- **Severity over time:** small multiples or stacked columns, not a crowded six-line chart.
- **Video comparison:** horizontal bars showing rate and relevant denominator for each monitored video; suppress/rank low-volume videos carefully.

Functionality: click a spike to open signal detail; compare current window with previous equal-length window; show missing collection periods as gaps, never zeros.

For the 48-hour UI, historical trend controls may remain inside Overview rather than occupy a separate top-level tab. If a dedicated Trends route is built later, it becomes a sub-route under Overview/History.

### 12.5 Narratives

**Question answered:** What kinds of anti-Muslim frames are appearing?

For the hackathon, use classifier-assigned taxonomy labels rather than unsupervised clustering.

- Ranked narrative bars: count, share of likely hate, change, reviewed fraction.
- Narrative cards: plain-language definition, representative **redacted** examples, severity mix, videos/sources, first/latest observed.
- Narrative timeline for the selected label.
- Item list filtered to the selected label.

Avoid word clouds: frequency does not explain stance or narrative, and slurs become gratuitously prominent.

### 12.6 Meme Signals

**Question answered:** How does image-text interaction convey and spread hate?

Use three prepared, access-controlled examples:

- thumbnail blurred by default;
- classification and confidence;
- modal basis: text, image, image-text interaction, or external context;
- OCR text and post context in separate fields;
- concise rationale;
- exact/near-duplicate count only if actually implemented;
- model-only/reviewed badge.

Do not claim automated cross-platform propagation unless pHash/embedding grouping and multiple observations really run. A compelling honest demo can say “multimodal assessment prototype.”

#### How image/meme classification works

The classification target is not “is this image hateful?” An ordinary photo can become hateful only when combined with overlay text or a post caption. The input bundle is:

```text
image pixels
 + OCR text inside image
 + post caption/title
 + bounded thread/source context
 + classification rubric
 → multimodal model
 → structured label + rationale + uncertainty
```

For the hackathon, use the Gemini image API as the multimodal model. Gemini supports image classification without training a specialized model. Send images through FastAPI with `GEMINI_API_KEY` held server-side and request structured JSON containing relevance, hate/stance, type, severity, modal basis, rationale and `requires_review`. Validate the response and preserve a manual-review path.

Do not call a general VLM score “trained Islamophobia detection.” It is a prompted prototype until evaluated on a domain-specific, human-labelled holdout set.

#### How to evaluate without training

Create a small frozen evaluation set of 30–60 licensed/approved memes:

- roughly balanced likely-hateful and non-hateful examples;
- ordinary Muslim imagery and affirming content;
- counterspeech and quoted hate;
- political/theological criticism that does not attack Muslims as people;
- benign confounders where text or image alone gives the wrong answer;
- overt and coded examples;
- no near-duplicates across prompt examples and evaluation set.

Have two humans label `muslim_relevant`, `stance`, `type`, `severity` and `modal_basis`; adjudicate disagreements. Report confusion matrix, macro F1, hateful recall and especially false-positive rate on benign Muslim content. Do not tune the prompt repeatedly against the final holdout.

#### Post-hackathon training path

The Islamophobia-specific [MIMIC repository](https://github.com/faiyazabdullah/MIMIC) publishes images, labels, notebooks and ViLT weights for the accompanying [MIMIC paper](https://arxiv.org/abs/2412.00681). The paper describes 953 memes: 408 hateful and 545 non-hateful. The repository does not visibly present a standard license in its root listing, so obtain/confirm permission before redistribution or production use.

Possible model paths:

- **ViLT baseline:** fine-tune a classification head on image + OCR text, following MIMIC. The generic [`dandelin/vilt-b32-mlm`](https://huggingface.co/dandelin/vilt-b32-mlm) checkpoint is pre-trained, not a ready hate classifier.
- **Open VLM adaptation:** fine-tune/LoRA a vision-language instruction model such as Qwen-VL, after checking the exact checkpoint’s license and compute requirements.
- **SigLIP 2:** use [`google/siglip2-base-patch16-224`](https://huggingface.co/google/siglip2-base-patch16-224) for image embeddings, relevance/near-duplicate candidates or as an encoder—not as a trustworthy out-of-box hate classifier.
- **General hateful-meme research:** Meta’s Hateful Memes benchmark provides valuable benign confounders but has restricted access and handling/sharing terms and is not Islamophobia-specific.

Before splitting a training dataset, group exact/near-duplicate memes with SHA-256, pHash and optionally image embeddings, then assign whole families to train/validation/test. Otherwise the model can memorize templates and produce misleading evaluation scores. Keep a separate Project Amanah dataset card and never train on newly collected Reddit/User Content unless rights and source terms explicitly permit it.

### 12.7 Review

**Question answered:** Which model decisions need a human?

Queue filters: high severity, low confidence, model disagreement, spike member, meme, unreviewed.

Each review item includes content warning, focal content, bounded context, source and observed time, model label/confidence, types, narrative, rationale, and link to original where permitted. Actions: **Confirm**, **Incorrect**, **Needs context**, **Skip**. Optional corrections: stance, type and narrative.

After action, append a review event; do not overwrite the prediction. Provide keyboard shortcuts only if they are discoverable and do not encourage unsafe speed.

### 12.8 Reports

**Question answered:** How can an analyst share what this monitored sample shows without losing context?

The report builder opens from Overview/Insights and inherits active filters. Required filters: date range and at least one source/query/community scope. Optional filters: narrative, severity, review state, language and sampling stratum.

Preview sections:

1. Title, generated time, analyst and immutable report ID.
2. Scope statement listing platforms, approved communities/channels, queries, date window and excluded strata.
3. Coverage and denominators, including collection failures and whether results are live, controlled or fixture-backed.
4. Selected KPI/trend/narrative charts with accessible summaries and drill-down citation IDs.
5. Reviewed local/global event associations using non-causal language.
6. Redacted evidence references; no author identities and no harmful content revealed by default.
7. Methodology, model/dataset/tool/license disclosure, known limitations and correction contact.

MVP outputs:

- print-optimized HTML that the browser can save as PDF;
- aggregate CSV for the charts/tables represented in the report.

Later outputs may include a server-rendered PDF and controlled evidence bundle. Create a `report_snapshot` before download so later data/model changes cannot silently alter the report. Item-level export requires elevated permission, an explicit redaction selection and an audit event.

### Secondary pages

- **Sources & Coverage:** configured queries/seed IDs, last run, collected/skipped/errors and API limitation notes.
- **Communities:** active source-scoped registry plus a human-reviewed candidate queue. Display selection rationale and coverage, not member lists.
- **Methodology:** taxonomy, definitions, model/dataset versions, sampling statement, caveats, privacy and contact.
- **Connections:** operational state for YouTube, Supabase, Gemini, GDELT and disabled/conditional Reddit, Bluesky, X, Threads, Meta, TikTok and Mastodon adapters.
- **Settings:** appearance, timezone/date defaults, content-safety preferences and account controls.

For 48 hours these can be one combined page linked from the footer/header rather than top-level tabs.

## 12A. Gemini implementation

Store `GEMINI_API_KEY` only on Render. Google’s current guidance says API keys should not be exposed in client-side production code and recommends a backend proxy. Use the official Gemini API with a server-configured model name rather than hard-coding a model throughout the application.

For the hackathon, Gemini receives only aggregate facts, taxonomy labels, methodology text and synthetic/redacted/explicitly authorized snippets. It must not receive raw real hateful content, OCR, personal data or unredacted evidence unless an explicit transfer authorization has been recorded. `ALLOW_THIRD_PARTY_CONTENT_INFERENCE=false` remains the default; the API rejects disallowed input before a Gemini request is constructed.

Use [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) so the trend brief conforms to a validated schema. Structured JSON guarantees shape, not truth; validate every citation and recompute every numeric claim from the supplied fact bundle. Gemini [embeddings](https://ai.google.dev/gemini-api/docs/embeddings) are optional for later semantic retrieval.

Recommended summary schema:

```json
{
  "headline": "Short evidence-led headline",
  "what_changed": [
    {"claim": "Likely-hate rate increased...", "citation_ids": ["metric:..."]}
  ],
  "narratives": [
    {"label": "collective blame", "summary": "...", "citation_ids": ["metric:...", "item:..."]}
  ],
  "coverage_note": "Based on ... monitored videos and ... collected comments.",
  "event_associations": [
    {"summary": "Reporting about ... occurred in the same period.", "citation_ids": ["signal:...", "news:..."]}
  ],
  "review_priorities": ["..."],
  "limitations": ["..."]
}
```

Generation flow:

```text
selected filters
 → deterministic metrics and top items
 → redacted fact bundle with immutable IDs
 → Gemini structured summary
 → Pydantic validation
 → verify every citation exists and every number matches input facts
 → cache by filter_hash + data_version + model + prompt_version
 → render with links back to Explorer
```

Assistant answers use the same data tools. Apply authentication, per-user rate limits, maximum date range/result count, short conversation retention and cost logging. Treat retrieved comments as untrusted prompt content and instruct the model never to follow directions inside them.

### 12A.1 Forecasting boundary

The LLM must not calculate a forecast from prose or eyeball a chart. A versioned deterministic service calculates the forecast first; Gemini explains the returned result.

For the hackathon, forecast two series separately:

- `likely_hate_count`: workload/volume, strongly affected by collection volume;
- `hate_rate_among_relevant`: likely-hate numerator divided by relevant denominator, always shown with both counts.

Use a simple seasonal-naive or exponentially weighted baseline with recent residuals for a prediction interval. Prefer a one- to three-day horizon. Require a configurable minimum such as 14 complete daily buckets and adequate recent collection coverage; otherwise return `insufficient_data`. Store model version, training window, point estimate, lower/upper bound, direction, missing-bucket count, and rolling-origin backtest metrics such as MAE, direction accuracy and interval coverage.

The UI and agent must label the result **experimental**, display the range rather than only a point, and distinguish:

- **Observed:** directly computed from collected content;
- **Predicted:** model output for a future period;
- **Hypothesized association:** a possible explanation supported by temporal/semantic evidence;
- **Unknown:** evidence or coverage is insufficient.

An event association is never described as a cause. Project Amanah's observational, query-bounded sample cannot establish that a news event caused online hate to rise or fall.

### 12A.2 Analytical-agent workflows

Implement one orchestrator with safe function calls, not a collection of autonomous agents. Gemini function calling selects from allowlisted tools; FastAPI validates authorization and arguments, executes each tool, and validates the final structured response.

1. **Coverage gate:** resolve the user's date range, timezone and filters; call `get_coverage` before any interpretation. Abstain or narrow the claim if collection failed, the denominator is too small, or periods are not comparable.
2. **Daily situation brief:** summarize observed volume/rate, changes from the previous equal-length window, top narratives, review backlog, new signals and data-quality warnings.
3. **Spike investigation:** retrieve the signal facts, derive narrative/search terms, query GDELT and optionally NewsAPI in a bounded pre/post window, rank candidates, list alternative explanations, and create a reviewable evidence pack.
4. **Forecast commentary:** retrieve a stored deterministic forecast, explain direction/range and uncertainty, identify only observed correlates, and avoid turning event candidates into causal claims.
5. **Narrative-shift watch:** compare taxonomy labels and semantic clusters across windows; surface emerging terms for human review. Never update the relevance lexicon or taxonomy automatically.
6. **Cross-source comparison:** compare normalized rates only when at least two adapters have sufficient and reasonably comparable coverage. State source-specific sampling differences and avoid claims about population prevalence.
7. **Review prioritization:** rank items by severity, uncertainty, model disagreement, novelty and signal membership. The agent may recommend an inspection order but cannot confirm labels or take enforcement action.
8. **Data-quality guardian:** detect missing runs, sudden collector-volume changes, quota failures, language shifts and model-version discontinuities before producing insight text.
9. **Forecast retrospective:** once the horizon ends, attach actual observations to `forecast_snapshot`, compute errors, and show whether earlier commentary was borne out. Never silently replace the original forecast.
10. **Evidence-backed Q&A:** answer a bounded analyst question using fact IDs, content IDs and news IDs; link every factual or numerical claim to the relevant dashboard record.

### 12A.3 Spike-to-event ranking

Event candidates are ranked using transparent features:

```text
association score =
  temporal proximity
  semantic similarity to the changed narrative
  independent-source corroboration
  optional explicitly available geographic relevance
- single-domain/provider concentration penalty
```

The score ranks what an analyst should inspect; it is not a probability of causation. Preserve the exact query, provider, result set and scoring components. Allow `approved`, `rejected`, `needs_context` and `no_clear_association` review states. A strong output includes counter-hypotheses such as a collection-volume change, one unusually active video/thread, classifier drift, coordinated behavior not yet established, or an unrelated contemporaneous event.

### 12A.4 Structured forecast-analysis response

```json
{
  "analysis_type": "forecast",
  "as_of": "2026-08-16T14:00:00Z",
  "metric": "hate_rate_among_relevant",
  "horizon_days": 3,
  "direction": "up",
  "point_estimate": 0.24,
  "interval": {"lower": 0.18, "upper": 0.31},
  "forecast_model": "seasonal_naive_v1",
  "confidence": "low",
  "observed_context": [
    {"claim": "The observed rate increased in the latest complete window.", "citation_ids": ["metric:..."]}
  ],
  "possible_associations": [
    {"claim": "Reporting about ... coincided with the change.", "citation_ids": ["signal:...", "news:..."]}
  ],
  "alternative_explanations": ["Collection volume changed ..."],
  "coverage_note": "Based on ...; ... buckets were incomplete.",
  "causality_note": "No causal claim is made.",
  "limitations": []
}
```

Reject an answer if a citation ID does not exist, a numeric claim differs from the tool result, `direction` conflicts with the forecast, coverage language is absent, causal wording is used, or the model attempts an unapproved tool/action.

### 12A.5 Agent security and audit rules

- Treat comments, OCR, article snippets and search results as untrusted data, never instructions.
- Do not provide arbitrary SQL, arbitrary URLs, shell/network access, author lookups, identity resolution, publishing, messaging or enforcement tools.
- Enforce tool-specific roles, date/result caps, call-count/time budgets and parameter schemas in FastAPI.
- Store each tool name, validated arguments, result fact IDs, model/prompt version, output schema status and user ID in `analysis_run`; do not log raw secrets or unnecessarily duplicate harmful content.
- Cache routine briefs after ETL. Keep interactive Ask Amanah read-only and require the analyst to trigger it.
- Use a fixed system instruction and server-owned tool definitions. Source text cannot modify either.
- Run regression fixtures for citation validity, numeric fidelity, causal-language refusal, insufficient-coverage abstention, prompt injection and unauthorized-tool requests.

## 12B. Repeated-activity signals—not “offender tracking”

Do not create a public “repeat offenders” feature. A model can be wrong, source handles can be impersonated or changed, and person-level dossiers create significant ethical, safety and platform-policy risk.

If the research need is approved later, implement a reviewer-only **Repeated Activity Signal**:

- Derive a stable, source-scoped pseudonym using HMAC of the platform’s opaque author ID. Never join identities across platforms.
- Count `human_confirmed` items separately from `model_only` items.
- Require a minimum such as 3 confirmed items across at least 2 distinct threads in a defined time window before surfacing a signal.
- Show content pattern, narrative mix, time range and evidence links—not a moral or legal label.
- Never infer the person’s religion, location, demographics or real identity.
- Exclude deleted/expired items and support deletion propagation.
- Restrict to authorized reviewers, audit every access and prohibit bulk export/ranking.
- Review source API terms and research/ethics approval before enabling it.

Omit this feature from the hackathon. The supplied participant briefing excludes profiling and targeted surveillance; even a source-scoped activity prototype could distract from that boundary. Reconsider only after formal policy/ethics review and source authorization. Sample coverage, search, human review, community-level patterns and grounded Insights provide the needed value without person-level tracking.

## 12C. Connections and Settings

### Connections

Show one compact status row/card per service:

- Service name and purpose
- `Connected`, `Degraded`, `Not configured`, `Access required`, `Institutional approval required`, `Fixture only` or `Disabled`
- Last successful request/run
- Last safe health check
- Quota/limit warning when available
- Admin-only “Test connection” and configuration link

Never return or display secrets, full connection strings or provider error bodies. Health checks are cached and rate-limited; do not call every external API on each page load. For Gemini, report configured/model name/last success without echoing the key.

### Settings

- Appearance: light, dark or system
- Timezone and default date range
- Content safety: blur media, redact slurs, collapse harmful text
- Table density and default visible columns
- Accessibility: reduced motion/high contrast preferences where needed
- Account: name, role, session and log out

Admin-only source queries, model thresholds and retention policy belong under Connections/Admin, not personal Settings.

## 12D. Feature priority and cut line

### P0 — must ship

- Public marketing page
- Invite-only login/logout and protected routes
- Overview with coverage, KPIs and historical trend
- Explorer with full-text search, autocomplete, filters, table and detail drawer
- Human review append action
- Sources/Methodology disclosure

### P1 — ship after P0 is stable

- Cached Gemini trend brief with verified citations
- One cached GDELT event investigation with explicit non-causal language
- Experimental deterministic one- to three-day outlook with range or `insufficient_data`
- Narrative ranking/timeline using fixed taxonomy labels
- Three prepared Meme Signals examples
- Print-optimized report snapshot and aggregate CSV from current filters
- Secret-free Connections status
- Light/dark/system and content-safety preferences

### P2 — cut first if time slips

- Interactive Ask Amanah chat; retain the static/cached brief
- Live multi-provider news retrieval; retain the cached GDELT evidence pack
- On-demand agent spike investigations and forecast retrospectives
- Community Discovery Queue using fixture/aggregate source-level candidates
- Saved searches/views
- Advanced connection tests and quota display
- Near-duplicate meme propagation
- Any live source beyond YouTube

### Post-hackathon only

- Reviewer-only repeated-activity signals after policy/ethics approval
- Arbitrary semantic RAG over large raw-content collections
- Alerts/notifications, raw/item-level bulk exports and organization administration
- Live Reddit/X/Threads/TikTok/Meta/Mastodon connectors unless official access and governance are approved
- Automated narrative clustering and multilingual expansion

The most defensible additional feature, after search and review, is **Coverage & Methodology**. It tells judges what the charts actually represent and prevents the interface from overstating platform-wide prevalence. Saved views and CSV aggregate export are useful later, but less important than a coherent, reproducible demo.

## 13. Dashboard style specification

Apply the main brand system with an analytical, restrained interface:

- Ivory page background, white content surfaces, navy text/navigation, teal actions/data, sparing gold for emerging signals.
- Red only for reviewed severe harm or destructive actions; ordinary Muslim relevance is teal/neutral.
- Inter for UI, Source Serif 4 only for editorial insight summaries, IBM Plex Mono for IDs/timestamps.
- Flat surfaces, subtle borders, no gradients, heavy shadows, glowing alerts, or gamified counters.
- Content max width around 1440 px; 12-column desktop grid; responsive one-column summaries on mobile.
- KPI numbers use tabular numerals and always include label, definition/tooltip, time window and comparison.
- Hateful text and meme imagery are collapsed/blurred by default with a session-level “redact slurs/hide media” preference.
- Charts use direct labels where possible, accessible tooltips, keyboard-focusable data points, and text summaries.

Status vocabulary:

- `Model only`
- `Needs review`
- `Human confirmed`
- `Human rejected`
- `Insufficient context`
- `Collection incomplete`

## 14. Filters and drill-down behavior

Global filters persist in the URL so a view can be shared among authorized users:

```text
?from=2026-08-09&to=2026-08-16
&source=youtube
&community=approved-channel-cohort
&query=yt-broad-muslim-context-en-ca
&stance=anti_muslim_hate
&severity=2,3
&review_state=model_only
```

Filters: date, platform/source, approved community/channel/subreddit, query, sampling stratum, video/thread, language, relevance, stance, type, severity, narrative, confidence band and review state. Every chart click applies filters rather than navigating to an unrelated page. A visible filter summary and “Reset” are mandatory.

Item lists use cursor pagination, sortable published/observed time, and content previews with redaction. The selected item opens in a side drawer on desktop and a dedicated route on mobile/direct link.

## 15. Metric definitions

| Metric | Exact definition | Warning |
|---|---|---|
| Observed | Successfully stored content items matching current source/type filters | Not all content on a platform |
| Relevant | Items whose relevance label is Muslim-related above the release threshold | Model/lexicon-derived; includes non-hateful content |
| Likely anti-Muslim | Relevant items whose stance is anti-Muslim hate above threshold | Machine classification until reviewed |
| Likely hate rate | Likely anti-Muslim / relevant | Never divide by all platform content without saying so |
| Confirmed hate | Items with latest effective human decision = confirm | Reviewer-dependent; smaller subset |
| Review precision | Confirmed / (confirmed + rejected) among reviewed model positives | Not overall model precision if review sample is prioritized |
| Spike magnitude | Current rate/count vs documented rolling baseline | Sensitive to coverage and small denominators |
| Narrative share | Likely-hate items with narrative / all likely-hate items in window | Multi-label totals can exceed 100% |
| Coverage score | Expected monitored queries/videos/runs successfully collected | Operational coverage, not population representativeness |

Always display numerator and denominator in tooltips/details. If relevant items are below a configured minimum, show “insufficient volume” instead of a volatile rate.

## 16. Chart rules

Use:

- line charts for rates over time;
- columns for volumes over time;
- horizontal bars for ranked categories/videos/narratives;
- stacked columns for composition when categories are mutually exclusive;
- event markers for spike/news associations;
- compact tables/lists for reviewable evidence.

Avoid:

- pie/donut charts when precise comparison matters;
- word clouds;
- geographic maps without reliable, consent-compatible location data;
- 3D charts;
- dual-axis charts unless both axes are unmistakably labeled and genuinely necessary;
- smoothed curves that imply unobserved values;
- zero-filled gaps when collection failed.

## 17. Minimum functional demo script

1. Open the marketing page and explain the name: Amanah is a shared trust to care for one another and resist normalization of harm with evidence, wisdom and justice.
2. On Overview, point to the coverage bar: “22 videos and 1,483 comments in this monitored sample.”
3. Explain the denominator: 312 Muslim-related items, 74 classified likely anti-Muslim; relevance is separate from hate.
4. Click the trend spike to open Explorer with the date/narrative filters already applied.
5. Search a phrase with autocomplete and filter the table by severity and review state; open one supporting record.
6. Open Insights and show a cached Gemini brief whose claims link back to metrics and Explorer records.
7. Ask Amanah one bounded question such as “Which narratives increased most this week?” and show its citations and coverage note.
8. Open Meme Signals and reveal one prepared image-text interaction example.
9. Open Review, reject or confirm one prediction, then show the immutable model output and appended reviewer decision.
10. Open Reports, preserve the active platform/date/narrative filters, and preview the scoped aggregate report/CSV disclaimer.
11. Open Connections briefly to show YouTube/Supabase/Gemini as live or fixture-backed and X/Meta/TikTok as access-gated—without exposing secrets.
12. Finish on Methodology: show how responsible-use safeguards make the product worthy of its name—sample boundaries, AI tools/datasets/licenses, third-party-transfer rule, model-only disclaimer, and what was deliberately not built. Close with “Carry the trust with care.”

## 18. 48-hour implementation order

### Hours 0–5: shell, auth and fixture

- Create public marketing and protected app route groups.
- Configure invite-only Supabase Auth and verify logout/route protection.
- Create the core Supabase tables, full-text search index and RLS.
- Seed a coherent redacted fixture through the same insert code path used by collectors.

### Hours 5–14: source, model and API

- Build one YouTube seed-video collector and one query-discovery function.
- Implement normalization v1 with tests.
- Add relevance rule/model and local classification, or structured hosted classification only for synthetic/redacted/explicitly authorized inputs.
- Validate output; store prediction and failure state.
- Implement overview, search/suggestions, item detail and manual run endpoints.

### Hours 14–25: Overview and Explorer

- Build shared shell, global filters and coverage bar.
- Complete Overview/history charts and taxonomy narrative summary.
- Build autocomplete, filterable Explorer table, item drawer and content warnings.
- Add chart-to-Explorer drill-down with platform/community/date/narrative filters preserved.
- Deploy early to Netlify/Render and resolve CORS/auth.

### Hours 25–33: grounded Insights

- Implement deterministic insight fact bundle and one cached Gemini structured summary.
- Add the simple versioned forecast service; store its range/backtest metadata and test the insufficient-data state.
- Validate citation IDs and numeric claims before saving/display.
- Add Ask Amanah with only the approved data tools and a strict result cap.
- Add rate limiting, visible generation metadata and a fixture response fallback.

### Hours 33–40: review, meme, event and connections

- Implement review append action.
- Add three prepared meme records/results.
- Add one cached GDELT query/result associated with a spike.
- Rank event candidates transparently and show counter-hypotheses plus “no clear association.”
- Build minimal Connections status plus combined Sources/Methodology page.
- If P0 is stable, add print-report preview and aggregate CSV from the same validated filters.

### Hours 40–48: hardening and rehearsal

- Stop adding sources/features.
- Verify API failure, empty, loading, missing-coverage and fixture-fallback states.
- Check denominators, labels, timestamps, redaction, mobile, keyboard and secrets.
- Verify real harmful/personal content cannot cross the third-party inference boundary when authorization is absent.
- Rehearse twice; record backup screenshots/video.

## 19. Acceptance checklist

- The public story explains why the project is called Amanah and translates faith-rooted care into justice, restraint, dignity and human accountability.
- Faith language cannot reasonably be read as endorsing coercion, vigilantism, identity policing, religious judgment or person-level surveillance.
- A keyword query discovers YouTube videos without requiring links.
- YouTube broad relevance, event and high-risk/fixture strata remain distinguishable in metrics.
- A seed YouTube URL/ID works when search is unavailable.
- Subreddits/communities require an approved registry entry before monitoring; discovery candidates do not activate themselves.
- Every comment is tied to video, query, run and observed time.
- Every collector maps source fields into the same validated canonical `ContentItem` contract before ML or dashboard use.
- Missing, zero, deleted and unavailable source values remain semantically distinct.
- Engagement fields are source-specific snapshots rather than a misleading cross-platform score.
- Re-running a collector does not duplicate source items or predictions.
- Raw, normalized and model-input representations are distinguishable and versioned.
- Neutral Muslim discussion and counterspeech appear as explicit non-hate classes.
- Dashboard counts reconcile with database queries.
- Every rate shows its denominator and every gap distinguishes missing collection from zero.
- Browser contains no server secrets.
- Public marketing routes work without authentication; dashboard/search/AI/review routes do not.
- Full-text search, autocomplete, filters and cursor pagination reconcile with authorized database rows.
- Gemini summaries and Ask Amanah answers cite existing metrics/items and display coverage limitations.
- Forecast commentary matches a stored deterministic forecast and displays range/model/coverage; too little history yields `insufficient_data`.
- News/event language is explicitly non-causal, preserves the provider query, and supports `no clear association`.
- Prompt-injection text in comments, OCR or news snippets cannot alter the allowlisted agent tools.
- Real harmful/personal content is rejected before a hosted-model call unless explicit transfer authorization is recorded.
- Review appends a decision without deleting the model output.
- A report snapshot preserves platform/community/date filters, coverage, methodology, redaction state and aggregate CSV provenance.
- Connections reports safe configured/health state without returning keys or raw provider errors.
- X/Meta/TikTok unavailable states say `Access required`/`Institutional approval required`; no scraping fallback is attempted.
- Prepared data is labeled prepared/cached; no live feature is implied when it is not live.
- The demo works with YouTube/external-inference/GDELT temporarily unavailable.
