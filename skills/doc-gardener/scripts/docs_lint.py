#!/usr/bin/env python3
"""docs:lint — mechanical validation of a docs/ knowledge base.

Part of the doc-gardener Claude Code skill. Performs fast, deterministic checks
with zero false positives — anything this script flags is definitely wrong.

Checks performed:
  1. Each doc that should have metadata (Status:, Last reviewed:) actually has it.
  2. Status: values are one of {draft, verified, deprecated}.
  3. Last reviewed: is a valid YYYY-MM-DD date and within the staleness threshold.
  4. Markdown links [text](path) to internal files resolve to existing files.
  5. Code-fence file headers (```lang path/to/file) point to existing files.
  6. Path-like strings in backticks starting with known code prefixes exist.
  7. Every docs/**/index.md references every sibling *.md file.

Files where metadata is NOT required (navigational/generated/plans):
  AGENTS.md, CLAUDE.md, README.md, any index.md, docs/PLANS.md,
  anything under docs/generated/, docs/references/, docs/exec-plans/active/,
  docs/exec-plans/completed/.

Exit codes:
  0 = all checks pass
  1 = warnings only (stale Last reviewed, missing metadata, soft path misses)
  2 = errors (broken links, invalid Status, malformed date, index missing siblings)

Usage:
  python3 docs_lint.py                               # lint cwd, default 60-day threshold
  python3 docs_lint.py --root path/to/repo
  python3 docs_lint.py --threshold-days 30
  python3 docs_lint.py --json                        # machine-readable output
  python3 docs_lint.py --strict                      # exit 2 on warnings too

Designed to run in CI and as the first step of the doc-gardener skill's
deeper analysis — skill consumers should pass --json and parse the findings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote, urlparse

# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------

RE_STATUS = re.compile(r"^Status:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
# Match any Last reviewed line first, then validate the date separately,
# so we can distinguish "missing" from "present but malformed".
RE_LAST_REVIEWED = re.compile(r"^Last reviewed:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
RE_DATE_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_OWNER = re.compile(r"^Owner:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)

# Markdown link: [text](target)  — tolerates optional "title" after the target.
RE_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Code-fence opening line with a file header: ```lang path/to/file.ext
# (the "header" is everything after the language token)
RE_CODE_FENCE_OPEN = re.compile(r"^```(\S+)\s+([^\n`]+?)\s*$", re.MULTILINE)

# Path-like strings in inline backticks: has a dot-extension and no spaces.
RE_PATH_BACKTICK = re.compile(r"`([A-Za-z0-9_\-./]+\.[A-Za-z0-9]{1,6})`")

VALID_STATUSES = {"draft", "verified", "deprecated"}

# Path prefixes that are unambiguous enough to lint path references in backticks.
# Anything else (e.g. `package.json`) is too ambiguous and is skipped.
CODE_PATH_PREFIXES = (
    "src/", "apps/", "packages/", "lib/", "internal/",
    "cmd/", "bin/", "pkg/", "tests/", "test/",
)

# Navigational / generated files where Status: + Last reviewed: are not required.
EXEMPT_FILE_NAMES = {"AGENTS.md", "CLAUDE.md", "README.md", "index.md", "PLANS.md"}
EXEMPT_PATH_COMPONENTS = {"generated", "references", "active", "completed"}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: Optional[int]
    severity: str  # "error" | "warning" | "info"
    rule: str
    message: str


@dataclass
class FileReport:
    path: str
    status: Optional[str] = None
    last_reviewed: Optional[str] = None
    owner: Optional[str] = None
    findings: list = field(default_factory=list)


@dataclass
class Report:
    root: str
    threshold_days: int
    files: list = field(default_factory=list)
    errors: int = 0
    warnings: int = 0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def requires_metadata(rel: Path) -> bool:
    """Does this doc require Status: / Last reviewed: headers?"""
    if rel.name in EXEMPT_FILE_NAMES:
        return False
    if any(part in EXEMPT_PATH_COMPONENTS for part in rel.parts):
        return False
    # Root ARCHITECTURE.md and everything under docs/ requires metadata.
    if rel == Path("ARCHITECTURE.md"):
        return True
    return len(rel.parts) > 0 and rel.parts[0] == "docs"


def line_of(content: str, pos: int) -> int:
    """1-indexed line number of a character position in content."""
    return content.count("\n", 0, pos) + 1


def is_external_url(target: str) -> bool:
    """True if the target is an external URL (http, mailto, etc.)."""
    parsed = urlparse(target)
    return bool(parsed.scheme) and parsed.scheme in {"http", "https", "mailto", "ftp", "ftps"}


def strip_code_fences(content: str) -> str:
    """Replace content inside ```fenced``` blocks with blank lines.

    Preserves line numbers so findings report the right line. The opening and
    closing fence lines themselves are preserved (so fence-header checks still
    see them); only the content between them is blanked.
    """
    out = []
    in_fence = False
    for line in content.split("\n"):
        if line.lstrip().startswith("```"):
            out.append(line)
            in_fence = not in_fence
        elif in_fence:
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def discover_docs(repo_root: Path) -> list[Path]:
    """Find all markdown files in scope (root specials + everything under docs/)."""
    found: list[Path] = []
    for name in ("AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md", "README.md"):
        p = repo_root / name
        if p.is_file():
            found.append(p)
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        found.extend(sorted(docs_dir.rglob("*.md")))
    # De-dup while preserving order (rglob may include already-added files in weird setups)
    seen: set = set()
    unique: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_metadata(content: str, rel: Path, fr: FileReport) -> None:
    """Populate fr.status/last_reviewed/owner and flag missing/invalid metadata."""
    status_m = RE_STATUS.search(content)
    if status_m:
        value = status_m.group(1).lower()
        fr.status = value
        if value not in VALID_STATUSES:
            fr.findings.append(Finding(
                file=str(rel),
                line=line_of(content, status_m.start()),
                severity="error",
                rule="metadata/status-invalid",
                message=f"Status: {value!r} not one of {sorted(VALID_STATUSES)}",
            ))
    elif requires_metadata(rel):
        fr.findings.append(Finding(
            file=str(rel), line=None, severity="warning",
            rule="metadata/status-missing",
            message="missing `Status:` header",
        ))

    lr_m = RE_LAST_REVIEWED.search(content)
    if lr_m:
        raw_value = lr_m.group(1).strip()
        fr.last_reviewed = raw_value
        if not RE_DATE_YMD.match(raw_value):
            fr.findings.append(Finding(
                file=str(rel),
                line=line_of(content, lr_m.start()),
                severity="error",
                rule="metadata/last-reviewed-malformed",
                message=f"`Last reviewed:` value {raw_value!r} is not a valid YYYY-MM-DD date",
            ))
            # Clear so check_freshness doesn't also complain
            fr.last_reviewed = None
    elif requires_metadata(rel):
        fr.findings.append(Finding(
            file=str(rel), line=None, severity="warning",
            rule="metadata/last-reviewed-missing",
            message="missing `Last reviewed:` header",
        ))

    owner_m = RE_OWNER.search(content)
    if owner_m:
        fr.owner = owner_m.group(1).strip()


def check_freshness(fr: FileReport, threshold_days: int) -> None:
    if not fr.last_reviewed:
        return
    # Date format is already validated in check_metadata; bail silently if it somehow isn't.
    try:
        reviewed = datetime.strptime(fr.last_reviewed, "%Y-%m-%d").date()
    except ValueError:
        return
    delta = (date.today() - reviewed).days
    if delta > threshold_days:
        fr.findings.append(Finding(
            file=fr.path, line=None, severity="warning",
            rule="freshness/stale",
            message=f"`Last reviewed` {delta} days ago (threshold {threshold_days})",
        ))
    elif delta < 0:
        fr.findings.append(Finding(
            file=fr.path, line=None, severity="warning",
            rule="freshness/future-dated",
            message=f"`Last reviewed` is dated in the future ({fr.last_reviewed})",
        ))


def check_markdown_links(
    doc: Path, content_stripped: str, rel: Path, repo_root: Path, fr: FileReport,
) -> None:
    for m in RE_MD_LINK.finditer(content_stripped):
        target = m.group(2).strip()
        if not target or target.startswith("#"):
            continue
        if is_external_url(target):
            continue
        # Discard anchor portion — we can't validate anchors statically
        target_path = unquote(target.split("#", 1)[0])
        if not target_path:
            continue
        resolved = (doc.parent / target_path).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError:
            # Link points outside the repo; can't validate
            continue
        if not resolved.exists():
            fr.findings.append(Finding(
                file=str(rel),
                line=line_of(content_stripped, m.start()),
                severity="error",
                rule="links/broken",
                message=f"broken internal link: {target}",
            ))


def check_code_fence_headers(content: str, rel: Path, repo_root: Path, fr: FileReport) -> None:
    """Validate code fences that include a file path after the language tag."""
    for m in RE_CODE_FENCE_OPEN.finditer(content):
        header = m.group(2).strip()
        # A header with a space is likely a shell command, not a file path.
        if " " in header:
            continue
        # Require it to look like a path (contains a slash or a dot).
        if "/" not in header and "." not in header:
            continue
        if is_external_url(header):
            continue
        resolved = (repo_root / header).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError:
            continue
        if not resolved.exists():
            fr.findings.append(Finding(
                file=str(rel),
                line=line_of(content, m.start()),
                severity="error",
                rule="code-fence/path-missing",
                message=f"code-fence header references missing path: {header}",
            ))


def check_backtick_paths(
    content_stripped: str, rel: Path, repo_root: Path, fr: FileReport,
) -> None:
    """Flag `src/foo/bar.ts`-style references where the file doesn't exist.

    Only runs on path-looking strings under known code prefixes to avoid
    false positives on version numbers or unrelated dotted names.
    """
    for m in RE_PATH_BACKTICK.finditer(content_stripped):
        path = m.group(1)
        if not any(path.startswith(p) for p in CODE_PATH_PREFIXES):
            continue
        resolved = (repo_root / path).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError:
            continue
        if not resolved.exists():
            fr.findings.append(Finding(
                file=str(rel),
                line=line_of(content_stripped, m.start()),
                severity="warning",
                rule="references/path-missing",
                message=f"referenced code path does not exist: {path}",
            ))


def check_index_coverage(
    repo_root: Path, all_docs: list[Path], reports_by_path: dict[str, FileReport],
) -> None:
    """Every docs/**/index.md must reference every sibling *.md in its dir."""
    indices = [d for d in all_docs if d.name == "index.md"]
    for idx in indices:
        try:
            content = idx.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        siblings = sorted(
            p for p in idx.parent.iterdir()
            if p.is_file() and p.suffix == ".md" and p.name != "index.md"
        )
        rel = idx.relative_to(repo_root)
        fr = reports_by_path.get(str(rel))
        if fr is None:
            fr = FileReport(path=str(rel))
            reports_by_path[str(rel)] = fr
        for s in siblings:
            # Accept name, stem, or relative-path references.
            if s.name not in content and s.stem not in content:
                fr.findings.append(Finding(
                    file=str(rel), line=None, severity="error",
                    rule="index/missing-sibling",
                    message=f"index does not reference sibling `{s.name}`",
                ))


# ---------------------------------------------------------------------------
# pipeline
# ---------------------------------------------------------------------------

def lint(repo_root: Path, threshold_days: int) -> Report:
    repo_root = repo_root.resolve()
    report = Report(root=str(repo_root), threshold_days=threshold_days)
    all_docs = discover_docs(repo_root)
    reports_by_path: dict[str, FileReport] = {}

    for doc in all_docs:
        rel = doc.relative_to(repo_root)
        try:
            content = doc.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            fr = FileReport(path=str(rel))
            fr.findings.append(Finding(
                file=str(rel), line=None, severity="error",
                rule="io/read-failed",
                message=f"could not read file: {e}",
            ))
            reports_by_path[str(rel)] = fr
            continue

        content_stripped = strip_code_fences(content)

        fr = FileReport(path=str(rel))
        check_metadata(content, rel, fr)
        check_freshness(fr, threshold_days)
        check_markdown_links(doc, content_stripped, rel, repo_root, fr)
        check_code_fence_headers(content, rel, repo_root, fr)
        check_backtick_paths(content_stripped, rel, repo_root, fr)
        reports_by_path[str(rel)] = fr

    check_index_coverage(repo_root, all_docs, reports_by_path)

    # Finalize — preserve discovery order, then append any reports added by later checks.
    for doc in all_docs:
        rel = doc.relative_to(repo_root)
        fr = reports_by_path.pop(str(rel), None)
        if fr is not None:
            report.files.append(fr)
    report.files.extend(reports_by_path.values())

    for fr in report.files:
        for f in fr.findings:
            if f.severity == "error":
                report.errors += 1
            elif f.severity == "warning":
                report.warnings += 1

    return report


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

SEV_ICON = {"error": "✗", "warning": "⚠", "info": "ℹ"}


def format_human(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"docs:lint — {report.root}")
    lines.append(f"  threshold: {report.threshold_days} days")
    lines.append(f"  scanned:   {len(report.files)} files")
    lines.append(f"  errors:    {report.errors}")
    lines.append(f"  warnings:  {report.warnings}")
    lines.append("")

    any_findings = False
    for fr in report.files:
        if not fr.findings:
            continue
        any_findings = True
        lines.append(f"## {fr.path}")
        meta_bits: list[str] = []
        if fr.status:
            meta_bits.append(f"Status: {fr.status}")
        if fr.last_reviewed:
            meta_bits.append(f"Last reviewed: {fr.last_reviewed}")
        if meta_bits:
            lines.append("  " + " | ".join(meta_bits))
        for f in fr.findings:
            icon = SEV_ICON.get(f.severity, "·")
            loc = f":{f.line}" if f.line else ""
            lines.append(f"  {icon} [{f.rule}]{loc}  {f.message}")
        lines.append("")

    if not any_findings:
        lines.append("✓ all checks passed")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docs_lint",
        description="Mechanical lint for a docs/ knowledge base (see module docstring).",
    )
    parser.add_argument("--root", default=".", help="Repository root (default: current dir)")
    parser.add_argument(
        "--threshold-days", type=int, default=60,
        help="Warn when Last reviewed is older than this many days (default: 60)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human text")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with status 2 if any warnings are present (default: exit 1 on warnings)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.root)
    if not repo_root.is_dir():
        print(f"error: --root {args.root!r} is not a directory", file=sys.stderr)
        return 2

    report = lint(repo_root, args.threshold_days)

    if args.json:
        json.dump(asdict(report), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_human(report))

    if report.errors:
        return 2
    if report.warnings:
        return 2 if args.strict else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
