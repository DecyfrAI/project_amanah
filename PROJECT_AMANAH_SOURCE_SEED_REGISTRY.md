# Project Amanah — Initial Reddit and YouTube Seed Registry

**Verified:** August 22, 2026  
**Purpose:** A small, purposive source set for testing retrieval and classification—not a claim that every listed community, creator, video or commenter is hateful.

## Use this registry carefully

These sources were selected because they contain public discussion about Islam, Muslims, immigration, mosques, sharia, extremism or related political narratives. Inclusion means **relevant for sampling**, not “hateful.” The system must classify individual comments in context and retain criticism, counterspeech, reporting, quotation and theological disagreement as distinct non-hate or uncertain classes.

Do not use this sample to estimate the prevalence of anti-Muslim hate across Reddit or YouTube. It is a deliberately enriched convenience sample for a hackathon demonstration.

## Recommended 48-hour shortlist

Start with:

- Reddit: `r/ReformUK`, `r/QuebecLibre`, `r/ukpolitics`, `r/europe_sub` and `r/PoliticalCompassMemes`.
- YouTube: the two Tommy Robinson-related seeds, the Ben Shapiro seed, the Douglas Murray discussion and one counterspeech/control video.
- Cap collection at 100–300 comments per submission/video and store the sampling mode.
- Use synthetic/redacted records if Reddit approval or YouTube comments are unavailable.

## Reddit source candidates

### Higher-relevance candidates

