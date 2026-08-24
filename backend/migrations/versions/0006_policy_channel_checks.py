"""Relax the FR-TOS-010 channel constraints to apply at publication.

`0005` required a reporting URL on every `official_form` row and an address on
every `allowlist_email` row, whatever the row's status. That is the wrong moment
to demand them: a `draft` entry exists precisely because a reviewer has not
finished it yet, and the catalogue's own rule is already "only a reviewed,
published entry may be offered to a user".

So the completeness check moves to publication, matching `published_requires_review`
beside it, and a second pair of checks keeps the two channels from being confused
at any status — a form platform never carries an address, and an email platform
never carries a form. The matcher reads published rows only, so nothing a user can
be shown loses a guarantee.

Written as a new revision rather than an edit to `0005`, which has already been
applied; a migration file has to keep describing what actually ran.

Revision ID: 0006_policy_channel_checks
Revises: 0005_contributions_discussion
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_policy_channel_checks"
down_revision: str | None = "0005_contributions_discussion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: `(name, condition)` as `0005` left them, so the downgrade restores exactly
#: the constraints this revision replaces.
_STRICT_CHECKS = (
    (
        "form_platform_has_report_url",
        "(recipient_kind = 'official_form') = (official_report_url IS NOT NULL)",
    ),
    (
        "email_platform_has_allowlisted_address",
        "(recipient_kind = 'allowlist_email') = (report_email IS NOT NULL)",
    ),
)

_RELAXED_CHECKS = (
    # A channel never carries the other channel's destination, at any status.
    (
        "form_platform_has_report_url",
        "recipient_kind <> 'official_form' OR report_email IS NULL",
    ),
    (
        "email_platform_has_allowlisted_address",
        "recipient_kind <> 'allowlist_email' OR official_report_url IS NULL",
    ),
    # A published entry is complete: whichever destination its channel needs is
    # present, because a user may be shown it.
    (
        "published_policy_names_its_destination",
        "status <> 'published' "
        "OR (recipient_kind = 'official_form' AND official_report_url IS NOT NULL) "
        "OR (recipient_kind = 'allowlist_email' AND report_email IS NOT NULL)",
    ),
)


def upgrade() -> None:
    for name, _condition in _STRICT_CHECKS:
        op.drop_constraint(f"platform_policies_{name}_check", "platform_policies", schema="public")
    for name, condition in _RELAXED_CHECKS:
        op.create_check_constraint(name, "platform_policies", condition, schema="public")


def downgrade() -> None:
    for name, _condition in reversed(_RELAXED_CHECKS):
        op.drop_constraint(f"platform_policies_{name}_check", "platform_policies", schema="public")
    for name, condition in _STRICT_CHECKS:
        op.create_check_constraint(name, "platform_policies", condition, schema="public")
