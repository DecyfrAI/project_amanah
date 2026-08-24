"""Persistence and version resolution for immutable research reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from amanah.api.schemas.filters import ItemFilters
from amanah.db.models.resources import ResearchReport, ResearchReportAuditEvent
from amanah.db.repositories.items import build_filter_conditions
from amanah.db.views import authenticated_items, authenticated_research_reports


class ResearchReportRepository:
    """Create snapshots and read only through the authorized projection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_data_version(self, filters: ItemFilters) -> str:
        """Fingerprint the exact visible aggregate state under the filters."""
        table = authenticated_items
        statement = select(
            table.c.id,
            table.c.prediction_id,
            table.c.observed_at,
            table.c.inferred_at,
            table.c.relevance,
            table.c.stance,
            table.c.review_state,
            table.c.source_name,
        ).order_by(table.c.id.asc())
        for condition in build_filter_conditions(table, filters):
            statement = statement.where(condition)
        digest = hashlib.sha256()
        for row in self._session.execute(statement):
            state = {
                "id": str(row.id),
                "prediction_id": str(row.prediction_id) if row.prediction_id else None,
                "observed_at": row.observed_at.isoformat(),
                "inferred_at": row.inferred_at.isoformat() if row.inferred_at else None,
                "relevance": row.relevance,
                "stance": row.stance,
                "review_state": row.review_state,
                "source_name": row.source_name,
            }
            digest.update(json.dumps(state, sort_keys=True, separators=(",", ":")).encode())
            digest.update(b"\n")
        return f"data-{digest.hexdigest()[:32]}"

    def create_report(self, report: ResearchReport) -> None:
        self._session.add(report)
        self._session.flush()

    def get_report(self, report_id: UUID) -> Row[Any] | None:
        statement = select(authenticated_research_reports).where(
            authenticated_research_reports.c.id == report_id
        )
        return self._session.execute(statement).one_or_none()

    def add_audit_event(
        self, *, report_id: UUID, actor_user_id: UUID, action: str, request_id: str
    ) -> None:
        self._session.add(
            ResearchReportAuditEvent(
                research_report_id=report_id,
                actor_user_id=actor_user_id,
                action=action,
                request_id=request_id,
            )
        )

    def commit(self) -> None:
        self._session.commit()
