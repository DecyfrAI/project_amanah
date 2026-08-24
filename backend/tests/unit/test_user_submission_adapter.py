"""The user-submission adapter's canonical translation (B-S16.3).

Only the pure half is exercised here — the fetching half needs a database and is
covered by `tests/db/test_contribution_api.py`. What matters is that a retrieved
page becomes a canonical item carrying metadata and nothing else, and that the
submission it came from can be recovered from what the pipeline stores.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from amanah.domain.enums import ContentKind, SubmissionStatus
from amanah.ingestion.contract import AdapterError, CanonicalContentItem, SourceReference
from amanah.ingestion.urls.adapter import (
    SUBMISSION_ID_KEY,
    UserSubmissionAdapter,
    _reference_hint,
    submission_id_from,
)
from amanah.ingestion.urls.extract import PageMetadata
from amanah.ingestion.urls.safe_fetch import RetrievalResult

RETRIEVED_AT = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _analyzed(**overrides: object) -> RetrievalResult:
    metadata = PageMetadata(
        title="Synthetic headline",
        description="Synthetic permitted excerpt.",
        canonical_url="https://example.invalid/story",
        site_name="Synthetic Publisher",
        language="en",
    )
    values: dict[str, object] = {
        "status": SubmissionStatus.analyzed,
        "canonical_url": "https://example.invalid/story",
        "metadata": metadata,
        "retrieved_at": RETRIEVED_AT,
    }
    values.update(overrides)
    return RetrievalResult(**values)  # type: ignore[arg-type]


def _reference(submission_id: object, user_id: object) -> SourceReference:
    return SourceReference(
        reference_id=str(submission_id),
        content_kind=ContentKind.news_article,
        hint=_reference_hint(submission_id, user_id, _analyzed()),  # type: ignore[arg-type]
    )


def _canonicalize(
    adapter: UserSubmissionAdapter, reference: SourceReference
) -> CanonicalContentItem:
    return adapter.canonicalize(adapter.fetch(reference))


@pytest.fixture
def adapter() -> UserSubmissionAdapter:
    """Constructed without a session: only the pure methods are used here."""
    return UserSubmissionAdapter.__new__(UserSubmissionAdapter)


def test_the_hint_carries_metadata_and_never_the_page_body() -> None:
    """`spec.md` section 10.5 permits metadata and a short excerpt. The retrieved
    bytes must not travel into the job queue."""
    hint = _reference_hint(uuid4(), uuid4(), _analyzed())

    assert hint["title"] == "Synthetic headline"
    assert hint["canonical_url"] == "https://example.invalid/story"
    assert "content" not in hint
    assert "body" not in hint


def test_a_retrieved_page_becomes_a_canonical_item(adapter: UserSubmissionAdapter) -> None:
    submission_id = uuid4()
    user_id = uuid4()

    item = _canonicalize(adapter, _reference(submission_id, user_id))

    assert item.source_key == "user_submission"
    assert item.source_item_id == f"submission:{submission_id}"
    assert item.canonical_url == "https://example.invalid/story"
    assert item.title == "Synthetic headline"
    assert item.permitted_excerpt == "Synthetic permitted excerpt."
    assert item.is_fixture is False
    assert item.submitted_origin == user_id


def test_the_canonical_item_carries_the_submission_it_came_from(
    adapter: UserSubmissionAdapter,
) -> None:
    """This is what lets the pipeline turn "processing" into a link to the item
    once the canonical write lands (FR-SUBMIT-008)."""
    submission_id = uuid4()

    item = _canonicalize(adapter, _reference(submission_id, uuid4()))

    assert item.provider_metadata[SUBMISSION_ID_KEY] == str(submission_id)
    assert submission_id_from(item) == submission_id


def test_a_collected_item_has_no_submission_to_recover() -> None:
    """`submission_id_from` is called unconditionally by the pipeline, so it has
    to answer for items that never came from a person."""
    collected = CanonicalContentItem(
        source_key="rss_bbc_news",
        source_item_id="article-1",
        content_kind=ContentKind.news_article,
        observed_at=RETRIEVED_AT,
        is_fixture=False,
    )

    assert submission_id_from(collected) is None


def test_an_unreadable_submission_identifier_is_reported_rather_than_raised() -> None:
    collected = CanonicalContentItem(
        source_key="user_submission",
        source_item_id="submission:x",
        content_kind=ContentKind.news_article,
        observed_at=RETRIEVED_AT,
        is_fixture=False,
        provider_metadata={SUBMISSION_ID_KEY: "not-a-uuid"},
    )

    assert submission_id_from(collected) is None


def test_a_reference_with_no_hint_is_refused(adapter: UserSubmissionAdapter) -> None:
    """A stage that cannot read its own input is broken, not unlucky."""
    empty = SourceReference(reference_id="x", content_kind=ContentKind.news_article)

    with pytest.raises(AdapterError, match="submission_reference_incomplete"):
        adapter.fetch(empty)


def test_an_absent_field_stays_absent_rather_than_becoming_an_empty_string(
    adapter: UserSubmissionAdapter,
) -> None:
    """A page with no description yields `None`, not a fabricated summary."""
    bare = _analyzed(metadata=PageMetadata(canonical_url="https://example.invalid/story"))
    reference = SourceReference(
        reference_id="x",
        content_kind=ContentKind.news_article,
        hint=_reference_hint(uuid4(), uuid4(), bare),
    )

    item = _canonicalize(adapter, reference)

    assert item.title is None
    assert item.permitted_excerpt is None
    assert item.publisher_or_container is None
