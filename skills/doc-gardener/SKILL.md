---
name: doc-gardener
description: Scan an existing docs/ folder, cross-reference it against the current codebase and recent git history, and update documentation that has drifted out of sync with reality. Use this skill whenever the user asks to refresh / update / review / audit their docs, check for stale documentation, sync docs with code, run doc maintenance, or "garden" the docs. Also trigger on phrases like "our docs are out of date", "make sure docs match the code", "what docs need updating after these changes", or any request to check documentation freshness. Works best on repos that follow the harness-engineering pattern (Status / Last reviewed headers) but falls back to git-based heuristics otherwise. Produces drift findings with evidence, then applies user-approved updates.
---

# doc-gardener

Keep the `docs/` folder honest. This skill implements the "doc gardening" loop described in OpenAI's *Harness engineering* article: scan the knowledge base for content that no longer reflects the code, and propose precise updates with evidence.

The output is a **drift report** (per-document classification with evidence from code and git) followed by **targeted updates** the user approves and applies.

## Core philosophy

1. **Drift is a bug.** A doc that disagrees with the code is worse than a missing doc — agents will act on it. Treat stale documentation with the same seriousness as stale code.
2. **Evidence, not opinion.** Every "this is stale" claim must cite specific code locations or git commits. Don't flag a doc as stale on vibes alone.
3. **Preserve rationale, update facts.** When a design doc drifts, the *what* and *why* may still be correct even when the *how* has changed. Update the implementation details; keep the reasoning.
4. **Never surprise the user.** Present findings first, let the user decide what to update, then apply. No silent rewrites.
5. **Uncertainty is a first-class output.** If you can't tell whether a doc is stale, say so and escalate to a human. Don't guess.

## When to run this skill

Trigger on requests like:
- "Our docs are out of date — can you refresh them?"
- "Check which docs need updating"
- "Run doc gardening / doc maintenance / a docs audit"
- "Sync the docs with the current code"
- "I just merged a big refactor, what docs need updating?"
- "Are there any stale design docs?"
- "Bump Last reviewed on anything that's still accurate"

Also trigger when the user mentions having run `harness-docs` previously and wants to keep it maintained, or when they reference the OpenAI harness engineering article's gardener concept.

Do NOT trigger for:
- Creating docs from scratch — use `harness-docs` for that.
- Fixing typos or rewording for style — that's normal editing, doesn't need a skill.
- Generating new documentation for an undocumented feature — also more like `harness-docs` territory or a direct write.

## Workflow

Six phases. Run in order. The first four produce a drift report; Phase 5 applies approved updates; Phase 6 wraps up.

### Phase 1 — Run mechanical lint and inventory the docs

Start by running the bundled `scripts/docs_lint.py` — this catches deterministic issues (broken links, missing/invalid metadata, stale dates, index coverage gaps) in one shot, and produces a machine-readable manifest the rest of the workflow builds on.

```bash
python3 <skill-path>/scripts/docs_lint.py --root <repo-root> --threshold-days <N> --json
```

The default threshold is 60 days; pass what the user requested. The skill is bundled with this script and should invoke it directly — no need to reimplement any of its checks.

Parse the JSON output. For each file you get:
- `path`, `status`, `last_reviewed`, `owner` — the doc's metadata.
- `findings[]` — each with `rule`, `severity`, `line`, `message`. These are pre-classified mechanical drift signals.

On top of the script's output, extract **linked code paths** per doc (the script doesn't do this — it's doc-gardener-specific context):

- Paths in backticks matching existing directories or files (e.g. `` `src/auth/service.ts` ``)
- Paths in code-fence file headers
- Markdown links to files inside the repo
- Implicit scope from the doc's location and title (e.g. `docs/design-docs/auth.md` → `src/auth/`)

Build a manifest: one entry per doc with lint findings + related code paths + git mtime (filled in next phase).

If `docs_lint.py` is not runnable for some reason (no python3, permission denied), fall back to reading each doc yourself and applying the same checks manually — but this is much slower. Prefer fixing the environment over skipping the script.

### Phase 2 — Gather git signals

For each doc in the manifest, collect evidence about whether the underlying reality has moved. Read `references/git-recipes.md` for the exact commands — key queries:

