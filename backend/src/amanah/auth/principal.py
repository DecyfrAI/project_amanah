"""The authenticated caller and the role ordering used for authorization."""

from dataclasses import dataclass
from uuid import UUID

from amanah.domain.enums import Role

#: Least privilege first. A role satisfies a requirement when its rank is at
#: least the required rank, so administrators inherit reviewer access.
_ROLE_RANK: dict[Role, int] = {
    Role.registered_user: 0,
    Role.reviewer: 1,
    Role.administrator: 2,
}


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """A caller whose access token this service verified.

    Only the identifier and role are carried. Profile data lives behind its own
    authorized read, and the raw token is never retained.
    """

    user_id: UUID
    role: Role


def satisfies_role(actual: Role, required: Role) -> bool:
    """Whether `actual` grants at least the privileges of `required`."""
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]
