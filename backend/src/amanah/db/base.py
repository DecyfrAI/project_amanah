"""Declarative base and the conventions every table in this service follows.

The naming convention is declared once here so constraint and index names are
generated, not hand-written. `rules/database.md` requires `<table>_<columns>_idx`
for indexes and `<table>_<columns>_<type>` for constraints; a migration that
drops a constraint therefore names it the same way the model does.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, func, text
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

#: Constraint naming, applied to every table through the shared metadata.
NAMING_CONVENTION = {
    "ix": "%(table_name)s_%(column_0_N_name)s_idx",
    "uq": "%(table_name)s_%(column_0_N_name)s_unique",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

#: Product tables live in `public` because that is the schema Supabase exposes
#: through PostgREST; keeping them anywhere else would leave the exposed schema
#: outside the row-level-security boundary this service defines.
SCHEMA = "public"


class Base(DeclarativeBase):
    """Base class for every mapped table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION, schema=SCHEMA)


#: Externally visible identifier. `rules/database.md` prefers `bigint IDENTITY`
#: for single-database systems but requires opaque UUIDs for identifiers exposed
#: outside the database; every identifier here appears in a URL or an API
#: response, and `spec.md` section 14 mandates UUID primary keys, so UUID wins.
#: Generation stays in Postgres so a row written by a migration, a job, or the
#: API is keyed the same way. See ADR 0003.
UuidPrimaryKey = Annotated[
    uuid.UUID,
    mapped_column(
        POSTGRES_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
]

UuidColumn = Annotated[uuid.UUID, mapped_column(POSTGRES_UUID(as_uuid=True))]

#: Every timestamp is `timestamptz` and stored in UTC.
CreatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now()),
]
UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
]
Timestamp = Annotated[datetime, mapped_column(DateTime(timezone=True))]