1. **[r/ReformUK](https://www.reddit.com/r/ReformUK/)**  
   UK party/community discussion where Islam, integration, immigration, public prayer, sharia and British-values threads recur. Search only matching submissions; do not characterize the whole community as hateful.

2. **[r/ukpolitics](https://www.reddit.com/r/ukpolitics/)**  
   Broad UK political discussion. Useful for mainstream comparison and event-linked threads concerning Muslims, Islamophobia, immigration, grooming-gang reporting, mosques and Reform UK.

3. **[r/europe_sub](https://www.reddit.com/r/europe_sub/)**  
   Europe-focused discussion with recurring immigration and Islam threads. Treat it as a candidate requiring manual review before activation.

4. **[r/QuebecLibre](https://www.reddit.com/r/QuebecLibre/)**  
   French-language Québec political discussion. Relevant recurring topics include secularism/*laïcité*, Bill 21/*loi 21*, hijab/niqab restrictions, mosques, immigration, integration and Islam in Québec. Preserve the original French text, language tag and accents; do not translate before the primary classifier. An [example thread explicitly debates whether coexistence with Muslims in Québec is possible](https://www.reddit.com/r/QuebecLibre/comments/1lgw5vx/lislam_ne_peut_pas_respecter_la_loi_21_une/), making this a useful but high-risk context requiring careful separation of religious criticism, Québec secularism arguments and hostility toward Muslims.

5. **[r/PoliticalCompassMemes](https://www.reddit.com/r/PoliticalCompassMemes/)**  
   Relevant to the meme branch because submissions are image-led political satire. OCR and image-plus-text interpretation are required. The subreddit rules prohibit identity-based hate, so collection should evaluate content rather than assume it is harmful.

6. **[r/europe](https://www.reddit.com/r/europe/)**  
   Broad European news and politics. Useful as a mainstream comparison source around immigration, elections, Quran-burning incidents, mosque disputes and public events.

7. **[r/Conservative](https://www.reddit.com/r/Conservative/)**  
   US conservative political discussion. Use only topic-filtered submissions about Islam/Muslims rather than collecting the entire subreddit.

8. **[r/worldnews](https://www.reddit.com/r/worldnews/)**  
   High-volume global-news comparison source. Useful around major events, but sample carefully because Israel–Palestine and terrorism threads can dominate the dataset.

### Hard-negative and boundary sources

9. **[r/exmuslim](https://www.reddit.com/r/exmuslim/)**  
   Essential boundary set containing personal testimony and criticism of Islam. Do not automatically label criticism of religion, accounts of abuse or discussion of leaving a faith as hatred toward Muslims. Expect difficult examples and require human review.

10. **[r/PoliticalDiscussion](https://www.reddit.com/r/PoliticalDiscussion/)**  
   Moderated political debate useful for neutral and analytical comparisons.

Do not collect from Muslim community/support spaces such as `r/islam` or `r/Muslim` for the hackathon without moderator/community partnership. Those communities are not “hate sources,” and `r/islam` explicitly prohibits unauthorized data collection in its rules. If a later partnership is established, use such spaces only for counterspeech, reported experiences and evaluation of false positives.

## Reddit query families

Run queries inside the approved subreddit registry; do not ingest every submission.

### Broad relevance

```text
Islam OR Muslim OR Muslims OR mosque OR masjid OR hijab OR niqab OR Quran OR Qur'an
```

### Political narratives

```text
"sharia law" OR Islamism OR Islamist OR "Muslim immigration" OR "Islamic immigration"
OR "public prayer" OR "Islamic takeover" OR "no-go zone"
```

### UK event/narrative terms

```text
"grooming gangs" OR "Muslim voters" OR "British values" OR Reform
OR "Tommy Robinson" OR "Quran burning" OR mosque
```

Keep query families separate in storage so the dashboard can disclose how each item entered the sample. A matched query establishes relevance only; it is not a hate label.

### Québec/French relevance

```text
islam OR musulman OR musulmans OR musulmane OR musulmanes OR mosquée
OR hijab OR niqab OR burqa OR voile OR charia OR islamisme OR islamiste
OR "loi 21" OR laïcité OR "accommodements raisonnables"
OR immigration OR intégration
```

Run the Québec/French family only in approved French-language sources such as `r/QuebecLibre`. Store `language=fr`, retain Québec-specific spelling/slang and evaluate French separately; an English translation may be stored as an auxiliary reviewer aid but must not replace the source text.

## YouTube seed videos

Before collection, preflight every video with `commentThreads.list`. Videos can be removed, made private or have comments disabled.

### Enriched discussion seeds

1. **Tommy Robinson — “Tommy Robinson Exposes the Islamic Takeover of the UK”**  
   URL: [youtube.com/watch?v=kM6hqIGWgd4](https://www.youtube.com/watch?v=kM6hqIGWgd4)  
   Video ID: `kM6hqIGWgd4`  
   Why: high-engagement interview with explicit chapters on Muslim immigration and influence in Britain.

2. **Tommy Robinson/Didsbury Mosque discussion — “Tommy Robinson Confronts Islamist Imam, Then Gets KICKED OUT of Mosque!”**  
   URL: [youtube.com/watch?v=Z_NV-xahGUk](https://www.youtube.com/watch?v=Z_NV-xahGUk)  
   Video ID: `Z_NV-xahGUk`  
   Why: mosque-specific framing likely to produce comments about Muslims, collective blame, terrorism and religious institutions.

3. **Ben Shapiro — “The Myth of the Tiny Radical Muslim Minority”**  
   URL: [youtube.com/watch?v=6L2Jil03qmI](https://www.youtube.com/watch?v=6L2Jil03qmI)  
   Video ID: `6L2Jil03qmI`  
   Why: explicitly generalizes about Muslim attitudes and is a strong test for distinguishing claims about extremism from hostility toward Muslims collectively.

4. **Douglas Murray — “Israel, Immigration & Islam”**  
   URL: [youtube.com/watch?v=KS1_cAdIQR4](https://www.youtube.com/watch?v=KS1_cAdIQR4)  
   Video ID: `KS1_cAdIQR4`  
   Why: long-form discussion covering multiculturalism, immigration, Islam and the West; useful for narrative and context-window testing.

5. **Piers Morgan debate — “Piers Morgan debates UK leader of Islamic Extremist group Hizb ut-Tahrir”**  
   URL: [youtube.com/watch?v=HzcxF5johQU](https://www.youtube.com/watch?v=HzcxF5johQU)  
   Video ID: `HzcxF5johQU`  
   Why: high-engagement debate tying Islam, Hamas, sharia and Britain together. Expect both anti-Muslim generalization and legitimate criticism/counterspeech.

6. **Piers Morgan Uncensored — “Israel-Palestine War: ‘That's BULLSH*T!’ Piers Morgan Debates Hamas With Islamist Extremist Doctor”**  
   URL: [youtube.com/watch?v=QtcEAGG_tnU](https://www.youtube.com/watch?v=QtcEAGG_tnU)  
   Video ID: `QtcEAGG_tnU`  
   Why: another high-volume debate/control source; classify comments about Hamas or a named ideology separately from comments targeting Muslims generally.

7. **Nigel Farage — “Nigel Farage Responds to Criticism Over Anti-Muslim Claims”**  
   URL: [youtube.com/watch?v=V4ewyFlokbU](https://www.youtube.com/watch?v=V4ewyFlokbU)  
   Video ID: `V4ewyFlokbU`  
   Why: direct discussion of claims about young Muslims and British values, with a high-engagement comment section likely to contain both political disagreement and generalized claims about Muslims.

### Boundary and comparison seeds

8. **Matt Walsh — “Listen To This Atheist's Thoughts On Christianity And Islam”**  
   URL: [youtube.com/watch?v=yALBrWnUVT8](https://www.youtube.com/watch?v=yALBrWnUVT8)  
   Video ID: `yALBrWnUVT8`  
   Why: a comparison source involving Islam but not selected on the assumption that its comments are hateful. Useful for checking source-bias and false positives.

9. **Jordan Peterson — “Discourse with Moderate Muslims”**  
   URL: [youtube.com/watch?v=D7_vx9pk-EA](https://www.youtube.com/watch?v=D7_vx9pk-EA)  
   Video ID: `D7_vx9pk-EA`  
   Why: discussion framed around moderate Muslims and reform; useful for distinguishing debate, paternalistic framing and direct anti-Muslim hostility.

10. **Muslim Skeptic response — “Ben Shapiro Almost Got Away with This (Radicalism in Islam vs. Judaism)”**  
   URL: [youtube.com/watch?v=P5v-3BMRvHI](https://www.youtube.com/watch?v=P5v-3BMRvHI)  
   Video ID: `P5v-3BMRvHI`  
   Why: counterspeech/control source responding to Shapiro. Including it prevents the sample from containing only hostile or critical framing.

## YouTube discovery queries

Use seed URLs for the reliable demo and these queries for bounded discovery:

```text
Tommy Robinson Islam Muslims mosque
Ben Shapiro Islam Muslims radical
Matt Walsh Islam Muslims Christianity
Douglas Murray Islam immigration
Nigel Farage Islam Muslims UK
Muslim immigration Europe
Islamic takeover UK
sharia law Britain
Quran burning Europe
mosque protest UK
```

For each query, request `type=video`, retain the query string and cap results. Use both a recent stratum (`order=date`, bounded `publishedAfter`) and a high-engagement stratum (`order=viewCount`), then deduplicate video IDs.

## Collection recipe

### YouTube

1. Parse each seed URL to `video_id`, or discover video IDs with `search.list`.
2. Retrieve metadata with `videos.list`.
3. Call `commentThreads.list(part=snippet,replies, videoId=..., maxResults=100, textFormat=plainText)`.
4. If a thread reports more replies than were embedded, retrieve the remainder with `comments.list(parentId=...)`.
5. Store video ID, channel ID, video title, comment/reply ID, parent ID, published/updated time, like count snapshot, query/seed provenance and collection time.
6. Never equate the creator's statements with commenters' statements; classify each content object separately.

### Reddit

1. Use only the official approved API/PRAW connection.
2. Search submissions within the approved subreddit registry.
3. Retrieve each matched submission and its comment tree, preserving parent relationships.
4. Store subreddit, submission ID, comment ID, parent ID, timestamps, matched query family and collection run.
5. Do not expose usernames in the dashboard; pseudonymize source-scoped author identifiers if retention is authorized.
6. Respect removals/deletions and implement expiry.

## Access and policy warning

As of this verification date, Reddit's Responsible Builder Policy says explicit approval is required before accessing Reddit data through its API. Reddit's Data API Terms also restrict using user content to train ML/AI models without permission. A PRAW client ID and secret therefore do **not** by themselves authorize this project. Use prepared fixtures unless approval covering the intended research/classification use is confirmed.

YouTube's official API can discover videos with `search.list` and retrieve public comment threads for a `videoId` with `commentThreads.list`; a thread may omit some replies, which must be retrieved with `comments.list`. Disabled comments return an error and should be recorded as a coverage gap rather than zero comments.

## Review rules

- Label individual content, not creators, channels or subreddits.
- Separate criticism of Islam, Islamism, governments, organizations and named conduct from hostility toward Muslims as people.
- Do not infer a commenter's religion, nationality or offline identity.
- Hide raw harmful text and author identifiers by default.
- Store denominators: videos/submissions checked, comments available, comments sampled and comments classified.
- Keep the public demo synthetic or redacted.
