"""Snapshot insights, invite-only discussion, captures, and profile (B-S27).

Every decision ADR 0004 records is asserted here as a behaviour: a snapshot
cannot be edited, participation is by invitation, retraction leaves the row,
reacting twice does not stack, and there is no free-floating board and no
per-author ranking anywhere in the schema or the contract.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from amanah.discussion.service import RETRACTED_BODY
from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import make_access_token, make_settings
from tests.db import factories

INSIGHTS = "/v1/insights"
CAPTURES = "/v1/captures"

AUTHOR = UUID("88888888-8888-8888-8888-888888888888")
INVITED = UUID("99999999-9999-9999-9999-999999999999")
UNINVITED = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ADMINISTRATOR = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

FILTER_HASH = "a1b2c3d4e5f60718"

SNAPSHOT = {
    "title": "Rate in the monitored sample",
    "claim": "12 of 400 monitored items were classified likely anti-Muslim.",
    "metric": "likely_anti_muslim_rate",
    "numerator": 12,
    "denominator": 400,
    "window_start": "2026-06-01T00:00:00Z",
    "window_end": "2026-06-30T00:00:00Z",
    "figure_label": "Daily rate",
    "filter_hash": FILTER_HASH,
    "explorer_href": "/app/explorer?from=2026-06-01",
    "source_keys": ["fixtures"],
    "items_observed": 400,
    "items_relevant": 120,
}

CAPTURE = {
    "alt_text": "Daily rate of likely anti-Muslim items in the monitored sample.",
    "image_source": "/media/figures/daily-rate.png",
    "filter_hash": FILTER_HASH,
    "explorer_href": "/app/explorer?from=2026-06-01",
}


@pytest.fixture
def api_settings(database_url: str) -> Settings:
    return make_settings(database_url=database_url)


def _client_for(settings: Settings, user_id: UUID) -> TestClient:
    client = TestClient(create_app(settings))
    client.headers["Authorization"] = f"Bearer {make_access_token(settings, user_id=user_id)}"
    return client


@pytest.fixture
def invitations(engine: Engine) -> None:
    """`AUTHOR` and `INVITED` may take part; `UNINVITED` deliberately may not."""
    with engine.begin() as connection:
        for user_id in (AUTHOR, INVITED):
            factories.insert_discussion_participant(
                connection, user_id=user_id, granted_by=ADMINISTRATOR
            )


@pytest.fixture
def author(api_settings: Settings, invitations: None) -> Iterator[TestClient]:
    with _client_for(api_settings, AUTHOR) as client:
        yield client


@pytest.fixture
def colleague(api_settings: Settings, invitations: None) -> Iterator[TestClient]:
    with _client_for(api_settings, INVITED) as client:
        yield client


@pytest.fixture
def outsider(api_settings: Settings, invitations: None) -> Iterator[TestClient]:
    with _client_for(api_settings, UNINVITED) as client:
        yield client


@pytest.fixture
def insight(author: TestClient) -> dict[str, Any]:
    response = author.post(INSIGHTS, json=SNAPSHOT)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()["insight"]
    return body


# -- snapshots ------------------------------------------------------------


def test_a_snapshot_freezes_its_counts_and_filter_state(insight: dict[str, Any]) -> None:
    """ADR 0004: the claim travels with the numbers that produced it, so a later
    reader can check it rather than believe it."""
    assert insight["numerator"] == 12
    assert insight["denominator"] == 400
    assert insight["value"] == pytest.approx(12 / 400)
    assert insight["filter_hash"] == FILTER_HASH
    assert insight["explorer_href"] == "/app/explorer?from=2026-06-01"


def test_a_snapshot_cannot_be_edited_after_creation(
    insight: dict[str, Any], engine: Engine
) -> None:
    """The whole point of freezing a figure is that the numbers stay the ones the
    author saw, so the table refuses an update outright."""
    with engine.begin() as connection, pytest.raises(Exception, match="immutable"):
        connection.execute(
            text("UPDATE public.snapshot_insights SET numerator = 999 WHERE id = :id"),
            {"id": insight["id"]},
        )


def test_a_snapshot_with_no_observations_reports_a_gap_not_a_zero(
    author: TestClient,
) -> None:
    """A zero denominator means nothing was observed. Publishing `0.0` would read
    as "no anti-Muslim content found", which the data does not support."""
    empty = {
        **SNAPSHOT,
        "numerator": 0,
        "denominator": 0,
        "items_observed": 0,
        "items_relevant": 0,
    }

    body = author.post(INSIGHTS, json=empty).json()["insight"]

    assert body["value"] is None


def test_creating_a_snapshot_is_open_to_any_signed_in_viewer(
    outsider: TestClient,
) -> None:
    """ADR 0004 gates *participation*, not the act of recording a figure the
    dashboard already showed you."""
    assert outsider.post(INSIGHTS, json=SNAPSHOT).status_code == 201


def test_an_anonymous_caller_reaches_no_insight_route(api_settings: Settings) -> None:
    with TestClient(create_app(api_settings)) as client:
        assert client.get(INSIGHTS).status_code == 401
        assert client.post(INSIGHTS, json=SNAPSHOT).status_code == 401
        assert client.post(CAPTURES, json=CAPTURE).status_code == 401
        assert client.get(f"{INSIGHTS}/{uuid4()}/discussion").status_code == 401
        assert client.get("/v1/me/posts").status_code == 401


def test_the_insight_list_is_newest_first(author: TestClient) -> None:
    author.post(INSIGHTS, json={**SNAPSHOT, "title": "First"})
    author.post(INSIGHTS, json={**SNAPSHOT, "title": "Second"})

    page = author.get(INSIGHTS).json()

    times = [row["created_at"] for row in page["items"]]
    assert times == sorted(times, reverse=True)


# -- participation --------------------------------------------------------


def test_an_uninvited_viewer_may_read_a_thread_but_not_post(
    author: TestClient, outsider: TestClient, insight: dict[str, Any]
) -> None:
    """Invite-only is about adding to a conversation, not about seeing it: a
    colleague can follow the reasoning before they can join."""
    thread = outsider.get(f"{INSIGHTS}/{insight['id']}/discussion")

    assert thread.status_code == 200
    assert thread.json()["can_participate"] is False

    refused = outsider.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "Let me in."}
    )
    assert refused.status_code == 403


def test_an_uninvited_viewer_cannot_capture_or_react(
    author: TestClient, outsider: TestClient, insight: dict[str, Any]
) -> None:
    post_id = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]["id"]

    assert outsider.post(CAPTURES, json=CAPTURE).status_code == 403
    assert (
        outsider.post(f"/v1/posts/{post_id}/reactions", json={"kind": "useful"}).status_code == 403
    )


def test_an_invited_colleague_may_post(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    response = colleague.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts",
        json={"body": "The denominator here is the monitored sample, not a population."},
    )

    assert response.status_code == 201
    assert response.json()["post"]["author_id"] == str(INVITED)


# -- notes, captures, retraction ------------------------------------------


def test_a_note_may_carry_the_authors_own_first_party_capture(
    author: TestClient, insight: dict[str, Any]
) -> None:
    capture = author.post(CAPTURES, json=CAPTURE).json()["capture"]

    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts",
        json={"body": "Here is the figure.", "capture_id": capture["id"]},
    ).json()["post"]

    assert post["capture"]["id"] == capture["id"]
    assert post["capture"]["alt_text"] == CAPTURE["alt_text"]


def test_a_note_cannot_borrow_someone_elses_capture(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    """Otherwise a note could show a figure whose filters its author never saw."""
    capture = author.post(CAPTURES, json=CAPTURE).json()["capture"]

    response = colleague.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts",
        json={"body": "Borrowing this.", "capture_id": capture["id"]},
    )

    assert response.status_code == 404


def test_retracting_leaves_the_row_and_removes_the_capture(
    author: TestClient, insight: dict[str, Any], engine: Engine
) -> None:
    """ADR 0004: nothing is silently deleted. The turn stays visible as one that
    was taken and withdrawn."""
    capture = author.post(CAPTURES, json=CAPTURE).json()["capture"]
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts",
        json={"body": "Something I would rather withdraw.", "capture_id": capture["id"]},
    ).json()["post"]

    retracted = author.post(f"/v1/posts/{post['id']}/retract").json()["post"]

    assert retracted["retracted_at"] is not None
    assert retracted["body"] == RETRACTED_BODY
    assert retracted["capture"] is None
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT count(*) FROM public.discussion_posts")).scalar_one()
    assert rows == 1, "the row must survive the retraction"


def test_a_retracted_note_keeps_its_place_in_the_thread(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    first = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "First note."}
    ).json()["post"]
    colleague.post(f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "Second note."})
    author.post(f"/v1/posts/{first['id']}/retract")

    thread = author.get(f"{INSIGHTS}/{insight['id']}/discussion").json()

    assert thread["posts"][0]["id"] == first["id"]
    assert thread["posts"][0]["body"] == RETRACTED_BODY
    assert thread["posts"][1]["body"] == "Second note."


def test_retracting_twice_does_not_restamp_the_withdrawal(
    author: TestClient, insight: dict[str, Any]
) -> None:
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]

    first = author.post(f"/v1/posts/{post['id']}/retract").json()["post"]
    second = author.post(f"/v1/posts/{post['id']}/retract").json()["post"]

    assert first["retracted_at"] == second["retracted_at"]


def test_only_the_author_may_retract_their_note(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "Mine."}
    ).json()["post"]

    assert colleague.post(f"/v1/posts/{post['id']}/retract").status_code == 404


# -- reactions ------------------------------------------------------------


def test_reacting_twice_replaces_rather_than_stacks(
    author: TestClient, insight: dict[str, Any]
) -> None:
    """The counts are a count of people, so the endpoint is idempotent."""
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]

    author.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "useful"})
    author.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "useful"})
    body = author.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "needs_context"}).json()

    assert body["post"]["reactions"]["useful"] == 0
    assert body["post"]["reactions"]["needs_context"] == 1
    assert body["post"]["reactions"]["viewer"] == "needs_context"


def test_reaction_counts_are_per_post_and_show_only_the_callers_own_choice(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]
    author.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "useful"})
    colleague.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "useful"})

    seen_by_colleague = colleague.get(f"{INSIGHTS}/{insight['id']}/discussion").json()["posts"][0]
    seen_by_outsider = author.get(f"{INSIGHTS}/{insight['id']}/discussion").json()["posts"][0]

    assert seen_by_colleague["reactions"]["useful"] == 2
    assert seen_by_colleague["reactions"]["viewer"] == "useful"
    assert seen_by_outsider["reactions"]["useful"] == 2


def test_a_retracted_note_cannot_be_reacted_to(author: TestClient, insight: dict[str, Any]) -> None:
    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]
    author.post(f"/v1/posts/{post['id']}/retract")

    response = author.post(f"/v1/posts/{post['id']}/reactions", json={"kind": "useful"})

    assert response.status_code == 404


def test_no_projection_can_produce_a_per_author_ranking(engine: Engine) -> None:
    """ADR 0004 forbids reputation. The reaction projection groups by post and
    exposes no author column, so a ranking cannot be assembled from it."""
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'authenticated_post_reactions'"
                )
            ).scalars()
        )

    assert columns == {
        "discussion_post_id",
        "useful_count",
        "needs_context_count",
        "viewer_reaction",
    }


def test_no_discussion_table_carries_a_reputation_column(engine: Engine) -> None:
    with engine.connect() as connection:
        columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('discussion_posts', 'snapshot_insights', 'post_reactions')"
                )
            ).scalars()
        )

    forbidden = {"score", "reputation", "karma", "rank", "author_score", "upvotes"}
    assert not (columns & forbidden)


def test_a_note_always_has_a_parent_insight(engine: Engine) -> None:
    """There is no free-floating board: the column is `NOT NULL` with a foreign
    key, so a post with no insight cannot exist."""
    with engine.connect() as connection:
        nullable = connection.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'discussion_posts' "
                "AND column_name = 'snapshot_insight_id'"
            )
        ).scalar_one()

    assert nullable == "NO"


# -- the caller's own notes -----------------------------------------------


def test_the_caller_sees_only_their_own_notes_with_the_parent_title(
    author: TestClient, colleague: TestClient, insight: dict[str, Any]
) -> None:
    author.post(f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "Mine."})
    colleague.post(f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "Theirs."})

    mine = author.get("/v1/me/posts").json()

    assert [post["body"] for post in mine["items"]] == ["Mine."]
    assert mine["items"][0]["insight_title"] == SNAPSHOT["title"]


# -- profile --------------------------------------------------------------


def test_the_profile_persists_onboarding_and_reports_the_verified_role(
    author: TestClient,
) -> None:
    """B-S27.1. The role is the server's decision from the token, not a value the
    stored row could grant."""
    response = author.patch(
        "/v1/me",
        json={
            "display_name": "Research colleague",
            "onboarding_status": "completed",
            "content_safety_preferences": {"reveal_redacted_text": True},
        },
    )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["display_name"] == "Research colleague"
    assert profile["onboarding_status"] == "completed"
    assert profile["role"] == "registered_user"

    assert author.get("/v1/me").json()["profile"]["onboarding_status"] == "completed"


def test_the_profile_reports_the_role_carried_by_the_verified_token(
    api_settings: Settings,
) -> None:
    """The effective role comes from the token the server verified, so a caller
    signed in as a reviewer is reported as one even with no stored row."""
    reviewer_id = uuid4()
    client = TestClient(create_app(api_settings))
    token = make_access_token(api_settings, user_id=reviewer_id, role="reviewer")
    client.headers["Authorization"] = f"Bearer {token}"

    with client:
        profile = client.get("/v1/me").json()["profile"]

    assert profile == {
        "user_id": str(reviewer_id),
        "role": "reviewer",
        "display_name": None,
        "onboarding_status": "not_started",
        "content_safety_preferences": {},
    }


def test_a_profile_update_cannot_grant_a_role(author: TestClient) -> None:
    response = author.patch("/v1/me", json={"role": "administrator"})

    assert response.status_code == 400
    assert author.get("/v1/me").json()["profile"]["role"] == "registered_user"


def test_a_display_name_appears_on_the_authors_notes(
    author: TestClient, insight: dict[str, Any]
) -> None:
    author.patch("/v1/me", json={"display_name": "Research colleague"})

    post = author.post(
        f"{INSIGHTS}/{insight['id']}/discussion/posts", json={"body": "A note."}
    ).json()["post"]

    assert post["author_display_name"] == "Research colleague"
