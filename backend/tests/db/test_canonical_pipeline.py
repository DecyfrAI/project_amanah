"""The fixture pipeline end to end, against a real database (B-S8.7, B-S12.7).

The claim under test is the one everything else rests on: running the same
collection twice produces the same rows. Not "roughly the same" — the same
identifiers, the same count, the same hashes. If that fails, every retry, every
resumed run, and every duplicate delivery in the system is unsafe.

The fixture adapter is used because it is deterministic and contacts nothing, so
a failure here is a pipeline failure and never a provider one.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from amanah.canonical.encryption import ContentCipher
from amanah.canonical.store import ContentStore
from amanah.db.models.content import CollectionRun, ContentItem
from amanah.db.models.jobs import BackgroundJob
from amanah.db.models.sources import Source
from amanah.domain.enums import CollectionMode, ContentKind, JobStage, JobState, SourceStatus
from amanah.ingestion.contract import CanonicalContentItem, ContentContext
from amanah.ingestion.fixtures.adapter import FIXTURE_SOURCE_KEY, FixtureAdapter
from amanah.ingestion.pipeline import CollectionPipeline
from amanah.jobs.runs import CollectionRunService, RunDispatch
from tests.db import factories

WORKER = "pipeline-worker"


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as active:
        yield active


@pytest.fixture
def fixture_source(engine: Engine) -> None:
    with engine.begin() as connection:
        factories.insert_source(connection, source_key=FIXTURE_SOURCE_KEY, name="Fixtures")


def _run(session: Session, key: str) -> CollectionRun:
    run, _ = CollectionRunService(session).dispatch(
        RunDispatch(
            source_key=FIXTURE_SOURCE_KEY,
            mode=CollectionMode.fixture,
            adapter_version="pending",
            idempotency_key=key,
            item_cap=50,
        )
    )
    return run


def _execute(session: Session, run: CollectionRun) -> CollectionPipeline:
    pipeline = CollectionPipeline(session, adapter=FixtureAdapter(), worker_id=WORKER)
    pipeline.begin(run)
    while pipeline.process_next() is not None:
        pass
    pipeline.finish(run)
    return pipeline


def _stored(session: Session) -> list[ContentItem]:
    return list(session.execute(select(ContentItem).order_by(ContentItem.source_item_id)).scalars())


def test_a_fixture_run_stores_the_whole_corpus(session: Session, fixture_source: None) -> None:
    del fixture_source
    run = _run(session, "fixture-run-1")

    _execute(session, run)

    session.refresh(run)
    items = _stored(session)
    assert run.status is JobState.succeeded
    assert len(items) == 12
    assert run.counts["stored"] == 12
    assert run.completed_at is not None


def test_re_running_the_same_collection_changes_nothing(
    session: Session, fixture_source: None
) -> None:
    """B-S8.7. The property every retry in the system depends on."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))
    first = {item.source_item_id: item.content_hash for item in _stored(session)}

    _execute(session, _run(session, "fixture-run-2"))
    second = {item.source_item_id: item.content_hash for item in _stored(session)}

    assert first == second
    assert len(second) == 12


def test_re_running_updates_rather_than_duplicating(session: Session, fixture_source: None) -> None:
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))
    identifiers = {item.id for item in _stored(session)}

    _execute(session, _run(session, "fixture-run-2"))

    assert {item.id for item in _stored(session)} == identifiers


def test_every_stage_checkpoints_before_the_next_one_starts(
    session: Session, fixture_source: None
) -> None:
    """B-S7.4. A `normalize` job exists only because a `fetch` job stored the
    canonical item that is now its input."""
    del fixture_source
    run = _run(session, "fixture-run-1")

    _execute(session, run)

    jobs = list(
        session.execute(
            select(BackgroundJob).where(BackgroundJob.collection_run_id == run.id)
        ).scalars()
    )
    stages = {job.stage for job in jobs}
    assert stages == {JobStage.discover, JobStage.fetch, JobStage.normalize}
    assert all(job.state is JobState.succeeded for job in jobs)
    for job in jobs:
        if job.stage is JobStage.normalize:
            assert job.checkpoint["content_item_id"]


