"""Controlled vocabulary shared by the API, storage, and ingestion layers.

One term means one thing everywhere. Every value here is part of the public `/v1`
contract, so values may be added in a minor release but never renamed or removed
without a new API major version.
"""

from enum import IntEnum, StrEnum

#: Public display value for records that have no meaningful platform, such as rows
#: imported from a reviewed open datapack. Dataset lineage is preserved separately.
NOT_APPLICABLE_DISPLAY = "N/A"


class SourceKind(StrEnum):
    """How a configured source supplies content."""

    news = "news"
    social = "social"
    user_submission = "user_submission"
    open_datapack = "open_datapack"


class PublicPlatform(StrEnum):
    """Platform shown to authenticated users.

    Open-datapack rows use `not_applicable`; their dataset provider, name, and
    version remain available as separate provenance fields.
    """

    youtube = "youtube"
    reddit = "reddit"
    bluesky = "bluesky"
    news_web = "news_web"
    user_submitted = "user_submitted"
    not_applicable = "not_applicable"


class ContentKind(StrEnum):
    """Shape of a canonical content item."""

    news_article = "news_article"
    social_post = "social_post"
    social_comment = "social_comment"
    dataset_record = "dataset_record"


class SourceStatus(StrEnum):
    """Availability of the item at its original source."""

    available = "available"
    inaccessible = "inaccessible"
    deleted = "deleted"


class Relevance(StrEnum):
    """Stage one of classification: is the item about Muslims or Islam at all?"""

    muslim_related = "muslim_related"
    not_related = "not_related"
    uncertain = "uncertain"


class Stance(StrEnum):
    """Stage two of classification: how the item treats its Muslim-related subject.

    Muslim-related language is never hateful by default; counterspeech and quoted
    hate are distinct from anti-Muslim rhetoric.
    """

    likely_anti_muslim = "likely_anti_muslim"
    non_hateful_discussion = "non_hateful_discussion"
    counterspeech_or_quotation = "counterspeech_or_quotation"
    uncertain = "uncertain"


class HateType(StrEnum):
    """Versioned taxonomy of anti-Muslim hate expressions."""

    animosity = "animosity"
    derogation = "derogation"
    dehumanization = "dehumanization"
    exclusion = "exclusion"
    threat_or_incitement = "threat_or_incitement"
    collective_blame = "collective_blame"
    other = "other"


class Severity(IntEnum):
    """Harm severity band; `none` means no anti-Muslim harm was identified."""

    none = 0
    low = 1
    moderate = 2
    high = 3


class ConfidenceTier(StrEnum):
    """Display tier derived from the versioned numeric model score."""

    low = "low"
    medium = "medium"
    high = "high"


class ReviewState(StrEnum):
    """Human-review state of an item's effective labels."""

    model_only = "model_only"
    pending_review = "pending_review"
    confirmed = "confirmed"
    corrected = "corrected"
    disputed = "disputed"
    needs_context = "needs_context"


class ContributionType(StrEnum):
    """Kinds of records that appear in a user's contribution history."""

    url_submission = "url_submission"
    classification_dispute = "classification_dispute"
    prepared_platform_report = "prepared_platform_report"


class SubmissionStatus(StrEnum):
    """Terminal and in-flight states of a user-submitted URL."""

    processing = "processing"
    analyzed = "analyzed"
    duplicate = "duplicate"
    unsupported = "unsupported"
    inaccessible = "inaccessible"
    rejected = "rejected"
    failed = "failed"


class JobState(StrEnum):
    """Background collection/processing job states."""

    queued = "queued"
    running = "running"
    retry_wait = "retry_wait"
    succeeded = "succeeded"
    failed = "failed"
    policy_blocked = "policy_blocked"
    cancelled = "cancelled"


class JobStage(StrEnum):
    """One checkpointed stage of the canonical collection pipeline.

    A stage writes its output before the next one is enqueued, so a retry re-runs
    one stage against stored input rather than restarting the run.

    `spec.md` section 12.3 draws the pipeline as discover/fetch, canonicalize,
    then normalize and deduplicate. Canonicalization has no stage of its own here
    because it is a pure in-memory translation with no external call: giving it
    one would mean checkpointing a raw provider payload into the job queue
    between the two, which is a payload the product has no reason to persist
    outside the one column documented to hold it. It runs at the end of `fetch`
    instead, so what crosses the boundary is already the canonical shape.
    """

    discover = "discover"
    fetch = "fetch"
    normalize = "normalize"


class NewsScope(StrEnum):
    """Geographic reach of an ingested news article.

    `local` is reporting tied to one of the monitored countries; `global` is
    religion or hate-crime reporting with no single national frame.
    """

    local = "local"
    globally = "global"


class DataMode(StrEnum):
    """Whether a response is backed by live collection, fixtures, or cached fallback."""

    fixture = "fixture"
    live = "live"
    fallback = "fallback"


class Role(StrEnum):
    """Authorization roles for authenticated principals, least privilege first."""

    registered_user = "registered_user"
    reviewer = "reviewer"
    administrator = "administrator"


