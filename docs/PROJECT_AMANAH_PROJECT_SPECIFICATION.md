# Project Amanah — Comprehensive Project Specification

**Version:** 1.3 — 48-hour hackathon scope  
**Tagline:** Monitoring Anti-Muslim Hate Online  
**Status:** Build-ready product and technical specification

> **Open-datapack addendum (2026-08-22):** Project Amanah also ingests reviewed Kaggle and other open datapacks through the canonical pipeline. Their public platform/source value is `N/A`; dataset provider, package, version, license, file hash, import run, and row provenance remain separate and mandatory. The root [`spec.md`](../spec.md) is authoritative.

> **Seed-registry addendum (2026-08-22):** [`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md`](../PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md) is a candidate Reddit/YouTube sampling catalog, not executable configuration, automatic approval, a hate label, or a representative prevalence sample. Only reviewed entries projected into versioned runtime configuration may run; see the authoritative root [`spec.md`](../spec.md).

**Companion implementation detail:** [Data, API & Dashboard Blueprint](./PROJECT_AMANAH_DATA_API_DASHBOARD_BLUEPRINT.md)

## 1. Executive summary

Project Amanah is a human-in-the-loop observatory for public anti-Muslim hate online. It collects permitted public content, identifies Muslim/Islam-relevant candidates, classifies likely anti-Muslim hate, extracts severity and narrative, detects changes over time, and lets trained reviewers inspect context and preserve evidence. It measures online patterns; it does not decide legality, automate enforcement, infer anyone’s religion, or prove that news events caused online hate.

Its practical value is longitudinal context. Individual incidents are easy to dismiss, forget or experience as an exhausting stream. Amanah turns a bounded sample into evidence about recurrence, narrative change, spikes, affected public communities, contemporaneous events and review priorities. It helps researchers and community organizations decide what merits closer inspection, create scoped reports and learn from reviewer corrections without requiring staff to repeatedly search for harmful material.

The product answers:

1. **How much is happening?** Rates, counts, coverage, and trends.
2. **What kind is happening?** Animosity, derogation, dehumanization, threats, exclusion, and evolving narratives.
3. **What changed around it?** Spikes and contemporaneous news/events, expressed as correlation only.
4. **What can a responsible analyst do next?** Drill into supporting records, review uncertainty, and export a redacted, filter-scoped report.

## 2. Problem and principles

Generic moderation models often miss coded language, context, multimodal jokes, and changing dog whistles. Keyword counts overcount criticism, counterspeech, news reporting, and neutral discussion. Platform-native moderation does not give civil-society researchers a cross-source, longitudinal, auditable view.

Repeated exposure also creates a human cost. Community members may become fatigued or numb after years of encountering hate, while isolated screenshots rarely establish a durable pattern. The design should preserve concern without sensationalizing abuse: hide harmful content by default, foreground trends and context, and let people inspect only the minimum evidence their task requires.

### Faith-rooted purpose and ethical boundary

The name **Amanah** is not decorative. *Amānah* means a trust, responsibility or something placed in one’s care. Project Amanah begins from the conviction that people are entrusted with one another’s wellbeing and should not become indifferent when their community is harmed. Its story draws on three connected Islamic principles:

