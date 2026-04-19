# Staleness signals

Full taxonomy of the signals that indicate a doc has drifted from reality. Each signal has a **severity** (how confident we can be that the doc is wrong) and a **detection method** (what to check in the code or git history).

Use this file during Phases 2–3 to ensure you're not missing classes of drift, and to keep severity judgments calibrated.

## Severity levels

- **Hard** — unambiguous evidence the doc is wrong (e.g. references a file that doesn't exist).
- **Soft** — circumstantial evidence the doc is likely wrong (e.g. related code has changed a lot since review).
- **Meta** — the doc's trust metadata itself is suspect (e.g. `Last reviewed` older than threshold).

Use Hard signals to support 🔴 **Critical** classification. Soft signals support 🟠 **Likely stale**. Meta signals alone only justify 🟡 **Possibly stale**.

## Hard signals (→ Critical)

### 1. Broken path references

The doc mentions a path in backticks, markdown links, or code-fence headers, and that path does not exist on disk at HEAD.

**Detect**: extract paths matching `(src|apps|packages|lib|internal)/...` and path-like strings inside backticks; verify with `git cat-file -e HEAD:<path>`.

**Evidence to cite**: the doc's line/section, the path, the commit that removed it (`git log --all --diff-filter=D -- <path> | head -5`).

Exception: if the path exists but under a different name, this is a **Rename** signal (still Hard, but the fix is a path-replace, not a rewrite).

### 2. Broken symbol references

The doc mentions a function / class / constant / export by name in code-like context, and that name no longer exists in the referenced file (or in the whole codebase).

**Detect**: extract identifiers from code fences and inline backticks. Grep for them in the expected file; if not found there, grep repo-wide.

**Evidence to cite**: the identifier, the file where the doc claims it lives, and where it actually is now (if anywhere).

### 3. Invalid code examples

A code fence in the doc would not run against current code: imports that don't resolve, types that don't match, API signatures that have changed.

**Detect**: for typed languages with import statements visible in the code fence, check that each import is resolvable at HEAD. For function-call examples, check the called function's current signature matches the arguments shown.

**Evidence to cite**: the code fence line range, the specific mismatch, the commit that changed the signature.

### 4. Structural architecture violations

The doc's architecture diagram or layer description claims a dependency direction that the current code does not obey. For instance, the doc says "UI only imports from Service", but there are current imports from UI directly into Repo.

**Detect**: for each stated constraint, grep/AST-check the claimed violation. This requires the doc to have stated something concrete — if it's vague, fall back to Soft.

**Evidence to cite**: the doc's claim, and a specific file + line that contradicts it.

### 5. Contradiction between two docs

Two docs claim different things about the same subject, and one of them must be wrong relative to current code.

**Detect**: when analyzing, if a claim in one doc contradicts another, verify which (if either) matches code. Mark the wrong one Critical.

**Evidence to cite**: both doc locations + the code that agrees with one of them.

## Soft signals (→ Likely stale)

### 6. High churn in related paths since review

Files the doc points to have had substantive commits since `Last reviewed`.

**Detect**: `git log --since=<last-reviewed> --oneline -- <path>`. Count commits; read commit messages.

**What counts as substantive**: feature commits, refactor commits, and API-change commits. Excludes formatting, dependency bumps, test-only changes, typo fixes — these rarely affect what a design doc says.

**Evidence to cite**: the count, a sample of commit subjects, and the specific file(s) with highest churn.

Calibration: 10+ substantive commits in 60 days to a core related path → Likely stale. 1–2 commits → probably fine. Between → read the commit messages and judge.

### 7. New public-surface additions

The doc describes an API/interface/command surface, and new public methods/routes/commands have appeared that aren't mentioned.

**Detect**: for a doc describing e.g. CLI commands, diff the list of commands in the doc vs. current help output or command registry. For an API doc, diff documented routes vs. actual router config.

**Evidence to cite**: the new surface elements absent from the doc.

### 8. Configuration drift

The doc enumerates config keys, env vars, or feature flags, and the current set differs.

**Detect**: compare the enumeration in the doc against the current config schema / env example / feature-flag definitions.

**Evidence to cite**: added and removed keys.

### 9. Version / dependency mention drift

The doc names specific versions ("we use X version 2.x") and the project is now on a materially different version.

**Detect**: extract version claims; check current lockfile / manifest.

**Evidence to cite**: claimed version, current version.

Skip trivial minor-version bumps unless breaking changes occurred.

### 10. Cross-link breakage

Markdown links from this doc to other docs resolve to files that now don't exist or have moved.

**Detect**: parse all `[text](path)` links; check each target exists.

**Evidence to cite**: the broken link.

Note: a broken cross-link is Hard if the link is load-bearing (the doc relies on the linked doc for meaning), Soft if it's a "see also". Use judgment.

## Meta signals (→ Possibly stale)

### 11. `Last reviewed` past threshold

`Last reviewed` date is older than the staleness threshold (default 60 days), with no specific code-drift signal.

**Detect**: trivial — parse the date and compare to today.

**Evidence to cite**: the date and the delta in days.

Action: typically just needs a review pass; the doc may well still be accurate.

### 12. Missing metadata

No `Status:` or no `Last reviewed:` header at all.

**Detect**: trivial.

**Action**: classify as ⚪ Unknown. Don't assume stale; surface for human triage.

### 13. Doc mtime newer than `Last reviewed`

The doc was edited after its claimed review date. Means someone changed the content without bumping the review date (or bumped the date without re-reading). Trust is broken.

**Detect**: `git log -1 --format=%cI -- <doc-path>` vs. parsed `Last reviewed`.

**Action**: treat `Last reviewed` as untrusted for this doc. Fall back to code-comparison to classify.

### 14. `Last reviewed` newer than doc mtime by a lot

Someone bumped the review date without touching the doc itself. Could be legitimate (re-read and confirmed fine) or lazy (bumped to make the dashboard green).

**Detect**: compare dates.

**Action**: minor meta signal. If no other drift signals are present, treat as Fresh but note it in the report so the user can decide.

## Gap signals (→ Orphan)

### 15. Domain with no design doc coverage

A top-level business domain in the code has no design doc that mentions it.

**Detect**: list `src/<domain>/` directories; grep `docs/design-docs/` for each name. Domains with no hits are orphans.

**Evidence to cite**: domain path, commit where it was introduced, rough size.

### 16. Feature with no product spec

A user-facing feature directory exists (e.g. `src/features/<feature>/`) without any corresponding `docs/product-specs/<feature>.md`.

**Detect**: similar to above but against `product-specs/`.

**Evidence to cite**: feature path, size, introduction commit.

### 17. New external dependency with no reference

A major framework / SDK has been added to the manifest that isn't in `docs/references/`.

**Detect**: diff current manifest against the dependencies mentioned in `docs/references/`.

**Evidence to cite**: the dependency name, version, when it was added.

## Signals that are NOT reasons to flag

Avoid false positives from these:

- **Minor wording is old-fashioned.** Voice/style drift isn't this skill's job.
- **Doc is short.** Short ≠ stale.
- **Doc has TODO markers in the original content.** TODOs are intentional placeholders; don't flag unless the TODO is specifically about updating.
- **Last reviewed is old but doc is obviously still correct.** Note as Meta/Possibly stale, don't escalate.
- **Doc discusses historical decisions.** A "decisions log" or ADR is *supposed* to preserve history. Don't flag old ADRs as stale just because the decision is old — flag only if the decision has been reversed and the doc doesn't note that.

## How to combine signals

A doc's final classification is the highest severity applicable:

- Any Hard signal → 🔴 Critical.
- No Hard, any Soft → 🟠 Likely stale.
- No Hard, no Soft, any Meta → 🟡 Possibly stale.
- Nothing → 🟢 Fresh (if metadata is present) or ⚪ Unknown (if metadata is missing).

Orphan is a separate axis — a domain can be an orphan regardless of any individual doc's classification.

When multiple signals of the same severity pile up, mention all of them in the evidence. "Critical" with 5 broken references is meaningfully worse than "Critical" with 1, and this informs the order the user should address findings.
