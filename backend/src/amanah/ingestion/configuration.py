"""Reviewed, versioned runtime configuration for sources and seeds (B-S8.9).

`PROJECT_AMANAH_SOURCE_SEED_REGISTRY.md` and `docs/news-rss-sources.md` are human
reference documents. Nothing here parses either of them, and nothing activates an
entry because it appears in one. A seed runs only after a person has reviewed it
and copied it into the YAML this module validates, with an approval, a stable
key, and a configuration version attached — which is B-S8.10 and `spec.md`
section 10.3, and is why `registry_key` plus `config_version` is the identity
rather than a heading position in a document.

The configuration is data, not code, and it is treated as untrusted input in the
ordinary way: every field is validated, an unknown field is an error rather than
a silently ignored typo, and an entry whose `approval_status` is anything but
`approved` is loaded but never projected into a runnable state.

`topical_filter` is a *relevance* filter and never a harm signal. Its keep terms
name the subject matter a feed is monitored for — religion, hate crime, public
affairs — and Muslim-related vocabulary appearing there says only that an article
is on topic. Deciding whether something is hateful is a separate, later, staged
classification.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from amanah.db.models.sources import Source, SourceSeedEntry
from amanah.domain.enums import (
    ApprovalStatus,
    PublicPlatform,
    RetentionPolicy,
    SamplingStratum,
    SeedEntryKind,
    SourceKind,
)

logger = logging.getLogger(__name__)

#: Where the reviewed configuration lives when nothing overrides it. These files
#: hold no secrets — only public feed URLs, purposes, caps, and approvals — so
#: the reviewed copy is committed and directly usable. A deployment that ships
#: the package without the repository points `SOURCE_CONFIG_DIRECTORY` at its own.
DEFAULT_CONFIG_DIRECTORY = Path(__file__).resolve().parents[4] / "config"

SOURCES_FILENAME = "sources.example.yml"
SEEDS_FILENAME = "source-seeds.example.yml"


def config_directory(configured: Path | None = None) -> Path:
    """The reviewed configuration directory, honouring the setting when present."""
    return configured if configured is not None else DEFAULT_CONFIG_DIRECTORY


#: Only English is evaluated for P0. A non-English entry may sit in the reviewed
#: configuration, but it is not runnable until the classifier and its evaluation
#: set cover that language (`spec.md` section 10.3).
MVP_LANGUAGES = frozenset({"en"})


class ConfigurationError(RuntimeError):
    """The reviewed configuration is missing, unreadable, or invalid."""


class TopicalFilter(BaseModel):
    """Per-feed subject-matter filter (B-S9.7).

    `keep_terms` selects what a feed is monitored *for*; `drop_terms` removes the
    desks that share a feed but not a purpose, such as sport and celebrity. A
    kept item is on topic, nothing more: neutral reporting is in scope and
    Muslim-related vocabulary is never treated as harm.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    keep_terms: tuple[str, ...] = ()
    drop_terms: tuple[str, ...] = ()

    def matches(self, *fields: str | None) -> bool:
        """Whether the joined fields are on topic for this feed."""
        haystack = " ".join(field for field in fields if field).casefold()
        if not haystack:
            return False
        if any(term.casefold() in haystack for term in self.drop_terms):
            return False
        if not self.keep_terms:
            return True
        return any(term.casefold() in haystack for term in self.keep_terms)


class SourceConfig(BaseModel):
    """One configured origin of content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_key: str = Field(min_length=1, max_length=100)
    kind: SourceKind
    platform: PublicPlatform
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    retention_policy: RetentionPolicy
    is_enabled: bool = False
    homepage_url: str | None = None
    policy_url: str | None = None

    @field_validator("homepage_url", "policy_url")
    @classmethod
    def _check_https(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("https://"):
            raise ValueError("must be an absolute https URL")
        return value


class SeedConfig(BaseModel):
    """One reviewed seed, query, or feed a source may collect from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    registry_key: str = Field(min_length=1, max_length=200)
    source_key: str = Field(min_length=1, max_length=100)
    entry_kind: SeedEntryKind
    display_name: str = Field(min_length=1)
    provider_reference: str = Field(min_length=1)
    query_family: str = Field(min_length=1, max_length=100)
    query_purpose: str = Field(min_length=1)
    sampling_stratum: SamplingStratum
    language: str = Field(pattern=r"^[a-z]{2}$")
    country_scope: str | None = Field(default=None, max_length=50)
    item_cap: int = Field(gt=0)
    approval_status: ApprovalStatus = ApprovalStatus.pending
    approved_by: str | None = None
    last_reviewed_at: datetime | None = None
    topical_filter: TopicalFilter | None = None
    #: Stamped from the enclosing document rather than written per entry, so a
    #: seed and the version it was approved under can never disagree. Together
    #: they are the documented identity of an approved configuration entry.
    config_version: str = ""

    @property
    def is_runnable(self) -> bool:
        """Approved *and* inside the evaluated language scope.

        Both conditions, not either: an approved French feed is still outside the
        English-only MVP, and an unapproved English one is still unapproved.
        """
        return self.approval_status is ApprovalStatus.approved and self.language in MVP_LANGUAGES


