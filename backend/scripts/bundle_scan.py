"""Fail when a browser bundle contains a server-only secret name or token shape."""

from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN = (
    re.compile(rb"SUPABASE_SERVICE_ROLE_KEY"),
    re.compile(rb"SUPABASE_JWT_SECRET"),
    re.compile(rb"GEMINI_API_KEY"),
    re.compile(rb"CONTENT_ENCRYPTION_KEY"),
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
)


def scan(directory: Path) -> list[str]:
    if not directory.is_dir():
        return ["browser bundle directory is missing"]
    problems: list[str] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        payload = path.read_bytes()
        if any(pattern.search(payload) for pattern in FORBIDDEN):
            problems.append(path.relative_to(directory).as_posix())
    return problems


def main() -> int:
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("apps/web/dist")
    problems = scan(directory)
    if problems:
        print("Browser bundle security scan failed: " + ", ".join(problems))
        return 1
    print("Browser bundle security scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
