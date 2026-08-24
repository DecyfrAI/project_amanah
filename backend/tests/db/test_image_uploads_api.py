"""Authenticated image upload and its classification (B-S28).

The subject is the boundary: who may upload, who may read what they uploaded,
what the server does to the bytes before storing them, and what it refuses. The
storage provider is stubbed at the HTTP transport — the real signing, cleaning,
ownership, and persistence all run.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine, text

from amanah.main import create_app
from amanah.settings import Settings
from tests.conftest import make_access_token, make_settings

UPLOADS = "/v1/image-uploads"
CLASSIFICATIONS = "/v1/image-classifications"

OWNER = UUID("11111111-1111-1111-1111-111111111111")
STRANGER = UUID("22222222-2222-2222-2222-222222222222")

STORAGE_KEY = "sb_secret_test_only"
BUCKET = "amanah-test-media"


def _png(width: int = 12, height: int = 8, colour: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_with_exif() -> bytes:
    image = Image.new("RGB", (16, 16), (200, 100, 50))
    exif = image.getexif()
    exif[0x010F] = "ACME Phone"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


class _StorageStub:
    """Stands in for Supabase Storage, recording what was written."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if "/object/sign/" in path:
            key = path.split(f"/object/sign/{BUCKET}/", 1)[-1]
            return httpx2.Response(
                200, json={"signedURL": f"/object/sign/{BUCKET}/{key}?token=stub"}
            )
        key = path.split(f"/object/{BUCKET}/", 1)[-1]
        if request.method == "POST":
            self.objects[key] = request.content
            return httpx2.Response(200, json={"Key": key})
        if request.method == "DELETE":
            self.deleted.append(key)
            self.objects.pop(key, None)
            return httpx2.Response(200, json={})
        if request.method == "GET":
            payload = self.objects.get(key)
            if payload is None:
                return httpx2.Response(404)
            return httpx2.Response(200, content=payload)
        return httpx2.Response(405)


@pytest.fixture
def storage() -> _StorageStub:
    return _StorageStub()


@pytest.fixture(autouse=True)
def _stub_transport(monkeypatch: pytest.MonkeyPatch, storage: _StorageStub) -> None:
    """Route every outbound storage call to the stub."""
    transport = httpx2.MockTransport(storage.handler)

    @contextmanager
    def build(_limits: Any) -> Iterator[httpx2.Client]:
        client = httpx2.Client(transport=transport, follow_redirects=False)
        try:
            yield client
        finally:
            client.close()

    for module in ("amanah.storage.object_store", "amanah.storage.signed_urls"):
        monkeypatch.setattr(f"{module}.http_client", build)


@pytest.fixture
def api_settings(database_url: str) -> Settings:
    return make_settings(
        database_url=database_url,
        supabase_storage_secret_key=STORAGE_KEY,
        supabase_storage_bucket=BUCKET,
    )


@contextmanager
def signed_in(settings: Settings, user_id: UUID) -> Iterator[TestClient]:
    """A signed-in client. Entered as a context so the lifespan opens the pool."""
    client = TestClient(create_app(settings))
    client.headers["Authorization"] = f"Bearer {make_access_token(settings, user_id=user_id)}"
    with client:
        yield client


@pytest.fixture
def owner(api_settings: Settings) -> Iterator[TestClient]:
    with signed_in(api_settings, OWNER) as client:
        yield client


@pytest.fixture
def stranger(api_settings: Settings) -> Iterator[TestClient]:
    with signed_in(api_settings, STRANGER) as client:
        yield client


def _upload(client: TestClient, payload: bytes, *, name: str = "example.png") -> Any:
    return client.post(UPLOADS, files={"file": (name, payload, "image/png")})


# --- who may upload ---------------------------------------------------------


def test_an_anonymous_caller_cannot_upload(api_settings: Settings) -> None:
    with TestClient(create_app(api_settings)) as anonymous:
        response = anonymous.post(UPLOADS, files={"file": ("x.png", _png(), "image/png")})

    assert response.status_code == 401


def test_an_upload_returns_an_identifier_and_never_the_storage_path(owner: TestClient) -> None:
    response = _upload(owner, _png())

    assert response.status_code == 201
    body = response.json()
    assert body["upload_id"]
    assert body["is_new"] is True
    for forbidden in ("storage_path", "storage_bucket", "filename"):
        assert forbidden not in body
    # The link is short-lived and minted per request, never a durable location.
    assert "token=" in body["image_url"]
    assert body["image_url_expires_at"]


# --- what the server does to the bytes --------------------------------------


def test_metadata_is_removed_before_the_bytes_are_stored(
    owner: TestClient, storage: _StorageStub
) -> None:
    response = owner.post(UPLOADS, files={"file": ("holiday.jpg", _jpeg_with_exif(), "image/jpeg")})

    assert response.status_code == 201
    stored = next(iter(storage.objects.values()))
    assert b"ACME Phone" not in stored
    assert not Image.open(io.BytesIO(stored)).getexif()


