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
