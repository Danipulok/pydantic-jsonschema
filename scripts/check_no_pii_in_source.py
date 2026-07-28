#!/usr/bin/env python3
# ruff: noqa: T201

"""Source-level PII scanner.

Greps every file passed on argv (or every source file in the repo, minus a static skip list, when
run standalone) for raw email addresses and phone numbers. This is a public repository, so an email
or phone hardcoded in source, docs, or a config template leaks personal data the moment it is
pushed. Enforces the "No Personal or Identifying Information" rule as a pre-commit hook + CI step
(`just check-pii`), catching what a human review misses.

Not flagged:

- `*@example.com` / `.org` / `.net` and the reserved `.example` TLD — RFC-2606 placeholders.
- The package's own author / maintainer emails, read from `pyproject.toml` (already public project
  metadata, so allow-listing them here duplicates nothing).
- Lines containing `# pii-ok` — escape hatch for a fixture that genuinely needs a real-looking
  value.
- `tests/` — this library validates email/URI grammar, so its fixtures are full of address-shaped
  strings by design; scanning them would be pure noise.

Exit codes: 0 if clean, 1 on any hit.
"""

import re
import sys
import tomllib
from pathlib import Path

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Loose phone matcher: an international `+…` sequence, or three delimited digit groups. Requires a
# `+` or explicit separators so ISO timestamps, byte sizes, and version numbers do not match.
_PHONE_RE = re.compile(r"(?:\+\d[\d\s\-().]{7,}|\b\d{3,4}[\s\-]\d{3,4}[\s\-]\d{3,4}\b)")

# RFC-2606 reserved placeholders — safe by definition regardless of local part.
_ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
_ALLOWED_EMAIL_TLDS = (".example",)
_ESCAPE_HATCH = "# pii-ok"

# Paths excluded from the standalone walk. `tests/` holds address-shaped grammar fixtures; this
# module holds the very patterns it searches for; lockfiles are generated, not source.
_EXCLUDED_PREFIXES = (
    "tests/",
    "scripts/check_no_pii_in_source.py",
)
_EXCLUDED_FILES = {"uv.lock"}

_SCANNED_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml"}
_SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", "htmlcov", "sbom"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _allowed_emails() -> frozenset[str]:
    """Author / maintainer emails declared in `pyproject.toml` — public project metadata."""
    pyproject = _repo_root() / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return frozenset()
    project = data.get("project", {})
    people = [*project.get("authors", []), *project.get("maintainers", [])]
    return frozenset(person["email"] for person in people if "email" in person)


def _is_excluded(path: Path) -> bool:
    rel = path.as_posix()
    if path.name in _EXCLUDED_FILES:
        return True
    return any(rel.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def _email_is_allowed(email: str, *, allowed_emails: frozenset[str]) -> bool:
    if email in allowed_emails:
        return True
    _, _, domain = email.partition("@")
    if any(domain == d or domain.endswith(f".{d}") for d in _ALLOWED_EMAIL_DOMAINS):
        return True
    return domain.endswith(_ALLOWED_EMAIL_TLDS)


def _scan_line(line: str, *, allowed_emails: frozenset[str]) -> list[str]:
    if _ESCAPE_HATCH in line:
        return []
    hits: list[str] = []
    for email in _EMAIL_RE.findall(line):
        if not _email_is_allowed(email, allowed_emails=allowed_emails):
            hits.append(f"email: {email}")
    for phone in _PHONE_RE.findall(line):
        if len(re.sub(r"\D", "", phone)) >= 8:
            hits.append(f"phone: {phone}")
    return hits


def scan_file(path: Path, *, allowed_emails: frozenset[str]) -> list[tuple[int, str]]:
    if _is_excluded(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        findings.extend(
            (line_number, hit) for hit in _scan_line(line, allowed_emails=allowed_emails)
        )
    return findings


def _default_targets() -> list[Path]:
    """Standalone invocation — walk the repo for source files worth scanning."""
    repo = _repo_root()
    results: list[Path] = []
    for path in repo.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in _SCANNED_SUFFIXES:
            results.append(path.relative_to(repo))
    return results


def main(argv: list[str]) -> int:
    allowed_emails = _allowed_emails()
    targets = [Path(arg) for arg in argv[1:]] or _default_targets()
    any_hits = False
    for target in targets:
        for line_number, hit in scan_file(target, allowed_emails=allowed_emails):
            any_hits = True
            print(f"{target}:{line_number}: {hit}")
    if any_hits:
        print(
            "\nPII detected in source. Use an `@example.com` placeholder, an env var, or a trailing"
            " `# pii-ok` comment if a fixture genuinely needs a real-looking value.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
