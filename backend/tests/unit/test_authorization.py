"""Role and ownership boundaries (B-S4.4, B-S4.5)."""

from uuid import uuid4

import pytest

from amanah.api.dependencies import ensure_resource_owner
from amanah.api.errors import PermissionDeniedError
from amanah.auth.principal import AuthenticatedUser, satisfies_role
from amanah.domain.enums import Role


@pytest.mark.parametrize(
    ("actual", "required", "expected"),
    [
        (Role.registered_user, Role.registered_user, True),
        (Role.registered_user, Role.reviewer, False),
        (Role.registered_user, Role.administrator, False),
        (Role.reviewer, Role.registered_user, True),
        (Role.reviewer, Role.reviewer, True),
        (Role.reviewer, Role.administrator, False),
        (Role.administrator, Role.reviewer, True),
        (Role.administrator, Role.administrator, True),
    ],
)
def test_role_hierarchy(actual: Role, required: Role, expected: bool) -> None:
    assert satisfies_role(actual, required) is expected


def test_owner_may_read_their_own_resource() -> None:
    owner_id = uuid4()
    user = AuthenticatedUser(user_id=owner_id, role=Role.registered_user)

    ensure_resource_owner(user, owner_id)


def test_another_user_is_denied() -> None:
    user = AuthenticatedUser(user_id=uuid4(), role=Role.registered_user)

    with pytest.raises(PermissionDeniedError):
        ensure_resource_owner(user, uuid4())


@pytest.mark.parametrize("role", [Role.reviewer, Role.administrator])
def test_privileged_roles_do_not_bypass_ownership(role: Role) -> None:
    """Reviewers and administrators reach other users' records through their own
    queues, never through an owner-scoped read."""
    user = AuthenticatedUser(user_id=uuid4(), role=role)

    with pytest.raises(PermissionDeniedError):
        ensure_resource_owner(user, uuid4())