class SourceConfiguration(BaseModel):
    """The reviewed source catalogue at one configuration version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config_version: str = Field(min_length=1, max_length=50)
    sources: tuple[SourceConfig, ...]

    def by_key(self, source_key: str) -> SourceConfig | None:
        return next((source for source in self.sources if source.source_key == source_key), None)


class SeedConfiguration(BaseModel):
    """The reviewed seed catalogue at one configuration version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config_version: str = Field(min_length=1, max_length=50)
    seeds: tuple[SeedConfig, ...]

    @model_validator(mode="after")
    def _stamp_config_version(self) -> Self:
        """Give every entry the version of the document it came from."""
        stamped = tuple(
            seed.model_copy(update={"config_version": self.config_version}) for seed in self.seeds
        )
        object.__setattr__(self, "seeds", stamped)
        return self

    def runnable_for(self, source_key: str) -> tuple[SeedConfig, ...]:
        """Approved, in-scope entries for one source, in configuration order."""
        return tuple(
            seed for seed in self.seeds if seed.source_key == source_key and seed.is_runnable
        )

    def by_registry_key(self, registry_key: str) -> SeedConfig | None:
        return next((seed for seed in self.seeds if seed.registry_key == registry_key), None)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"configuration file is missing: {path.name}")
    try:
        # `safe_load` only: the loader that can construct arbitrary Python
        # objects has no place reading a file this service will act on.
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"configuration file is not valid YAML: {path.name}") from exc
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"configuration file is not a mapping: {path.name}")
    return loaded


def load_source_configuration(directory: Path | None = None) -> SourceConfiguration:
    """Read and validate the reviewed source catalogue."""
    return SourceConfiguration.model_validate(
        _read_yaml(config_directory(directory) / SOURCES_FILENAME)
    )


def load_seed_configuration(directory: Path | None = None) -> SeedConfiguration:
    """Read and validate the reviewed seed catalogue."""
    return SeedConfiguration.model_validate(
        _read_yaml(config_directory(directory) / SEEDS_FILENAME)
    )


def project_sources(session: Session, configuration: SourceConfiguration) -> int:
    """Write the reviewed source catalogue into the database.

    Idempotent on `source_key`, so running it twice converges. Connector status
    is deliberately not touched: it is observed at run time, not declared in a
    file, and overwriting it here would let configuration claim a connector is
    healthy when nothing has contacted it.
    """
    written = 0
    for source in configuration.sources:
        values = {
            "source_key": source.source_key,
            "kind": source.kind,
            "platform": source.platform,
            "name": source.name,
            "purpose": source.purpose,
            "retention_policy": source.retention_policy,
            "is_enabled": source.is_enabled,
            "homepage_url": source.homepage_url,
            "policy_url": source.policy_url,
            "config_version": configuration.config_version,
        }
        session.execute(
            insert(Source)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Source.source_key],
                set_={key: value for key, value in values.items() if key != "source_key"},
            )
        )
        written += 1
    session.commit()
    logger.info("source configuration projected", extra={"sources": written})
    return written


def project_seeds(session: Session, configuration: SeedConfiguration) -> int:
    """Write approved, in-scope seed entries into the database.

    Entries that are pending, rejected, or outside the evaluated language scope
    are skipped rather than written as disabled rows: `spec.md` section 10.3 says
    an unreviewed entry stays inactive, and the cheapest way to guarantee that is
    for it not to exist in the runtime table at all.
    """
    identifiers = _source_ids(session, {seed.source_key for seed in configuration.seeds})
    written = 0
    skipped = 0
    for seed in configuration.seeds:
        if not seed.is_runnable:
            skipped += 1
            continue
        source_id = identifiers.get(seed.source_key)
        if source_id is None:
            raise ConfigurationError(
                f"seed {seed.registry_key} names a source that is not configured"
            )
        values = {
            "registry_key": seed.registry_key,
            "source_id": source_id,
            "entry_kind": seed.entry_kind,
            "display_name": seed.display_name,
            "provider_reference": seed.provider_reference,
            "query_family": seed.query_family,
            "query_purpose": seed.query_purpose,
            "sampling_stratum": seed.sampling_stratum,
            "language": seed.language,
            "country_scope": seed.country_scope,
            "item_cap": seed.item_cap,
            "approval_status": seed.approval_status,
            "approved_by": seed.approved_by,
            "config_version": configuration.config_version,
            "last_reviewed_at": seed.last_reviewed_at,
        }
        session.execute(
            insert(SourceSeedEntry)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[SourceSeedEntry.registry_key, SourceSeedEntry.config_version],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in {"registry_key", "config_version"}
                },
            )
        )
        written += 1
    session.commit()
    logger.info(
        "seed configuration projected",
        extra={"approved": written, "skipped": skipped, "version": configuration.config_version},
    )
    return written


def _source_ids(session: Session, source_keys: Iterable[str]) -> dict[str, Any]:
    rows = session.execute(
        select(Source.source_key, Source.id).where(Source.source_key.in_(tuple(source_keys)))
    ).all()
    return {row.source_key: row.id for row in rows}
