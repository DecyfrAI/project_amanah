"""Repository security scans reject server secrets in browser artifacts."""

from pathlib import Path

from scripts.bundle_scan import scan


def test_bundle_scan_accepts_an_ordinary_asset(tmp_path: Path) -> None:
    (tmp_path / "app.js").write_text("console.log('hello')", encoding="utf-8")

    assert scan(tmp_path) == []


def test_bundle_scan_rejects_server_only_secret_names(tmp_path: Path) -> None:
    (tmp_path / "app.js").write_text("const key='GEMINI_API_KEY'", encoding="utf-8")

    assert scan(tmp_path) == ["app.js"]