- trusts must be carried and judgments made with justice ([Qur’an 4:58](https://quran.com/4/58));
- communities should call toward what is good and resist what is wrong ([Qur’an 3:104](https://quran.com/3/104)); and
- believing men and women share responsibility for one another and for encouraging good ([Qur’an 9:71](https://quran.com/9/71)).

For this product, that trust becomes concrete obligations: classify fairly, preserve context, admit uncertainty, collect with restraint, protect dignity, care for reviewers and make findings useful for education, advocacy, research and responsible platform engagement.

**Ghayrah**—also transliterated *gheerah*—is used here as disciplined protective concern for the deen and community: the refusal to normalize or become numb to harm. It is governed by truth, mercy, wisdom and justice. It must never be presented as rage, possessiveness, coercion, vigilantism or permission to police individuals.

“Enjoining good and forbidding wrong” therefore describes responsible witness and response: making patterns visible, preserving reviewable evidence, supporting correction and helping communities act wisely. It does not authorize automated punishment, religious judgment or surveillance of people. Public-facing religious language should be reviewed after the hackathon by a trusted scholar and community advisor; the product is not a religious authority.

Design principles:

- Make the product itself worthy of trust through justice, accuracy, restraint, dignity and human accountability.
- Separate **relevance** from **hate** so Muslim vocabulary is not treated as harmful.
- Preserve original context and model provenance.
- Prefer calibrated abstention and human review over confident guessing.
- Publish rates with denominators and source coverage.
- Treat model rationales as aids, not proof.
- Minimize retained personal data and exposure to harmful content.
- Monitor sources and communities, not identities; candidate-community discovery always requires human approval.
- Capture the smallest harmful unit that supports the finding plus enough context to interpret it.

## 3. Goals, non-goals, and success measures

### Goals

- Ingest authorized public content from at least one live source end to end.
- Classify Muslim relevance, anti-Muslim stance/hate, and severity/type.
- Analyze text and memes using image, embedded text, and post context.
- Surface narratives, spikes, cross-platform meme families, and event associations.
- Support reviewer correction with audit history and evidence integrity.
- Provide reproducible dataset/model evaluation and transparent limitations.
- Maintain a documented registry of monitored subreddits, channels, queries and other public communities.
- Produce filter-scoped, redacted reports for briefings, research and platform engagement.
- Turn the idea of *amanah* into visible product behavior: careful evidence handling, mutual care, principled resistance to harm and refusal to sensationalize it.

### Non-goals

- Automated takedowns, law-enforcement referrals, or legal conclusions
- User profiling, religion inference, face recognition, or geolocation inference
- Private-message collection, access-control circumvention, or unrestricted scraping
- Automatically branding a subreddit, channel or community as hateful, or autonomously expanding surveillance scope
- Generating counter-speech automatically in the MVP
- Claiming population prevalence from a convenience sample
- Acting as a religious authority or using faith language to justify coercion, vigilantism, identity policing or person-level surveillance

### MVP acceptance measures

- One production source (YouTube) runs idempotently on schedule.
- At least 95% of ingested rows retain source ID, timestamps, collection run, and model version.
- Evaluation reports macro F1, per-class precision/recall, calibration, confusion matrix, and slices for counterspeech/quotation/sarcasm.
- Reviewer can confirm/reject/abstain and see surrounding context.
- Every dashboard rate names its denominator and collection coverage.
- Every chart can drill into the authorized records supporting that filtered aggregate.
- A report export preserves filters, coverage, methodology, citations and redaction state.
- Deletion/expiry workflow and audit logging are tested.

No accuracy target should be promised before a representative, independently reviewed holdout set exists.

## 4. Users and permissions

- **Research analyst:** explores trends, narratives, and evidence.
- **Reviewer:** adjudicates queued content and records rationale.
- **Administrator:** manages sources, lexicon versions, roles, retention, and model releases.
- **Public visitor (optional):** sees only aggregated, redacted, disclosure-safe findings.

Roles follow least privilege. Raw content and author identifiers are never available to public visitors.

## 5. System architecture

```text
YouTube   Bluesky   Reddit*   X*   Threads*   TikTok*   Mastodon*   News/RSS/GDELT
    │        │        │      │       │          │          │              │
    └────────┴────────┴──────┴──── Source/provider adapters ┴──────────────┘
                              │
              approved source/community/query registry
                              │
                    raw intake + provenance
                              │
              Normalize · language · dedupe · media hash
                              │
                 Candidate filter (versioned lexicon)
                    │                         │
                 text item                image/meme
                    │                         │
        relevance → hate/type       OCR + visual relevance
                    │                         │
                    └──── multimodal fusion ──┘
                              │
            calibrated result · rationale · abstention
                              │
        embeddings → narratives → time buckets → spike detector
                              │                  │
                              ├──── local/global news association
                              ├──── community discovery candidates
                              └──── report snapshots
                                              │
             Supabase Postgres + pgvector + private object storage
                              │
                  FastAPI service + review audit log
                              │
                     React/Vite dashboard

* Conditional on approved official API/research access, terms, cost and compliant retention. No scraping fallback.
```

Adapters emit the same canonical `ContentItem`; downstream stages never depend on a source-specific payload.

## 6. Ingestion sources

### Source decision for the hackathon

- **Live P0:** YouTube only, against approved/controlled content, with a synthetic/redacted fixture fallback.
- **Best next adapter:** Bluesky bounded post search; public AppView endpoints are comparatively accessible.
- **Conditional:** Reddit, X, Threads and Mastodon only when official credentials/access already work.
- **Application-gated, not a 48-hour dependency:** TikTok Research API and Meta Content Library/API.
- **Context rather than monitored hate content:** GDELT plus curated local/national/global RSS or NewsAPI.

“Easily scraped” is not an implementation category. Project Amanah uses documented official APIs, approved research environments or explicitly permitted feeds. When access is unavailable, the connection is disabled and the demo uses disclosed fixtures.

### YouTube — MVP source

Use [`search.list`](https://developers.google.com/youtube/v3/docs/search/list) to discover video IDs with query, publication window, region/language, ordering and `type=video`. YouTube supports `|` for OR and `-` for exclusion. Enrich IDs with `videos.list`, then use [`commentThreads.list`](https://developers.google.com/youtube/v3/docs/commentThreads/list) for top-level threads and `comments.list` when included replies are incomplete. Comments can be disabled or deleted; record these as coverage states, not zero activity.

Maintain three separately labelled query strata:

1. **Broad relevance discovery:** neutral topic terms such as `Muslim|Islam`, `mosque|hijab`, and approved local-language equivalents.
2. **Event discovery:** a reviewed event/place term combined with Muslim-relevance terms, refreshed as news changes.
3. **Seed coverage:** approved video/channel IDs that make the demo reproducible.

Do not search only for slurs or overtly hateful phrases and then present the result as prevalence; that would preselect hate. If a high-risk discovery query is used to find evaluation examples, store it as `oversampled_high_risk` and exclude it from ordinary rate comparisons.

### Reddit / PRAW — conditional adapter

Use [PRAW](https://praw.readthedocs.io/) only after obtaining valid OAuth/API access. Reddit requires OAuth and compliance with its [Data API guidance](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki), [Developer Terms](https://redditinc.com/policies/developer-terms), and [Data API Terms](https://redditinc.com/policies/data-api-terms). Store minimal identifiers and excerpts, support deletion/expiry, and do not make the demo depend on approval. No HTML scraping fallback.

The administrator must define an approved subreddit registry. Begin with a balanced, documented set of public topical, local-news and general-discussion communities—not only places presumed hostile. Record inclusion rationale, region/topic, query set, approval owner, start/end date and review date. Search submissions in the registry, then collect bounded comment trees from matching submissions; do not promise global comment-body search.

A separate discovery job may search submissions through `r/all` and aggregate which subreddits repeatedly contain relevant matching posts. It creates **community candidates**, not active monitors or “hate community” labels. A human approves, dismisses or requests context before the registry changes.

### Bluesky

For bounded backfills/search, use AT Protocol app-view endpoints. For live public events, use the official [firehose/Jetstream guidance](https://docs.bsky.app/docs/advanced-guides/firehose); Jetstream provides JSON and collection filtering. Filter `app.bsky.feed.post`, checkpoint event time/cursor, reconnect with backoff, and treat edits/deletes as state changes. A full-network stream can be high volume: apply candidate filtration promptly and monitor sampling.

### X — access- and cost-sensitive

The official [X search API](https://docs.x.com/x-api/posts/search/introduction) supports keyword/operator queries, a seven-day recent search and a paid/Enterprise full archive. It requires an approved developer project/app and keys/tokens. Build only a disabled adapter contract or fixture unless access, pricing, quotas and permitted research use are confirmed. Do not scrape the website.

### Threads and Instagram/Facebook

Meta’s current official Threads workspace exposes keyword search with `TOP` or `RECENT` and a `threads_keyword_search` permission. Treat [Threads keyword search](https://www.postman.com/meta/threads/request/m9j4i2x/search-for-threads-posts) as a plausible post-hackathon adapter, contingent on a Meta app, token, permission review and verified rate limits.

The [Instagram API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) is oriented around professional accounts, their media/comments/mentions and hashtagged media; it is not a general public-comment firehose. Broader public Facebook/Instagram research belongs in [Meta Content Library and API](https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/), for which qualified academic or nonprofit researchers apply through ICPSR. Neither path should be promised for the 48-hour build.

### TikTok comments

TikTok’s [Research Tools](https://developers.tiktok.com/docs/en/about-research-api) can provide public video and comment data to approved independent/academic nonprofit researchers. The [video-comment endpoint](https://developers.tiktok.com/doc/research-api-specs-query-video-comments) accepts a `video_id` and returns bounded comments/replies with the required research scope. This is viable only after approval and credentials; seed TikTok URLs alone do not grant API access. Use a disabled adapter/fixture in the hackathon and do not scrape TikTok.

### Mastodon — optional federated source

Mastodon offers documented public/authorized APIs, but search is instance-specific. Its [search API](https://docs.joinmastodon.org/methods/search/) always supports accounts/hashtags while full-text status availability depends on the server’s search configuration and authentication. An adapter must name monitored instances and disclose that it does not represent the whole fediverse. This can be easier to prototype than X/Meta/TikTok, but it is lower-value than finishing YouTube and Bluesky.

### Web/news

Use a curated allowlist of RSS feeds and pages whose terms permit collection. Respect robots directives, rate limits, copyrights, and paywalls. Prefer headline, timestamp, canonical URL, publisher, and short permitted excerpt over full article storage. General web content is primarily contextual evidence, not a training corpus.

Maintain two news scopes:

- **Local:** city/province/state and national sources relevant to the monitored communities, including local incidents, policy debates and community responses.
- **Global:** major international stories likely to shape discourse across platforms.

Every event candidate carries `scope=local|national|global`, explicit locations only when supplied, and the exact discovery query. Locality is configured; never infer a user’s location from content.

### GDELT

Use the [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) to discover contemporaneous reporting and the [GDELT 2.0 event data](https://www.gdeltproject.org/data.html) for structured event candidates. Cache query, time window, result URL/title, language, and retrieval time. GDELT volume is not proof of event importance or causality.

### Community registry and discovery rules

Normalize “community” as a source-scoped container: subreddit, YouTube channel/video cohort, Bluesky feed/list or Mastodon instance/hashtag. Store source, opaque ID, display name, URL, inclusion rationale, query set, sampling stratum, approval status/owner, active window, terms snapshot and last review. Discovery uses aggregate source-level signals only; it never joins identities across platforms or builds dossiers about members.

Candidate ranking may consider repeated relevance matches, distinct threads, growth versus that candidate’s own baseline and narrative novelty. Require minimum sample sizes and human approval. The UI says “Suggested for analyst review,” not “hateful community.”

## 7. Normalization and candidate filtration

Canonical normalization preserves both `text_raw` and a derived `text_normalized`. Perform Unicode normalization; safe URL/user placeholders; whitespace cleanup; language detection; quote/repost markers; emoji retention; and source-aware context assembly. Do not stem away identity terms or destroy punctuation needed for threats/sarcasm.

Deduplicate by `(source, source_content_id)`. Compute normalized-text SHA-256 and SimHash/MinHash for repeated text. For media, compute SHA-256 plus pHash/dHash; never treat perceptual similarity as identity without a threshold and review.

Maintain `config/lexicon.yml` with version, owner, rationale, locale, category, terms/patterns, expiry/review date, and tests. Categories include Muslim targets, religious practice, institutions, geopolitical terms, slurs, stereotypes, exclusion/deportation, demographic threat, violence, and emerging coded language.

A text becomes a candidate when a high-precision target pattern matches, a source/query is already Muslim-contextual, or a low-cost semantic relevance score crosses threshold. An image becomes a candidate when caption/context matches, OCR matches, or a visual relevance model detects relevant objects/context. **Relevance never equals hate.** Log filter version and matched rule IDs; never expose sensitive lexicon internals publicly if that enables evasion.

## 8. Text analysis pipeline

Use staged classification:

1. **Relevance:** `muslim_related`, `not_related`, `uncertain`.
2. **Stance/hate:** `anti_muslim_hate`, `non_hateful_discussion`, `counterspeech_or_quotation`, `uncertain`.
3. **Type/severity (multi-label):** animosity, derogation, dehumanization, exclusion/segregation, threat/incitement; severity 0–3.
4. **Narrative tags:** e.g. demographic replacement, collective blame/terrorism, incompatibility, criminality, cultural contamination.

Baseline: fine-tune or evaluate [HateXplain’s BERT checkpoint](https://huggingface.co/Hate-speech-CNERG/bert-base-uncased-hatexplain) and [HateXplain dataset/code](https://github.com/hate-alert/HateXplain). It supplies hate/offensive/normal labels, target annotations, and human rationales, but is general-purpose and sourced from Twitter/Gab; it is not an Islamophobia detector.

Recommended progression:

- Baseline: TF-IDF/logistic regression and HateXplain checkpoint.
- Domain model: compact encoder fine-tuned on licensed, balanced anti-Muslim data.
- Optional adjudicator: constrained structured-output LLM for uncertain cases; do not accept it as ground truth.
- General safety comparison: OpenAI’s current [Moderations endpoint](https://developers.openai.com/api/reference/resources/moderations) accepts text and image, but its general categories do not replace a domain taxonomy or validation.

**Hackathon data boundary:** use synthetic, redacted or controlled examples. Do not upload real hateful content or personal data to Gemini, OpenAI or another third-party AI service without explicit authorization covering that transfer. When authorization is absent, run local inference on permitted content, send only aggregate/redacted fact bundles to the LLM, or use disclosed precomputed fixture outputs. The default `ALLOW_THIRD_PARTY_CONTENT_INFERENCE` setting is `false`.

Training must include hard negatives: ordinary Muslim speech, neutral reporting, academic/religious criticism, quoted hate, counterspeech, reclaimed language, and ambiguous geopolitical discussion. Split by source/time/author or meme family to reduce leakage. Calibrate probabilities on held-out data; use thresholds per class and an abstention zone. Store model ID, dataset manifest, commit, prompt/config hash, threshold set, and inference timestamp.

## 9. Meme multimodal pipeline

Never classify OCR alone. Meme meaning can arise only from the interaction of image and text—a central motivation for Meta’s [Hateful Memes dataset](https://ai.meta.com/blog/hateful-memes-challenge-and-data-set/), which includes benign confounders.

```text
image → validate/normalize → SHA-256 + pHash → OCR ─┐
caption + parent context ────────────────────────────┼→ fusion classifier
visual relevance + image embedding ─────────────────┘       │
                                      structured result + review
```

Output includes relevance, hate label, types, severity, confidence/calibration band, `modal_basis` (`text`, `image`, `image_text_combination`, `external_context`), concise evidence rationale, OCR text/confidence, and review requirement.

Candidate cascade:

- Cheap OCR and visual embedding/relevance pass first.
- Domain multimodal model for candidates.
- Optional stronger VLM adjudication only in the uncertain band or on disagreement.
- Human review for threats, low confidence, model disagreement, novel narratives, or publication-bound evidence.

The same hackathon data boundary applies to images and OCR. Prepared memes must be licensed/approved, synthetic or properly redacted. A hosted VLM may receive only material whose transfer is explicitly authorized; otherwise use a local model or disclosed precomputed result.

Use pHash distance plus image embeddings (for example [SigLIP 2](https://huggingface.co/google/siglip2-base-patch16-224)) to propose meme families. Confirm propagation using timestamps and source IDs; do not infer who originated a meme from the earliest item in a partial collection.

## 10. Datasets and model registry

| Resource | Intended use | Key caveats |
|---|---|---|
| [MIMIC paper](https://arxiv.org/abs/2412.00681) / [code-data repository](https://github.com/faiyazabdullah/MIMIC) | Islamophobia-specific meme baseline | 953 curated memes (408 hateful, 545 non-hateful); small, English-centric, binary, platform-curated; verify repository license/availability before redistribution; prevent near-duplicate leakage. |
| [Meta Hateful Memes](https://ai.meta.com/blog/hateful-memes-challenge-and-data-set/) | General multimodal pretraining/evaluation and benign confounders | Not Islamophobia-specific; restricted access/handling and sharing terms; synthetic reconstruction may differ from organic memes. |
| [HateXplain](https://github.com/hate-alert/HateXplain) / [checkpoint](https://huggingface.co/Hate-speech-CNERG/bert-base-uncased-hatexplain) | General hate baseline, targets, rationale experiments | Twitter/Gab domain, broad targets, annotation disagreement and bias; model card/license must be rechecked before deployment. |
| [DynaHate paper](https://arxiv.org/abs/2012.15761) / [Dynabench tasks](https://github.com/bvidgen/Dynamically-Generated-Hate-Speech-Dataset) | Hard positive/adversarial examples | Roughly 40k general hate examples; Muslim-targeted slice can be positive-heavy. Do not construct “Muslim term = hate” labels; confirm license and exact release schema. |
| [CONAN repository](https://github.com/marcoguerini/CONAN) | Islamophobia hate/counter-narrative pairs; hard negatives | Expert-written, not natural prevalence data; research-use/redistribution terms must be checked; counter-narratives contain quoted hateful language. |
| [English Islamophobia tweet study](https://doi.org/10.1007/s10579-020-09539-5) | Three-way relevance/islamophobia framing | Reported 9,612 tweets (2,930 Islamophobic, 4,336 about Islam but non-Islamophobic, 2,346 neither); tweet availability and IDs may decay; English/Twitter-era sampling; verify access/license and reconcile reported counts across derivative papers. |
| [Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | Optional local multimodal adjudicator | Compute-heavy; generative confidence is not calibrated; prompt injection via image text; verify license and benchmark on local data. |
| [ViLT](https://huggingface.co/dandelin/vilt-b32-mlm) | Reproducible MIMIC-style fusion baseline | Older architecture; OCR quality and small domain dataset constrain performance. |

Dataset governance requirements: record license snapshot, source URL, retrieval date, allowed uses, redistribution limits, consent/annotation context, languages, label definition, known demographic/source skews, hashes, transformations, and deletion obligations in a dataset card. Never commit restricted content to a public repository.

The previously inspected DynaHate files contained 40,623 records and 1,129 unique Muslim/Muslim-woman-targeted examples, all labeled hate in that target slice. Treat these counts as local-file observations that must be reproduced in a data audit, not universal properties of every DynaHate release.

## 11. Human review

Queue priority combines severity, uncertainty, model disagreement, spike membership, novelty, and publication need—not author influence. Reviewer sees content warning, item/context, source link, OCR/image, predictions, rationale, rule matches, similar items, and model/version.

Allowed decisions: `confirm`, `reject`, `needs_context`, `out_of_scope`, `duplicate`, `escalate_threat`. Reviewer selects corrected labels, notes ambiguity, and may redact personal data. Store immutable decision events rather than overwriting predictions. Two-person review is required for exemplar publication, taxonomy changes, or external threat escalation. Measure inter-annotator agreement and reviewer well-being; rotate queues and allow no-fault breaks.

Reviewer labels enter training only after quality checks, consent/governance approval, and a frozen dataset release—not automatically.

## 12. Narrative clustering

Embed only relevant items using a versioned sentence embedding model. Cluster in bounded time windows using HDBSCAN (unknown cluster count) or agglomerative clustering; combine semantic similarity with entities, lexicon themes, and meme-family signals. Generate a candidate label from representative items, then require human approval. Track cluster lineage (`emerged`, `merged`, `split`, `continued`) rather than assigning permanent meaning to unstable IDs.

Quality checks include coherence, diversity, minimum size, source concentration, duplicated-content share, and reviewer agreement. Display representative, redacted examples and distinguish narrative volume from unique-author count.

## 13. Trend and spike detection

Aggregate by UTC hour/day and source. Primary metric is `likely_hate_items / relevant_items`; also show raw numerator, denominator, unique threads/videos, collection success, and reviewed subset.

MVP detector:

- Compare current value with rolling 7-day median/MAD and same-day-of-week baseline.
- Require minimum volume and source coverage.
- Create a signal when robust z-score and relative/absolute change thresholds pass.
- Suppress duplicate alerts during a cooldown; close after recovery.

Stretch: Bayesian change-point detection, seasonal decomposition, and source-weighted ensembles. Backtest against known periods and simulated missing ingestion. A collector outage must create a coverage warning, not a “drop in hate.”

## 14. Event correlation and short-horizon analysis

For each spike, query [GDELT DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) in a pre/post window using narrative terms and embeddings. [NewsAPI](https://newsapi.org/docs/endpoints) or curated RSS may be optional interchangeable providers. Rank candidate events by temporal proximity, semantic similarity, geographic relevance (only when explicitly available), independent-source corroboration, and coverage volume. Store the exact query, returned metadata and score components. Reviewers approve links.

UI language: “This spike coincided with increased reporting about …” Include alternative events and “no clear association.” Never use causal verbs without a separate causal design.

Forecasting is a separate deterministic task. A versioned seasonal-naive or exponentially weighted baseline produces a one- to three-day point estimate, prediction interval, direction, coverage assessment and rolling backtest metrics. Require enough complete historical buckets; otherwise return `insufficient_data`. Gemini may explain the stored forecast and retrieve possible event associations, but it may not invent the forecast, calculate unsupported probabilities, or turn association into causation.

The analysis agent runs read-only workflows: coverage gate, situation brief, spike investigation, forecast commentary, narrative-shift watch, data-quality checks, review prioritization, forecast retrospective and evidence-backed Q&A. Every numerical claim cites a deterministic fact ID; every event claim cites a stored news candidate; every response separates observed facts, predictions, hypotheses and unknowns. Comments, OCR and article snippets are treated as untrusted prompt data. Tool calls, prompt/model version, input fact IDs, citations and validation status are audited.

## 15. Evidence and reporting workflow

Use a human-governed lifecycle adapted from the meeting’s report-design guidance:

```text
Capture → Classify → Contextualize and route → Human decision → Learn and report
```

- **Capture:** retain the smallest content unit that carries the finding, plus enough parent/thread/source context to explain its meaning; include URL/ID and timestamps.
- **Classify:** record policy/taxonomy reason, content type, confidence, model/version and whether the result is model-only.
- **Contextualize and route:** attach the relevant signal/narrative/community/news context and send it to the appropriate internal review queue. Routing never initiates a takedown or external report automatically.
- **Human decision:** confirm, reject, request context, correct labels or exclude. Publication/export can require a second reviewer.
- **Learn and report:** preserve the original prediction and append reviewer feedback; update evaluation and create a filter-scoped report snapshot.

Create an evidence manifest with source URL/ID, captured/observed/published times, permitted excerpt, surrounding-context IDs, media object key, SHA-256, MIME type, collector version, terms/retention policy, and chain-of-custody events. Store immutable original hash and derivative hashes separately. Timestamp in UTC and retain source timezone when present.

Raw evidence is private, encrypted, access logged, and subject to expiry/deletion. The public dashboard uses aggregates and synthetic/redacted examples. A deleted source item is marked unavailable; retained copies follow source terms and approved research/legal policy. Exports include methodology, scope, provenance, model/human status, and a warning that a hash verifies the stored artifact—not the truth of its claim.

Reports are aggregate-first and filtered by date, source/platform, approved community/channel, query, narrative, severity and review state. A report contains executive summary, selected-filter statement, coverage/denominators, trend charts, narrative findings, reviewed event associations, redacted evidence references, methodology, model/dataset disclosure, limitations and generation metadata. CSV exports contain chart/aggregate data by default; item-level exports require elevated permission, explicit redaction and audit logging. For the hackathon, a print-optimized HTML report plus filtered aggregate CSV is sufficient.

## 16. Core schemas

```text
source(id, kind, name, policy_url, enabled, config, retention_days)
community_registry(id, source_id, source_community_id, name, url, inclusion_rationale,
                   sampling_stratum, approval_status, approved_by, active_from,
                   active_until, policy_snapshot, last_reviewed_at)
community_candidate(id, source_id, source_community_id, name, discovery_run_id,
                    reason, aggregate_features, status, decided_by, decided_at)
collection_run(id, source_id, started_at, ended_at, status, cursor, stats, error)
content_item(id, source_id, content_type, source_content_id, thread_id,
             root_id, parent_source_id, container_id, container_label,
             author_pseudonym, title, published_at, updated_at, observed_at,
             language, text_raw_ciphertext, text_normalized,
             root_title, parent_text_ciphertext, canonical_url_ciphertext,
             like_count, score, reply_count, view_count, repost_count,
             engagement_observed_at, adapter_version,
             canonical_schema_version, source_status, raw_object_key,
             deleted_at, expires_at, metadata)
media_asset(id, content_id, object_key, mime_type, sha256, phash, width, height,
            ocr_text_ciphertext, ocr_confidence, embedding, expires_at)
filter_match(id, content_id, lexicon_version, rule_id, stage, score)
model_release(id, task, model_name, version, artifact_uri, dataset_manifest,
              commit_sha, thresholds, metrics, approved_at)
prediction(id, content_id, media_id, model_release_id, relevance_label,
           hate_label, type_labels, severity, confidence, modal_basis,
           rationale, created_at)
review_task(id, prediction_id, priority, reason, status, assigned_to, due_at)
review_event(id, task_id, reviewer_id, decision, labels, note, created_at)
narrative(id, label, description, status, model_release_id)
narrative_membership(narrative_id, content_id, score, window_start)
metric_bucket(id, source_id, narrative_id, interval, bucket_start,
              observed_count, relevant_count, likely_hate_count, reviewed_hate_count,
              coverage_score)
signal(id, metric_key, opened_at, closed_at, magnitude, baseline, status, detector_version)
news_event(id, provider, external_id, title, url, scope, location_names,
           event_at, language, embedding, metadata)
signal_event_link(signal_id, news_event_id, score, review_status, rationale)
forecast_snapshot(id, metric_key, filter_hash, generated_at, horizon_start, horizon_end,
                  point_estimate, lower_bound, upper_bound, direction, model_version,
                  training_window, coverage, backtest_metrics, actual_outcome)
analysis_run(id, analysis_type, user_id, filter_hash, model_name, prompt_version,
             input_fact_ids, tool_audit, output, citation_ids, validation_status, created_at)
report_snapshot(id, requested_by, filter_hash, filters, coverage, sections,
                redaction_mode, methodology_version, citation_ids, status,
                object_key, generated_at, expires_at)
evidence_manifest(id, content_id, sha256, captured_at, policy_snapshot,
                  custody_log, access_class)
audit_event(id, actor_id, action, entity_type, entity_id, before_hash, after_hash, created_at)
```

Unique constraints: `(source_id, source_content_id)`, prediction idempotency `(content_id, media_id, model_release_id)`, and metric `(metric_key, source_id, bucket_start, interval)`. Partition high-volume content/prediction tables by month when needed. Use `jsonb` only for source-specific metadata, not core query fields.

## 17. Security, privacy, and ethics

- Treat every record, reviewer action and public claim as an *amanah*: handle it justly, disclose uncertainty and protect the dignity of the people represented in the data.
- Collect only public, authorized data; document lawful basis and consult counsel/ethics review for real deployment.
- For the hackathon, default to synthetic/redacted/controlled material and disclose every AI tool, dataset, outside source, license and earlier-work component.
- Do not transmit real hateful content or personal data to third-party AI services without explicit authorization; enforce this in configuration and tests.
- Do not infer protected characteristics, expose author handles, or enable person-level search.
- Pseudonymize author IDs with a rotating keyed hash; separate keys from the database.
- Encrypt transport, database, and object storage; encrypt especially sensitive text/URLs at application level where appropriate.
- Use row-level security, private buckets, least-privilege service roles, secret rotation, MFA for reviewers, rate limits, and immutable audit events.
- Sanitize all content as hostile input: prevent stored XSS, SSRF in media fetches, decompression bombs, malicious file types, and prompt injection from content.
- Fetch media through an allowlisted egress service with size/time limits; strip executable metadata; never render arbitrary HTML.
- Do not log raw hateful text, tokens, API secrets, or signed object URLs.
- Establish retention by source and artifact class; implement deletion propagation and backup expiry.
- Publish model/data cards, false-positive/negative slices, coverage limitations, and change logs.
- Form a community advisory group including Muslim civil-society and subject-matter experts; compensate reviewers and provide trauma-aware controls.
- Red-team political criticism, theological debate, reporting, quotation, satire, counterspeech, multilingual text, and reclaimed terms.

## 18. MVP and stretch scope

### 48-hour hackathon MVP

- YouTube adapter demonstrated against approved/controlled video IDs, manual trigger, and synthetic/redacted fixture fallback
- Versioned lexicon and candidate filter
- Local classifier or hosted structured classifier restricted to explicitly authorized/synthetic/redacted inputs; no fine-tuning during the event
- Supabase schema, private storage, auth/RLS
- FastAPI read/review endpoints
- Dashboard overview, trends, narrative tags, item detail, review queue
- Netlify frontend and Render API
- Public marketing page, invite-only login and protected dashboard routes
- Full-text Explorer with safe autocomplete, filters and redacted content table
- Chart-to-Explorer drill-down preserving source/community/date/narrative filters
- Simple spike plus one cached GDELT/news overlay
- Experimental deterministic short-horizon forecast with range/coverage, or an honest insufficient-data state
- Cached Gemini trend/forecast brief and tightly grounded Ask Amanah prototype with citations
- Three prepared multimodal meme examples, including a benign confounder
- Print-optimized, filter-scoped report plus aggregate CSV export if P0 is stable
- Minimal audit/provenance and honest methodology/limitations page
- Synthetic/redacted offline demonstration corpus when live APIs fail

Do not build live Reddit/Bluesky/X/Meta/TikTok, autonomous community scouting, fine-tuning, automated clustering, distributed queues, or a production evidence export during the 48 hours.

### High-value next

- Meme OCR + multimodal classifier using MIMIC evaluation
- pHash/embedding meme-family propagation
- Bluesky Jetstream adapter
- Human-reviewed community discovery queue and monitored-community registry
- Reviewer-approved embedding clusters
- Production evidence/report bundle export

### Stretch

- Reddit after access approval
- X recent-search adapter after access/cost review
- Threads keyword-search adapter after Meta app/permission review
- TikTok Research API and Meta Content Library integrations after institutional approval
- Instance-scoped Mastodon adapter
- Multilingual/Arabic evaluation and RTL UI
- Active learning with governance gate
- Change-point detection and cross-source lead/lag analysis
- Organization workspaces and public aggregate portal
- Research API with privacy budgets and query controls

## 19. Risks and mitigations

- **False positives against Muslim speech:** two-stage relevance/hate, hard negatives, Muslim-led review, abstention.
- **Sampling bias:** coverage telemetry, denominators, per-source results, no population claims.
- **Dataset leakage:** group/time/source splits, hash/embedding duplicate checks.
- **Platform policy changes:** adapter isolation, policy registry, deletion hooks, demo fixtures.
- **Unavailable/restricted sources:** connection statuses show `not approved` or `not configured`; no scraping fallback and no claim of cross-platform coverage.
- **Community stigmatization:** neutral registry names, aggregate candidate evidence, human approval, no member profiling, and no “hateful community” label.
- **Graphic exposure:** blur/redaction defaults, workload limits, wellness policy.
- **Event overclaim:** reviewer approval and explicit non-causal wording.
- **Model drift/dog whistles:** versioned lexicon, drift monitoring, periodic annotated samples.
- **Abuse of dashboard:** authenticated access, aggregate-only public mode, no individual rankings.

## 20. Definition of done for a credible demo

Begin by explaining why the project is called Amanah: a shared trust to care for one another and resist normalization of harm with truth, wisdom and justice. Run one controlled or synthetic/redacted item through capture, normalization, classification, storage, chart drill-down, human review and audit history; then export a scoped report snapshot. Demonstrate a meme where neither OCR nor image alone is sufficient. Show a spike with coverage telemetry and a reviewer-approved contemporaneous event. Finish with the methodology page: what is collected, what is missed, which integrations are live versus fixtures, which AI tools/datasets/licenses were used, how labels were evaluated, how the system embodies restraint rather than surveillance, and how a person can request correction/deletion.