def test_one_fetch_job_exists_per_reference(session: Session, fixture_source: None) -> None:
    """The fan-out is what makes a single failing item survivable."""
    del fixture_source
    run = _run(session, "fixture-run-1")

    _execute(session, run)

    fetch_jobs = session.execute(
        select(func.count())
        .select_from(BackgroundJob)
        .where(
            BackgroundJob.collection_run_id == run.id,
            BackgroundJob.stage == JobStage.fetch,
        )
    ).scalar_one()
    assert fetch_jobs == 12


def test_stored_items_are_marked_as_fixtures(session: Session, fixture_source: None) -> None:
    """`AGENTS.md`: fixture and live stay distinguishable through to the screen."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))

    assert all(item.is_fixture for item in _stored(session))


def test_a_deleted_source_item_keeps_its_state(session: Session, fixture_source: None) -> None:
    """`spec.md` section 15.1: a source-deleted item stays a research record and
    says that it is gone."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))

    deleted = [item for item in _stored(session) if item.source_status is SourceStatus.deleted]

    assert len(deleted) == 1


def test_an_undetermined_language_is_stored_as_null(session: Session, fixture_source: None) -> None:
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))

    assert any(item.language is None for item in _stored(session))
    assert any(item.language == "fr" for item in _stored(session))


def test_context_is_stored_for_a_comment_and_omitted_where_absent(
    session: Session, fixture_source: None
) -> None:
    """B-S12.3. "No parent" and "parent unavailable" stay distinguishable."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))
    items = {item.source_item_id: item for item in _stored(session)}

    with_parent = items["fixture-comment-0001"]
    without_parent = items["fixture-comment-0005"]

    assert with_parent.normalized_context["parent_text"]
    assert "parent_text" not in without_parent.normalized_context
    assert without_parent.normalized_context["root_text"]


def test_quoted_wording_survives_into_storage(session: Session, fixture_source: None) -> None:
    """Counterspeech that quotes hostile wording must not be flattened, and
    nothing is censored on the way in."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))
    items = {item.source_item_id: item for item in _stored(session)}

    quoting = items["fixture-comment-0003"]

    assert quoting.normalized_text is not None
    assert "they do not belong here" in quoting.normalized_text
    assert "*" not in quoting.normalized_text


def test_tracking_parameters_are_stripped_from_a_stored_url(
    session: Session, fixture_source: None
) -> None:
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))
    items = {item.source_item_id: item for item in _stored(session)}

    article = items["fixture-news-0002"]

    assert article.canonical_url is not None
    assert "utm_source" not in article.canonical_url


def test_a_run_records_its_adapter_version(session: Session, fixture_source: None) -> None:
    """A dispatch says what was asked for; only the worker knows what answered."""
    del fixture_source
    run = _run(session, "fixture-run-1")

    _execute(session, run)

    session.refresh(run)
    assert run.adapter_version == FixtureAdapter().adapter_version


def test_a_successful_run_updates_the_source_freshness(
    session: Session, fixture_source: None
) -> None:
    """The UI shows actual last-success time, so it has to be written."""
    del fixture_source
    _execute(session, _run(session, "fixture-run-1"))

    source = session.execute(
        select(Source).where(Source.source_key == FIXTURE_SOURCE_KEY)
    ).scalar_one()

    assert source.last_success_at is not None
    assert source.last_checked_at is not None


# -- deduplication --------------------------------------------------------


def _news_item(**overrides: object) -> CanonicalContentItem:
    values: dict[str, object] = {
        "source_key": FIXTURE_SOURCE_KEY,
        "source_item_id": "news-1",
        "content_kind": ContentKind.news_article,
        "observed_at": datetime(2026, 7, 20, tzinfo=UTC),
        "is_fixture": True,
        "canonical_url": "https://example.test/story",
        "title": "Council debates mosque safety",
        "publisher_or_container": "Synthetic Wire",
        "permitted_excerpt": "A short synthetic description.",
        "context": ContentContext(title="Council debates mosque safety"),
    }
    values.update(overrides)
    return CanonicalContentItem(**values)  # type: ignore[arg-type]


def _source_id(session: Session) -> object:
    return session.execute(
        select(Source.id).where(Source.source_key == FIXTURE_SOURCE_KEY)
    ).scalar_one()


