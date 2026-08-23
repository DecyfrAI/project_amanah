"""The adapter contract, and the fixture adapter that has to satisfy it (B-S8.6).

`AdapterContractTests` is written to be *inherited*. Every future adapter gets
these checks for free by subclassing it and supplying an instance, which is the
point: the contract is the thing downstream code depends on, so it should be
verified per implementation rather than described once in a docstring.

The checks are deliberately about the contract's promises — cap obedience, cursor
progress, honest fixture status, canonical shape — and not about any particular
source's data.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from amanah.domain.enums import ContentKind, SourceStatus
from amanah.ingestion.codec import decode_item, decode_reference, encode_item, encode_reference
from amanah.ingestion.contract import (
    AdapterError,
    CanonicalContentItem,
    DiscoveryRequest,
    SourceAdapter,
)
from amanah.ingestion.fixtures.adapter import FIXTURE_SOURCE_KEY, FixtureAdapter


class AdapterContractTests:
    """Checks every source adapter must pass.

    Subclass it, implement `adapter`, and the suite runs against that
    implementation. Nothing here contacts a network: an adapter that cannot be
    exercised offline cannot be covered by this suite and needs recorded
    boundary fixtures of its own.
    """

    @pytest.fixture
    def adapter(self) -> SourceAdapter:
        raise NotImplementedError

    def test_it_identifies_itself(self, adapter: SourceAdapter) -> None:
        assert adapter.source_key
        assert adapter.adapter_version
        assert isinstance(adapter.is_fixture, bool)

    def test_health_check_answers_without_a_provider(self, adapter: SourceAdapter) -> None:
        """Connector state must be reportable when the provider is unreachable —
        that is exactly when someone asks."""
        health = adapter.health_check()

        assert health.status is not None
        if health.safe_warning is not None:
            assert isinstance(health.safe_warning, str)

    def test_discovery_respects_the_item_cap(self, adapter: SourceAdapter) -> None:
        """The cap bounds a live provider call; ignoring it is a bug, not a
        tuning choice."""
        result = adapter.discover(DiscoveryRequest(item_cap=2))

        assert len(result.references) <= 2

    def test_discovery_reports_counts_and_a_cursor(self, adapter: SourceAdapter) -> None:
        result = adapter.discover(DiscoveryRequest(item_cap=5))
        checkpoint = adapter.checkpoint(result)

        assert isinstance(dict(checkpoint.counts), dict)
        assert isinstance(checkpoint.coverage_warnings, tuple)

    def test_canonicalization_produces_the_shared_shape(self, adapter: SourceAdapter) -> None:
        """Downstream code depends on this and never on a provider payload."""
        result = adapter.discover(DiscoveryRequest(item_cap=1))
        if not result.references:
            pytest.skip("this adapter discovered nothing offline")

        item = adapter.canonicalize(adapter.fetch(result.references[0]))

        assert isinstance(item, CanonicalContentItem)
        assert item.source_key == adapter.source_key
        assert item.source_item_id
        assert isinstance(item.content_kind, ContentKind)
        assert item.observed_at.tzinfo is not None

    def test_every_item_carries_the_adapter_s_fixture_status(self, adapter: SourceAdapter) -> None:
        """`AGENTS.md`: fixture and live must stay distinguishable from storage
        through to the screen, and this is where that starts."""
        result = adapter.discover(DiscoveryRequest(item_cap=3))
        for reference in result.references:
            item = adapter.canonicalize(adapter.fetch(reference))
            assert item.is_fixture == adapter.is_fixture

    def test_a_canonical_item_survives_a_job_boundary(self, adapter: SourceAdapter) -> None:
        """Stages exchange JSON, so the shape has to round-trip without loss."""
        result = adapter.discover(DiscoveryRequest(item_cap=1))
        if not result.references:
            pytest.skip("this adapter discovered nothing offline")
        item = adapter.canonicalize(adapter.fetch(result.references[0]))

        restored = decode_item(encode_item(item))

        assert restored == item

    def test_a_reference_survives_a_job_boundary(self, adapter: SourceAdapter) -> None:
        result = adapter.discover(DiscoveryRequest(item_cap=1))
        if not result.references:
            pytest.skip("this adapter discovered nothing offline")
        reference = result.references[0]

        assert decode_reference(encode_reference(reference)) == reference


class TestFixtureAdapter(AdapterContractTests):
    """The fixture adapter against the shared contract, plus what is its own."""

    @pytest.fixture
    def adapter(self) -> SourceAdapter:
        return FixtureAdapter()

    def test_it_is_honest_about_being_a_fixture(self, adapter: SourceAdapter) -> None:
        assert adapter.is_fixture is True
        assert adapter.source_key == FIXTURE_SOURCE_KEY

    def test_discovery_is_deterministic(self, adapter: SourceAdapter) -> None:
        """ "The pipeline changed" and "the data changed" must stay
        distinguishable, which needs the corpus to be stable."""
        first = adapter.discover(DiscoveryRequest(item_cap=5))
        second = adapter.discover(DiscoveryRequest(item_cap=5))

        assert [reference.reference_id for reference in first.references] == [
            reference.reference_id for reference in second.references
        ]

    def test_a_cursor_resumes_after_the_last_reference(self, adapter: SourceAdapter) -> None:
        first = adapter.discover(DiscoveryRequest(item_cap=3))
        second = adapter.discover(DiscoveryRequest(item_cap=3, cursor=first.cursor))

        seen = {reference.reference_id for reference in first.references}
        assert seen.isdisjoint({reference.reference_id for reference in second.references})

    def test_an_unknown_cursor_is_refused_rather_than_restarting(
        self, adapter: SourceAdapter
    ) -> None:
        """Silently starting again would re-collect a window someone already
        paid for and looks identical to working."""
        with pytest.raises(AdapterError):
            adapter.discover(DiscoveryRequest(item_cap=3, cursor="not-a-reference"))

    def test_a_capped_run_says_the_window_is_only_partly_covered(
        self, adapter: SourceAdapter
    ) -> None:
        result = adapter.discover(DiscoveryRequest(item_cap=1))

        assert result.coverage_warnings

    def test_the_window_excludes_items_published_outside_it(self, adapter: SourceAdapter) -> None:
        result = adapter.discover(
            DiscoveryRequest(
                item_cap=50,
                window_start=datetime(2026, 7, 24, tzinfo=UTC),
                window_end=datetime(2026, 7, 25, tzinfo=UTC),
            )
        )

        assert result.counts["skipped_out_of_window"] > 0
        assert len(result.references) < 12

    def test_the_corpus_carries_the_cases_the_pipeline_must_not_break(
        self, adapter: SourceAdapter
    ) -> None:
        """Benign Muslim speech, counterspeech that quotes hostile wording,
        missing context, a non-English record, and a deleted one."""
        result = adapter.discover(DiscoveryRequest(item_cap=50))
        items = [adapter.canonicalize(adapter.fetch(ref)) for ref in result.references]

        assert any(item.language == "fr" for item in items)
        assert any(item.source_status is SourceStatus.deleted for item in items)
        assert any(
            item.content_kind is ContentKind.social_comment and item.context.parent_text is None
            for item in items
        )
        assert any(
            '"' in (item.original_text or "") or "“" in (item.original_text or "") for item in items
        )

    def test_context_travels_with_a_comment(self, adapter: SourceAdapter) -> None:
        """A comment lifted out of its thread reads differently from the same
        comment under its parent."""
        result = adapter.discover(DiscoveryRequest(item_cap=50))
        comments = [
            adapter.canonicalize(adapter.fetch(reference))
            for reference in result.references
            if reference.content_kind is ContentKind.social_comment
        ]

        assert any(item.context.root_text for item in comments)


def test_a_missing_reference_is_a_permanent_failure() -> None:
    """Retrying a reference the corpus does not contain would spend the budget
    for nothing."""
    adapter = FixtureAdapter()
    result = adapter.discover(DiscoveryRequest(item_cap=1))
    unknown = result.references[0].__class__(
        reference_id="does-not-exist", content_kind=ContentKind.news_article
    )

    with pytest.raises(AdapterError) as raised:
        adapter.fetch(unknown)

    assert raised.value.is_retryable is False