1. **Doc's own last-edit.** `git log -1 --format=%cI -- <doc-path>`. If this date is older than `Last reviewed`, the `Last reviewed` header is almost certainly wrong (someone bumped it without looking). If newer, the doc was touched after being reviewed — possibly fine, possibly drifted.
2. **Code changes since review.** For each related path, find commits since `Last reviewed`: `git log --since=<date> -- <path>`. Count and categorize (bugfix vs feature vs refactor based on commit messages, conservatively).
3. **Deleted references.** For every path mentioned in the doc, check `ls` / `git cat-file -e HEAD:<path>`. Paths that no longer exist are hard drift signals.
4. **Renamed references.** If a path is gone but the doc was recent, check `git log --follow --diff-filter=R -- <path>` or a repo-wide rename heuristic to detect if the file was moved.
5. **Orphan domains.** List top-level directories under `src/` (or equivalent). Any that have no design doc in `docs/design-docs/` mentioning them are potential orphans — the code has grown a surface the docs don't cover.
6. **High-churn hot spots.** `git log --since=<review-threshold> --name-only --pretty=format: | sort | uniq -c | sort -rn | head -20`. Files with many commits that are mentioned in docs deserve extra scrutiny.

Keep the output per-doc. Don't merge signals across docs yet.

### Phase 3 — Classify staleness

Assign each doc one of these grades, with evidence. Findings from `docs_lint.py` (Phase 1) and from git (Phase 2) both feed into this — a doc can earn Critical from either source.

- **🔴 Critical** — Hard drift. From lint: rules `links/broken`, `metadata/status-invalid`, `metadata/last-reviewed-malformed`, `code-fence/path-missing`, `index/missing-sibling`. From code comparison: APIs/symbols referenced by the doc that no longer exist. Must fix.
- **🟠 Likely stale** — From git: related code changed substantively since `Last reviewed`, and the changes appear to affect what the doc describes. Needs verification and probably updates. Lint may be quiet — this is exactly the kind of drift lint can't catch.
- **🟡 Possibly stale** — From lint: rule `freshness/stale`, or `references/path-missing` (soft — the script only flags unambiguous paths). From metadata: no strong code-drift signal found. Refresh review recommended; may just need a date bump.
- **🟢 Fresh** — Recent review AND no meaningful churn in related paths AND no lint findings. Leave alone (or just bump the date if the user wants to reaffirm).
- **⚪ Unknown** — From lint: `metadata/status-missing` or `metadata/last-reviewed-missing`, and no git signal pins down whether the doc is current. Surface for human triage.
- **➕ Orphan** — New code area with no design-doc coverage (detected from Phase 2). Not a drift per se, but a documentation gap worth surfacing.

The staleness threshold passed to the lint script is the same one used for git-signal analysis. If the user hasn't specified, default to **60 days**. Mention the default in the report so they can override.

Critical rule: **evidence-bound classification**. For Critical, cite the specific lint rule or the specific broken code reference. For Likely stale, cite the specific commits. Never guess.

### Phase 4 — Present the drift report

Output a single structured report for the user to review **before making any changes**. Shape:

```
# Doc gardening report
Scope: <docs/ + AGENTS.md + ARCHITECTURE.md>
Threshold: 60 days since Last reviewed
Manifest: 23 docs scanned

## Summary
- 🔴 Critical:      2
- 🟠 Likely stale:  5
- 🟡 Possibly stale: 8
- 🟢 Fresh:         6
- ⚪ Unknown:        2
- ➕ Orphans:        3

## 🔴 Critical

### docs/design-docs/auth.md
- `Last reviewed: 2025-09-14`
- Doc references `src/auth/middleware/jwt.ts` which was removed in commit a3f21b (2026-01-08). Functionality moved to `src/auth/providers/token.ts`.
- Code example at line 63 imports `verifyToken` from `@app/auth` — this export no longer exists (replaced by `verifySession`).
- Proposed fix: update file path and import; verify the example still illustrates the intended flow.

### ...

## 🟠 Likely stale
...

## ➕ Orphans
- `src/billing/` (added 2026-02-10, 34 files, no design doc)
- `src/features/sharing/` (added 2026-01-22, no product spec)
...

## Recommended actions
1. Apply fixes for the 2 Critical docs.
2. Review and refresh the 5 Likely stale docs.
3. For Possibly stale: bulk-bump Last reviewed where you're confident, or schedule a review pass.
4. For Orphans: decide whether each warrants a design doc, product spec, or just a tech-debt entry.
```

Then ask: "Which of these should I apply? You can say 'all critical', 'show me the full diff for auth.md first', 'just bump the possibly-stale dates', etc."

