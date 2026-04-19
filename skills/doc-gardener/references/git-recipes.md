# Git recipes

Concrete commands for every git-based signal this skill uses. Copy and adapt. Paths should be quoted if they contain spaces.

## Preliminaries

Always run from the repo root. Check the working state first:

```bash
git rev-parse --show-toplevel           # confirm you're in a git repo
git rev-parse --abbrev-ref HEAD         # current branch
git status --porcelain                  # warn if there are uncommitted changes
```

If `git status` shows uncommitted changes, note it in the report — findings are based on HEAD, not the working tree. Don't refuse to run; just flag.

## Per-doc history

### When was this doc last actually edited?

```bash
git log -1 --format='%cI %H %s' -- <doc-path>
```

Compare this date to the doc's `Last reviewed` header. If the commit date is **newer** than `Last reviewed`, the review date is likely untrustworthy (someone edited without bumping, or bumped without reading).

### Full history of a doc

```bash
git log --follow --format='%cI %h %s' -- <doc-path>
```

`--follow` tracks renames. Useful when trying to understand why a doc says what it does.

### Diff of a doc over a time range

```bash
git log --follow -p --since='<date>' -- <doc-path>
```

Skim this to see what's been added/removed since the last review.

## Related-code history

### Commits to a path since the doc was reviewed

```bash
git log --since='<last-reviewed-date>' --oneline -- <related-path>
```

For a directory, add a trailing slash. Use `--` to disambiguate from branch names.

### Same, but with stats to gauge magnitude

```bash
git log --since='<last-reviewed-date>' --stat -- <related-path>
```

The `insertions(+)/deletions(-)` line after each commit shows size. A dozen 1-line commits is different from two 500-line commits.

### Filter to meaningful commits (heuristic)

There's no perfect way to filter "meaningful" commits, but this removes obvious noise:

```bash
git log --since='<date>' --oneline -- <path> \
  | grep -viE '^\w+ (chore|style|format|typo|bump|deps|lint|ci)(\(|:)'
```

This is conservative — it only strips conventional-commit prefixes that are clearly non-substantive. Adjust if the repo uses different conventions.

### Subjects grouped by type

If the repo uses conventional commits:

```bash
git log --since='<date>' --format='%s' -- <path> \
  | awk -F'[(:]' '{print $1}' \
  | sort | uniq -c | sort -rn
```

Gives you a tally like `12 feat`, `5 fix`, `3 refactor`, `8 chore`. A doc with lots of `feat` commits in its related paths is likely stale in a way a doc with only `chore`/`fix` is not.

## Path existence and renames

### Does this path currently exist?

```bash
git cat-file -e "HEAD:<path>" 2>/dev/null && echo exists || echo missing
```

Quiet and scriptable. Works for files and directories.

### If missing, was it deleted or renamed?

First, find when it was deleted:

```bash
git log --all --diff-filter=D --format='%cI %h %s' -- <path> | head -5
```

Then, in the commit just before that deletion, look for a rename:

```bash
git log --all --follow --diff-filter=R --format='%cI %h %s' --name-status -- <possible-current-path>
```

For a broader search — "was this file moved somewhere else":

```bash
git log --all --diff-filter=R --name-status --format='%cI %h' \
  | grep -A1 '<original-path>'
```

Renames aren't always clean in git; a "delete + add" that git didn't detect as rename looks like a deletion + orphan. If nothing shows as R, grep for the filename:

```bash
git log --all --format='%cI %h' --diff-filter=A --name-only \
  | grep -B1 '<basename>'
```

## Orphan detection

### List top-level domain-like directories

```bash
ls -d src/*/ 2>/dev/null       # or apps/*/ or packages/*/
```

Adapt to the repo's structure.

### Find which of those have no design doc

```bash
for dir in src/*/; do
  name=$(basename "$dir")
  if ! grep -rqil "\b$name\b" docs/design-docs/ 2>/dev/null; then
    echo "orphan: $dir"
  fi
done
```

Adjust the grep to match how docs would reference the domain (exact name, path, etc.).

### When was a domain introduced?

```bash
git log --diff-filter=A --format='%cI %h %s' --follow -- <domain-path> | tail -1
```

`tail -1` gets the earliest (first addition).

## Churn hot-spots

### Files changed most often in the last N days

```bash
git log --since='<date>' --name-only --pretty=format: \
  | grep -v '^$' \
  | sort | uniq -c | sort -rn | head -20
```

Cross-reference this with docs' related paths. A hot-spot that's in a related path → reinforces Likely-stale classification.

### Authors touching a path recently

```bash
git log --since='<date>' --format='%an' -- <path> | sort | uniq -c | sort -rn
```

Useful if the repo has doc owners and you want to reach out.

## Dependency drift

### Diff manifest over time

For `package.json`:

```bash
git show "HEAD:package.json" | jq '.dependencies, .devDependencies' > /tmp/now.json
git show "<old-sha>:package.json" | jq '.dependencies, .devDependencies' > /tmp/then.json
diff /tmp/then.json /tmp/now.json
```

Adapt for `pyproject.toml`, `Cargo.toml`, `go.mod`, etc. For quick adds/removes:

```bash
git log --since='<date>' --oneline -- package.json Cargo.toml pyproject.toml go.mod
```

## Scoped diffs for specific drift checks

### "Has this symbol's signature changed since the doc was reviewed?"

Get the file's state at the review commit and compare:

```bash
# Approximate the review-time commit
review_sha=$(git log --before='<last-reviewed-date>' -1 --format='%H' -- <file-path>)

git show "$review_sha:<file-path>" > /tmp/before.txt
git show "HEAD:<file-path>" > /tmp/after.txt
diff /tmp/before.txt /tmp/after.txt | head -80
```

Use `--before` with the review date to land on the commit that was HEAD at review time.

### "Show me what a section of the doc would need to change"

```bash
# Current state of the code the doc describes
git show "HEAD:<related-file>"
```

Compare visually against the doc section. For anything non-trivial, read both files directly rather than relying on diff tools.

## Uncommitted-change awareness

If `git status --porcelain` showed changes, and any related path is among them:

```bash
git diff -- <related-path>         # unstaged
git diff --cached -- <related-path> # staged
```

Include these in findings only if they materially affect the doc. Note in the report: "Findings include uncommitted changes in working tree."

## Performance notes

On large repos, some of these commands are slow. Useful optimizations:

- Prefer `git log --oneline` when you just need counts/subjects.
- Use `-- <paths>` early in the command to limit scope.
- Cache results in-memory per doc rather than re-running per signal.
- For the orphan detection loop, batch the grep across all design docs once rather than per-directory.

If a single query runs >10 seconds, narrow its scope. You don't need perfect data — you need enough evidence to classify.
