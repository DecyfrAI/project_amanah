"""Every mapped table, imported here so `Base.metadata` is complete.

Alembic and the schema tests both read `Base.metadata`, so a model that is not
re-exported here is invisible to both. Importing the package is what registers
the tables.
"""

from amanah.db.base import Base
from amanah.db.models.analysis import Prediction, ReviewEvent, ReviewTask
from amanah.db.models.community import (
    ClassificationDispute,
    ContentSubmission,
    ContributionEvent,
    UserProfile,
)
from amanah.db.models.content import CollectionRun, ContentItem
from amanah.db.models.datasets import DatasetImportRun, DatasetPackage
from amanah.db.models.jobs import BackgroundJob
from amanah.db.models.metrics import InsightSnapshot, MetricBucket, NewsEventLink
from amanah.db.models.reporting import PlatformPolicy, PolicyMatch, PreparedPlatformReport
from amanah.db.models.resources import (
    ResearchReport,
    ResearchReportAuditEvent,
    ResourceAuditEvent,
    ResourceEntry,
)
from amanah.db.models.sources import Source, SourceSeedEntry

__all__ = [
    "BackgroundJob",
    "Base",
    "ClassificationDispute",
    "CollectionRun",
    "ContentItem",
    "ContentSubmission",
    "ContributionEvent",
    "DatasetImportRun",
    "DatasetPackage",
    "InsightSnapshot",
    "MetricBucket",
    "NewsEventLink",
    "PlatformPolicy",
    "PolicyMatch",
    "Prediction",
    "PreparedPlatformReport",
    "ResearchReport",
    "ResearchReportAuditEvent",
    "ResourceAuditEvent",
    "ResourceEntry",
    "ReviewEvent",
    "ReviewTask",
    "Source",
    "SourceSeedEntry",
    "UserProfile",
]