def test_the_stored_key_is_server_generated_and_owner_scoped(
    owner: TestClient, storage: _StorageStub
) -> None:
    """Nothing the caller sent contributes to the path."""
    _upload(owner, _png(), name="../../escape.png")

    key = next(iter(storage.objects))
    assert key.startswith(f"user-images/{OWNER}/")
    assert "escape" not in key
    assert ".." not in key


def test_the_declared_content_type_does_not_decide_the_stored_type(owner: TestClient) -> None:
    """A PNG announced as a JPEG is stored as what it actually is."""
    response = owner.post(UPLOADS, files={"file": ("a.jpg", _png(), "image/jpeg")})

    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


# --- what the server refuses ------------------------------------------------


def test_a_file_that_is_not_an_image_is_refused(owner: TestClient) -> None:
    response = owner.post(UPLOADS, files={"file": ("x.png", b"not an image", "image/png")})

    assert response.status_code == 422
    assert "image" in response.json()["error"]["message"].lower()


def test_an_oversized_upload_is_refused(database_url: str) -> None:
    settings = make_settings(
        database_url=database_url,
        supabase_storage_secret_key=STORAGE_KEY,
        supabase_storage_bucket=BUCKET,
        image_upload_max_bytes=1024,
    )

    with signed_in(settings, OWNER) as client:
        response = client.post(UPLOADS, files={"file": ("big.png", _png(400, 400), "image/png")})

    assert response.status_code == 413


def test_a_refusal_describes_the_limit_rather_than_the_file(owner: TestClient) -> None:
    """The endpoint must not become an oracle about what it detected."""
    message = owner.post(
        UPLOADS, files={"file": ("x.gif", b"GIF89a nonsense", "image/gif")}
    ).json()["error"]["message"]

    assert "nonsense" not in message
    assert "x.gif" not in message


# --- idempotency and ownership ----------------------------------------------


def test_uploading_the_same_picture_twice_converges(
    owner: TestClient, storage: _StorageStub
) -> None:
    payload = _png()

    first = _upload(owner, payload).json()
    second = _upload(owner, payload).json()

    assert first["upload_id"] == second["upload_id"]
    assert second["is_new"] is False
    assert len(storage.objects) == 1


def test_two_owners_uploading_the_same_picture_get_separate_rows(
    owner: TestClient, stranger: TestClient
) -> None:
    payload = _png()

    mine = _upload(owner, payload).json()
    theirs = _upload(stranger, payload).json()

    assert mine["upload_id"] != theirs["upload_id"]


def test_another_user_cannot_classify_someone_elses_upload(
    owner: TestClient, stranger: TestClient
) -> None:
    owned = _upload(owner, _png()).json()["upload_id"]

    response = stranger.post(CLASSIFICATIONS, json={"upload_id": owned})

    # The same answer a missing row gives, so this cannot enumerate identifiers.
    assert response.status_code == 404


def test_classification_needs_exactly_one_subject(owner: TestClient) -> None:
    assert owner.post(CLASSIFICATIONS, json={}).status_code == 400

    both = owner.post(CLASSIFICATIONS, json={"example_id": str(uuid4()), "upload_id": str(uuid4())})
    assert both.status_code == 400


# --- the transfer gate ------------------------------------------------------


def test_classification_is_refused_while_third_party_transfer_is_disabled(
    owner: TestClient,
) -> None:
    """The default: an upload is not sent to the provider without an opt-in."""
    upload_id = _upload(owner, _png()).json()["upload_id"]

    response = owner.post(CLASSIFICATIONS, json={"upload_id": upload_id})

    assert response.status_code == 503
    assert "unavailable" in response.json()["error"]["message"].lower()


# --- what a row keeps -------------------------------------------------------


def test_the_row_stores_metadata_and_a_path_but_no_bytes(owner: TestClient, engine: Engine) -> None:
    _upload(owner, _png(12, 8))

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT owner_user_id, storage_path, sha256, mime_type, byte_size, "
                "pixel_width, pixel_height, retention_expires_at "
                "FROM public.image_uploads"
            )
        ).one()

    assert row.owner_user_id == OWNER
    assert row.storage_path.startswith("user-images/")
    assert len(row.sha256) == 64
    assert (row.pixel_width, row.pixel_height) == (12, 8)
    assert row.byte_size > 0
    # Retention is recorded at write time rather than inferred later.
    assert row.retention_expires_at is not None


def test_the_upload_table_has_no_column_for_bytes_or_a_filename(engine: Engine) -> None:
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'image_uploads'"
                )
            ).all()
        }

    for forbidden in ("bytes", "payload", "data", "content", "filename", "original_name"):
        assert forbidden not in columns