This is the most important checkpoint in the skill. Do not proceed without user direction.

### Phase 5 — Apply updates

Only after the user approves. Read `references/update-patterns.md` for how to rewrite different doc types — the short rules:

1. **One doc at a time.** Don't batch-edit; each doc gets its own diff preview before the user accepts.
2. **Update facts, preserve rationale.** The `Rationale` and `Consequences` sections of a design doc usually stay put. The `Decision` and any code examples are what drifts.
3. **Fix references precisely.** If `src/old/path.ts` → `src/new/path.ts`, update every mention in the doc.
4. **Update code examples from current code.** Don't paraphrase — pull the actual current API from the referenced file.
5. **Bump metadata.** After applying substantive changes: `Last reviewed: <today>`, keep `Status: verified` unless the change is so large the doc needs re-review (then `Status: draft`).
6. **For dead content, deprecate rather than delete.** If a whole doc's topic no longer exists in the code, set `Status: deprecated` and add a header explaining what replaced it and linking there. Don't silently remove — agents may follow old links.
7. **Surface new tech debt.** If during an update you discover a code issue that isn't the doc's fault, don't fix it inline — add an entry to `docs/exec-plans/tech-debt-tracker.md`.
8. **For orphans,** unless the user says "create design docs for each", just add them to `tech-debt-tracker.md` as documentation-coverage gaps. Creating design docs for code you don't fully understand is how bad docs get born.

After each update, show the diff and confirm before moving on. For "Possibly stale" bulk date-bumps the user approves, it's fine to batch — those are metadata-only changes.

### Phase 6 — Summarize and hand off

After all approved updates are applied:

1. **Write a change summary.** What was touched, grouped by Critical / Likely stale / Possibly stale / Orphans-added-to-tech-debt.
2. **Suggest a commit/PR shape.** Typically one commit per doc for the Critical and Likely stale; one commit for all the date-bumps. For a PR, draft a body the user can copy.
3. **Propose a next-run date.** Based on the threshold and how much drift you found, suggest when to run doc-gardener again (e.g. "quarterly" if things were mostly fresh; "monthly" if drift was widespread).
4. **Mention systemic fixes.** If 5+ docs had the same kind of drift (e.g. all referenced a renamed module), suggest adding a lint rule or CI check. The best gardening is the kind that prevents the weeds. If the user hasn't yet wired `scripts/docs_lint.py` into CI, this is a good moment to suggest it — offer to generate a workflow file that runs `python3 scripts/docs_lint.py --root . --strict` on PRs touching `docs/` or referenced code paths.

Do not open a PR automatically. Commit and push only if the user explicitly asks.

## References

- `scripts/docs_lint.py` — Bundled mechanical lint script. Use this at Phase 1 and whenever the user wants a quick freshness check. Also suitable for the user's CI. Run with `--json` for machine-readable output. Exit codes: 0 clean, 1 warnings, 2 errors.
- `references/staleness-signals.md` — Full taxonomy of drift signals and how to detect each. Read during Phases 2–3.
- `references/git-recipes.md` — Concrete git commands for every signal this skill uses. Keep open during Phase 2.
- `references/update-patterns.md` — How to safely rewrite each doc type (design doc, architecture, index, product spec, etc.). Read during Phase 5.

## Common mistakes to avoid

- **Flagging without evidence.** "This might be stale" is not a finding. Every flag needs a commit hash, a file path that no longer exists, or a specific API mismatch.
- **Rewriting voice.** If the doc says "We parse at the boundary because…", don't turn it into "Data shapes are parsed at the boundary because…". Match the existing voice; only change factually-drifted content.
- **Silent deletion.** Never delete a doc just because its topic is gone. Deprecate with forward-link.
- **Auto-applying without the report.** Phase 4 is non-negotiable. Even for obvious fixes, show the report first.
- **Ignoring the `Last reviewed` trust problem.** Someone may have bumped the date without reading the doc. When a doc's own git mtime predates its `Last reviewed`, distrust the header and verify from code anyway.
- **Over-updating `Last reviewed`.** Bumping the date without reviewing is exactly the anti-pattern that creates silent rot. Only bump dates after either (a) substantive review, or (b) the user explicitly approves a bulk bump with the understanding that it's a self-attested "nothing changed".
- **Creating design docs for orphan code you don't understand.** A fabricated design doc is worse than an acknowledged gap. Default to "add to tech-debt-tracker"; only create a real doc if the user directs you or you can extract the design from clear code + existing notes.