class ResourceCategory(StrEnum):
    """Curated education-resource sections."""

    understanding_islamophobia = "understanding_islamophobia"
    research_and_data = "research_and_data"
    responding_to_online_hate = "responding_to_online_hate"
    platform_reporting_guidance = "platform_reporting_guidance"
    support_for_affected_people = "support_for_affected_people"
    getting_involved = "getting_involved"
    country_specific = "country_specific"


class ApprovalStatus(StrEnum):
    """Governance state of a reviewed configuration or dataset manifest.

    Nothing collects, imports, or runs while this is anything but `approved`.
    """

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SeedEntryKind(StrEnum):
    """Shape of an approved source-seed entry."""

    search_query = "search_query"
    seed_video = "seed_video"
    channel = "channel"
    subreddit = "subreddit"
    feed = "feed"


class SamplingStratum(StrEnum):
    """Why an entry was sampled.

    Inclusion means sampling relevance, never a hate label, and the enriched
    stratum must never be read as population prevalence.
    """

    enriched = "enriched"
    boundary_control = "boundary_control"
    ordinary_monitoring = "ordinary_monitoring"


class RetentionPolicy(StrEnum):
    """What the source's terms permit us to keep."""

    indefinite_permitted = "indefinite_permitted"
    limited_by_terms = "limited_by_terms"
    delete_on_request = "delete_on_request"


class ConnectorStatus(StrEnum):
    """Safe, publishable state of a configured source connector.

    Deliberately coarse: it never carries a provider error body, a host name, or
    anything that would distinguish a bad key from a network failure.
    """

    ok = "ok"
    degraded = "degraded"
    disabled = "disabled"
    not_configured = "not_configured"
    access_required = "access_required"


class CollectionMode(StrEnum):
    """How a collection run was dispatched."""

    scheduled = "scheduled"
    manual = "manual"
    backfill = "backfill"
    fixture = "fixture"


class InferenceStatus(StrEnum):
    """Typed outcome of one classification attempt."""

    succeeded = "succeeded"
    deferred = "deferred"
    policy_blocked = "policy_blocked"
    invalid_output = "invalid_output"
    provider_failure = "provider_failure"


class ReviewTaskType(StrEnum):
    """Why an item entered the human-review queue."""

    dispute = "dispute"
    low_confidence = "low_confidence"
    severity_escalation = "severity_escalation"
    model_disagreement = "model_disagreement"
    uncertain_relevance = "uncertain_relevance"
    invalid_output = "invalid_output"


class ReviewTaskStatus(StrEnum):
    """Lifecycle of a review task."""

    open = "open"
    claimed = "claimed"
    completed = "completed"
    cancelled = "cancelled"


class ReviewDecision(StrEnum):
    """An appended reviewer decision. Decisions never overwrite a prediction."""

    confirmed = "confirmed"
    corrected = "corrected"
    needs_context = "needs_context"
    rejected = "rejected"


class DisputeStatus(StrEnum):
    """Lifecycle of a user's classification dispute."""

    open = "open"
    in_review = "in_review"
    resolved_upheld = "resolved_upheld"
    resolved_corrected = "resolved_corrected"
    withdrawn = "withdrawn"


class ContributionEventType(StrEnum):
    """User-safe transition recorded on a contribution timeline."""

    created = "created"
    status_changed = "status_changed"
    resolved = "resolved"


class OnboardingStatus(StrEnum):
    """How far the signed-in user has progressed through onboarding."""

    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class MetricInterval(StrEnum):
    """Bucket width of a stored deterministic metric."""

    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"


class RelationBasis(StrEnum):
    """How a news item was associated with a metric movement.

    Association is never causation; the basis is stored so a reader can judge it.
    """

    shared_narrative = "shared_narrative"
    temporal_proximity = "temporal_proximity"
    manual_link = "manual_link"


class RelationReviewState(StrEnum):
    """Whether a human has checked a proposed news/metric association."""

    unreviewed = "unreviewed"
    confirmed = "confirmed"
    rejected = "rejected"


class ValidationStatus(StrEnum):
    """Whether generated narrative output passed citation validation."""

    pending = "pending"
    validated = "validated"
    rejected = "rejected"


class PublicationStatus(StrEnum):
    """Editorial lifecycle of a curated catalog entry.

    Only `published` entries reach an authenticated base-role reader.
    """

    draft = "draft"
    published = "published"
    archived = "archived"


class PreparedReportStatus(StrEnum):
    """State of a report the user prepared for a platform.

    The product never submits a report, so no state here claims platform receipt.
    """

    prepared = "prepared"
    submitted = "submitted"
    closed = "closed"


class PreparedReportOutcome(StrEnum):
    """Outcome the user recorded after reporting to the platform themselves."""

    no_response = "no_response"
    content_removed = "content_removed"
    content_restricted = "content_restricted"
    no_violation = "no_violation"
    other = "other"


class ResearchReportStatus(StrEnum):
    """Lifecycle of a research-report snapshot. `ready` snapshots are immutable."""

    pending = "pending"
    ready = "ready"
    failed = "failed"


class RedactionMode(StrEnum):
    """How much of the underlying evidence a report snapshot may carry."""

    default_redacted = "default_redacted"
    aggregate_only = "aggregate_only"
