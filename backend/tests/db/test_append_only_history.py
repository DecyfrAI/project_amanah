"""History that cannot be rewritten (B-S3.5, B-S3.8).

Predictions and review and contribution events are the project's record of what
the model said and what people decided. A reviewer correction appends; it never
edits. A ready report snapshot is frozen. These tests try to break each rule
directly against the database, because that is where the guarantee lives.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from tests.db import factories

#: The triggers raise `restrict_violation`, which SQLAlchemy maps to this class.
REJECTED = IntegrityError


def _item_with_prediction(connection: Connection) -> tuple[str, str]:
    source_id = factories.insert_source(connection)
    item_id = factories.insert_content_item(connection, source_id=source_id)
    prediction_id = factories.insert_prediction(connection, content_item_id=item_id)
    return str(item_id), str(prediction_id)


def test_a_prediction_cannot_be_updated(connection: Connection) -> None:
    _, prediction_id = _item_with_prediction(connection)

    with pytest.raises(REJECTED, match="append_only_violation"):
        connection.execute(
            text("UPDATE public.predictions SET score = 0.1 WHERE id = :id"),
            {"id": prediction_id},
        )


def test_a_prediction_cannot_be_deleted(connection: Connection) -> None:
    _, prediction_id = _item_with_prediction(connection)

    with pytest.raises(REJECTED, match="append_only_violation"):
        connection.execute(
            text("DELETE FROM public.predictions WHERE id = :id"), {"id": prediction_id}
        )


def test_a_review_event_cannot_be_rewritten(connection: Connection) -> None:
    item_id, prediction_id = _item_with_prediction(connection)
    task_id = connection.execute(
        text(
            "INSERT INTO public.review_tasks (content_item_id, prediction_id, task_type, reason) "
            "VALUES (:item_id, :prediction_id, 'dispute', 'Synthetic reason') RETURNING id"
        ),
        {"item_id": item_id, "prediction_id": prediction_id},
    ).scalar_one()
    event_id = connection.execute(
        text(
            "INSERT INTO public.review_events (review_task_id, reviewer_id, decision, note) "
            "VALUES (:task_id, :reviewer_id, 'confirmed', 'Synthetic note') RETURNING id"
        ),
        {"task_id": task_id, "reviewer_id": uuid4()},
    ).scalar_one()

    with pytest.raises(REJECTED, match="append_only_violation"):
        connection.execute(
            text("UPDATE public.review_events SET decision = 'rejected' WHERE id = :id"),
            {"id": event_id},
        )


def test_a_correction_must_say_what_it_corrects_to(connection: Connection) -> None:
    """A `corrected` decision without labels would leave the projection guessing."""
    item_id, prediction_id = _item_with_prediction(connection)
    task_id = connection.execute(
        text(
            "INSERT INTO public.review_tasks (content_item_id, prediction_id, task_type, reason) "
            "VALUES (:item_id, :prediction_id, 'dispute', 'Synthetic reason') RETURNING id"
        ),
        {"item_id": item_id, "prediction_id": prediction_id},
    ).scalar_one()

    with pytest.raises(Exception, match="corrected_labels_match_decision"):
        connection.execute(
            text(
                "INSERT INTO public.review_events (review_task_id, reviewer_id, decision) "
                "VALUES (:task_id, :reviewer_id, 'corrected')"
            ),
            {"task_id": task_id, "reviewer_id": uuid4()},
        )


def test_a_contribution_event_cannot_be_deleted(connection: Connection) -> None:
    """A user's timeline is what happened, not a summary someone can tidy."""
    event_id = factories.insert_contribution_event(connection, user_id=uuid4())

    with pytest.raises(REJECTED, match="append_only_violation"):
        connection.execute(
            text("DELETE FROM public.contribution_events WHERE id = :id"), {"id": event_id}
        )


def test_a_ready_report_snapshot_is_immutable(connection: Connection) -> None:
    report_id = _insert_report(connection, status="ready")

    with pytest.raises(REJECTED, match="immutable_snapshot_violation"):
        connection.execute(
            text("UPDATE public.research_reports SET data_version = 'tampered' WHERE id = :id"),
            {"id": report_id},
        )


def test_a_ready_report_snapshot_cannot_be_deleted(connection: Connection) -> None:
    report_id = _insert_report(connection, status="ready")

    with pytest.raises(REJECTED, match="immutable_snapshot_violation"):
        connection.execute(
            text("DELETE FROM public.research_reports WHERE id = :id"), {"id": report_id}
        )


def test_a_pending_report_may_still_be_completed(connection: Connection) -> None:
    """Immutability starts at `ready`. A snapshot still being generated is not
    frozen, or it could never finish."""
    report_id = _insert_report(connection, status="pending")

    connection.execute(
        text(
            "UPDATE public.research_reports SET status = 'ready', completed_at = now() "
            "WHERE id = :id"
        ),
        {"id": report_id},
    )

    status = connection.execute(
        text("SELECT status FROM public.research_reports WHERE id = :id"), {"id": report_id}
    ).scalar_one()
    assert status == "ready"


def _insert_report(connection: Connection, *, status: str) -> str:
    completed_at = "now()" if status == "ready" else "NULL"
    return str(
        connection.execute(
            text(
                "INSERT INTO public.research_reports "
                "(user_id, filter_hash, filters, data_version, methodology_version, status, "
                " completed_at) "
                "VALUES (:user_id, :filter_hash, '{}'::jsonb, 'd1', 'm1', "
                f"CAST(:status AS research_report_status), {completed_at}) RETURNING id"
            ),
            {"user_id": uuid4(), "filter_hash": "0" * 64, "status": status},
        ).scalar_one()
    )
