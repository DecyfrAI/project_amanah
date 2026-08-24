"""The reporting assistant has no way to reach a platform (B-S18.6, FR-TOS-006).

`spec.md` forbids submitting a report, calling a platform reporting API, sending
mail, or claiming a platform received anything. The strongest way to hold that is
structurally: the modules that prepare a report import nothing that can open a
socket, and this test fails the moment one does.

It reads the source rather than the imported module because that is what catches
a deferred import inside a function — the shape a "just this once" network call
usually takes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPORTING = Path(__file__).resolve().parents[2] / "src" / "amanah" / "reporting"

#: Anything that can open a connection or hand a message to something that will.
FORBIDDEN_MODULES = frozenset(
    {
        "aiohttp",
        "asyncio",
        "email",
        "ftplib",
        "http",
        "httpx",
        "requests",
        "smtplib",
        "socket",
        "ssl",
        "subprocess",
        "urllib",
        "urllib3",
        "webbrowser",
    }
)

#: The project's own outbound-request modules. Reporting must not reach these
#: either: they are safe *for retrieval*, and retrieval is not what this does.
FORBIDDEN_PROJECT_MODULES = frozenset(
    {
        "amanah.ingestion.http",
        "amanah.ingestion.urls.safe_fetch",
    }
)


def _imported_names(path: Path) -> set[str]:
    """Every module named by an import anywhere in the file, nested ones included."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", sorted(REPORTING.glob("*.py")), ids=lambda path: path.name)
def test_no_reporting_module_can_reach_the_network(path: Path) -> None:
    imported = _imported_names(path)
    roots = {name.split(".")[0] for name in imported}

    assert not (roots & FORBIDDEN_MODULES), (
        f"{path.name} imports {sorted(roots & FORBIDDEN_MODULES)}"
    )
    assert not (imported & FORBIDDEN_PROJECT_MODULES)


def test_the_guard_would_notice_a_network_import(tmp_path: Path) -> None:
    """A test that cannot fail is worth nothing, so prove this one can."""
    offender = tmp_path / "offender.py"
    offender.write_text("def send():\n    import httpx\n", encoding="utf-8")

    roots = {name.split(".")[0] for name in _imported_names(offender)}

    assert roots & FORBIDDEN_MODULES
