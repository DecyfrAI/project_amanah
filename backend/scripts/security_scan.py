"""Deterministic forbidden-file and obvious-secret scan for tracked files."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".parquet", ".pkl", ".pt", ".pth"}
SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
}


def tracked_files() -> tuple[Path, ...]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git executable is required")
    output = subprocess.run(  # noqa: S603 - executable resolved from PATH, arguments fixed
        [git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    return tuple(ROOT / value.decode() for value in output.split(b"\0") if value)


def scan(paths: tuple[Path, ...]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden artifact: {relative}")
        if path.name == ".env":
            problems.append(f"populated environment file: {relative}")
        if not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        payload = path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(payload):
                problems.append(f"possible {label}: {relative}")
    return problems


def main() -> int:
    problems = scan(tracked_files())
    if problems:
        print("\n".join(problems))
        return 1
    print("Tracked-file security scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