def test_the_same_article_from_two_feeds_links_rather_than_duplicating(
    session: Session, fixture_source: None
) -> None:
    """B-S9.4. A duplicated article inflates the denominator of every rate."""
    del fixture_source
    store = ContentStore(session)
    source_id = _source_id(session)

    first = store.upsert(_news_item(), source_id=source_id)  # type: ignore[arg-type]
    second = store.upsert(
        _news_item(
            source_item_id="news-2",
            canonical_url="https://www.example.test/story/?utm_source=feed",
        ),
        source_id=source_id,  # type: ignore[arg-type]
    )
    session.commit()

    assert second.is_duplicate is True
    assert second.content_item_id == first.content_item_id
    assert session.execute(select(func.count()).select_from(ContentItem)).scalar_one() == 1


def test_a_syndicated_headline_is_caught_by_the_second_key(
    session: Session, fixture_source: None
) -> None:
    """Same publisher and headline under a different URL is still one story."""
    del fixture_source
    store = ContentStore(session)
    source_id = _source_id(session)

    store.upsert(_news_item(), source_id=source_id)  # type: ignore[arg-type]
    duplicate = store.upsert(
        _news_item(source_item_id="news-3", canonical_url="https://example.test/other-path"),
        source_id=source_id,  # type: ignore[arg-type]
    )
    session.commit()

    assert duplicate.is_duplicate is True


def test_two_different_articles_are_both_kept(session: Session, fixture_source: None) -> None:
    del fixture_source
    store = ContentStore(session)
    source_id = _source_id(session)

    store.upsert(_news_item(), source_id=source_id)  # type: ignore[arg-type]
    store.upsert(
        _news_item(
            source_item_id="news-4",
            canonical_url="https://example.test/different",
            title="Police publish hate crime figures",
        ),
        source_id=source_id,  # type: ignore[arg-type]
    )
    session.commit()

    assert session.execute(select(func.count()).select_from(ContentItem)).scalar_one() == 2


def test_the_database_refuses_a_duplicate_url_even_without_the_check(
    session: Session, fixture_source: None
) -> None:
    """The pre-check reports duplicates; the constraint is what survives a race."""
    del fixture_source
    store = ContentStore(session)
    source_id = _source_id(session)
    store.upsert(_news_item(), source_id=source_id)  # type: ignore[arg-type]
    session.commit()

    with pytest.raises(Exception, match="content_items_canonical_url_key_idx"):
        session.execute(
            text(
                "INSERT INTO public.content_items "
                "(source_id, source_item_id, content_kind, canonical_url_key, "
                " observed_at, content_hash) "
                "VALUES (:source_id, 'racing-insert', 'news_article', "
                " 'example.test/story', now(), repeat('a', 64))"
            ),
            {"source_id": source_id},
        )
        session.commit()
    session.rollback()


def test_permitted_original_text_is_encrypted_when_a_key_is_configured(
    session: Session, fixture_source: None
) -> None:
    """B-S12.1. Stored separately from the normalized model text."""
    del fixture_source
    cipher = ContentCipher(b"\x02" * 32)
    store = ContentStore(session, cipher=cipher)

    stored = store.upsert(
        _news_item(original_text="the exact original wording"),
        source_id=_source_id(session),  # type: ignore[arg-type]
    )
    session.commit()

    item = session.get_one(ContentItem, stored.content_item_id)
    assert item.text_ciphertext is not None
    assert b"exact original wording" not in item.text_ciphertext
    assert cipher.decrypt(item.text_ciphertext) == "the exact original wording"
    assert item.normalized_text == "the exact original wording"


def test_without_a_key_the_original_is_not_retained_as_plaintext(
    session: Session, fixture_source: None
) -> None:
    """Writing plaintext into a column called `text_ciphertext` would mislead
    every later reader, so nothing is written at all."""
    del fixture_source
    store = ContentStore(session)

    stored = store.upsert(
        _news_item(original_text="the exact original wording"),
        source_id=_source_id(session),  # type: ignore[arg-type]
    )
    session.commit()

    item = session.get_one(ContentItem, stored.content_item_id)
    assert item.text_ciphertext is None
