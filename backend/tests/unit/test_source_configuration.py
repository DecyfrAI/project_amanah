"""Reviewed source and seed configuration (B-S8.9, B-S8.10, B-S9.7).

Two questions. Does the committed configuration actually load and match the
allowlist it was reviewed from? And can an unreviewed entry get in — through a
typo, a missing approval, or a language nobody has evaluated?

The committed files are loaded here rather than a synthetic copy, because a
configuration that validates in a fixture and not in the repository would be a
test that proves nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from amanah.domain.enums import ApprovalStatus, SamplingStratum, SeedEntryKind, SourceKind
from amanah.ingestion.configuration import (
    MVP_LANGUAGES,
    ConfigurationError,
    SeedConfiguration,
    SourceConfiguration,
    TopicalFilter,
    load_seed_configuration,
    load_source_configuration,
)

#: Feeds `docs/news-rss-sources.md` checked and rejected on 23 August 2026.
#: `AGENTS.md` forbids replacing them with a guess, so their absence is a
#: property worth asserting rather than a coincidence.
REJECTED_FEED_HOSTS = ("feeds.reuters.com", "reutersagency.com", "apnews.com", "ctvnews.ca")


@pytest.fixture(scope="module")
def sources() -> SourceConfiguration:
    return load_source_configuration()


@pytest.fixture(scope="module")
def seeds() -> SeedConfiguration:
    return load_seed_configuration()


def test_the_committed_configuration_loads(
    sources: SourceConfiguration, seeds: SeedConfiguration
) -> None:
    assert sources.sources
    assert seeds.seeds


def test_the_two_files_share_one_version(
    sources: SourceConfiguration, seeds: SeedConfiguration
) -> None:
    """They are one reviewed artifact. Versions that disagree mean one was
    edited without the review that produced the other."""
    assert sources.config_version == seeds.config_version


def test_every_seed_names_a_configured_source(
    sources: SourceConfiguration, seeds: SeedConfiguration
) -> None:
    for seed in seeds.seeds:
        assert sources.by_key(seed.source_key) is not None, seed.registry_key


def test_no_rejected_feed_reappears(seeds: SeedConfiguration) -> None:
    """Reuters, AP, and the old CTV path were checked and did not work. Adding a
    guessed replacement is prohibited."""
    references = " ".join(seed.provider_reference for seed in seeds.seeds)

    for host in REJECTED_FEED_HOSTS:
        assert host not in references


def test_every_feed_is_https(seeds: SeedConfiguration) -> None:
    feeds = [seed for seed in seeds.seeds if seed.entry_kind is SeedEntryKind.feed]

    assert feeds
    assert all(seed.provider_reference.startswith("https://") for seed in feeds)


def test_every_seed_carries_its_sampling_provenance(seeds: SeedConfiguration) -> None:
    """`spec.md` section 10.3: registry inclusion is sampling relevance, never a
    hate label, and the purpose has to travel with the entry to say so."""
    for seed in seeds.seeds:
        assert seed.query_purpose.strip()
        assert seed.query_family.strip()
        assert isinstance(seed.sampling_stratum, SamplingStratum)


def test_every_runnable_seed_is_approved_and_attributed(seeds: SeedConfiguration) -> None:
    for seed in seeds.seeds:
        if seed.is_runnable:
            assert seed.approval_status is ApprovalStatus.approved
            assert seed.approved_by


def test_every_seed_is_capped(seeds: SeedConfiguration) -> None:
    assert all(seed.item_cap > 0 for seed in seeds.seeds)


def test_the_open_datapack_source_is_the_single_controlled_row(
    sources: SourceConfiguration,
) -> None:
    """`spec.md` section 14.6 requires exactly one, displaying `N/A`."""
    datapacks = [source for source in sources.sources if source.kind is SourceKind.open_datapack]

    assert len(datapacks) == 1
    assert datapacks[0].name == "N/A"


def test_youtube_ships_disabled(sources: SourceConfiguration) -> None:
    """It needs a credential and approved seeds; neither is assumed."""
    youtube = sources.by_key("youtube")

    assert youtube is not None
    assert youtube.is_enabled is False


def test_every_news_outlet_has_a_homepage_for_attribution(
    sources: SourceConfiguration,
) -> None:
    """The reviewed licence notes ask for attribution and a link back."""
    outlets = [source for source in sources.sources if source.kind is SourceKind.news]

    assert outlets
    assert all(source.homepage_url for source in outlets)


# -- what cannot get in ---------------------------------------------------


def test_an_unapproved_entry_is_not_runnable(seeds: SeedConfiguration) -> None:
    pending = seeds.seeds[0].model_copy(update={"approval_status": ApprovalStatus.pending})

    assert pending.is_runnable is False


def test_a_language_outside_the_evaluated_scope_is_not_runnable(
    seeds: SeedConfiguration,
) -> None:
    """`spec.md` section 10.3 keeps the French candidate disabled until the
    classifier and its evaluation set cover the language."""
    french = seeds.seeds[0].model_copy(update={"language": "fr"})

    assert french.is_runnable is False
    assert MVP_LANGUAGES == {"en"}


def test_a_mistyped_field_is_an_error_rather_than_a_silent_default() -> None:
    """A typo that is ignored is a seed running under settings nobody chose."""
    with pytest.raises(ValidationError):
        SourceConfiguration.model_validate(
            {
                "config_version": "1",
                "sources": [
                    {
                        "source_key": "x",
                        "kind": "news",
                        "platform": "news_web",
                        "name": "X",
                        "purpose": "Testing.",
                        "retention_policy": "limited_by_terms",
                        "enabled": True,  # the field is `is_enabled`
                    }
                ],
            }
        )


def test_a_non_https_homepage_is_refused() -> None:
    with pytest.raises(ValidationError):
        SourceConfiguration.model_validate(
            {
                "config_version": "1",
                "sources": [
                    {
                        "source_key": "x",
                        "kind": "news",
                        "platform": "news_web",
                        "name": "X",
                        "purpose": "Testing.",
                        "retention_policy": "limited_by_terms",
                        "homepage_url": "http://insecure.test",
                    }
                ],
            }
        )


def test_a_missing_configuration_file_is_reported_clearly(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="missing"):
        load_source_configuration(tmp_path)


def test_a_configuration_file_that_is_not_yaml_is_refused(tmp_path: Path) -> None:
    (tmp_path / "sources.example.yml").write_text("just a string", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="not a mapping"):
        load_source_configuration(tmp_path)


# -- the topical filter ---------------------------------------------------


def test_the_filter_keeps_subject_matter_and_drops_other_desks() -> None:
    """B-S9.7. Relevance, not harm: an article that passes is on topic and
    nothing more."""
    topical = TopicalFilter(keep_terms=("mosque", "hate crime"), drop_terms=("football",))

    assert topical.matches("Council debates mosque safety") is True
    assert topical.matches("Football transfer roundup") is False
    assert topical.matches("A story about gardening") is False


def test_a_drop_term_beats_a_keep_term() -> None:
    """A sport story that mentions a mosque is still a sport story."""
    topical = TopicalFilter(keep_terms=("mosque",), drop_terms=("football",))

    assert topical.matches("Football club visits local mosque") is False


def test_matching_is_case_insensitive_and_reads_every_field() -> None:
    topical = TopicalFilter(keep_terms=("hate crime",))

    assert topical.matches("A Headline", "The body mentions a HATE CRIME report") is True


def test_a_filter_with_no_keep_terms_keeps_everything() -> None:
    """A feed that is entirely on topic needs no keep list, only a drop list."""
    topical = TopicalFilter(drop_terms=("football",))

    assert topical.matches("Anything at all") is True


def test_neutral_muslim_related_reporting_passes_the_filter(
    seeds: SeedConfiguration,
) -> None:
    """The committed keep list includes Muslim-related vocabulary *for
    topicality*. Passing it says an article is in scope, never that it is
    hateful."""
    topical = seeds.seeds[0].topical_filter

    assert topical is not None
    assert topical.matches("Mosque opens a community food bank") is True
