# Update patterns

How to safely rewrite each doc type during Phase 5. The overarching rule: **update facts, preserve rationale and voice**. Most drift fixes are surgical, not rewrites.

Read this before applying any update. If a doc doesn't fit any pattern here, default to the **design doc** pattern (most conservative).

## Universal rules

Before editing any doc:

1. **Read the whole file.** Don't rewrite based on a drift finding alone — you need context.
2. **Note the voice.** First- vs. third-person, tense, formality. Match it exactly in the edit.
3. **Preserve section structure.** Don't reorganize unless asked. Same headings, same order.
4. **Leave non-drifted sections untouched.** If only the "Decision" section is stale, don't also "improve" the "Context" section.
5. **Metadata last.** Apply the content change, diff-preview, confirm, then bump `Last reviewed`. Never bump the date on an un-made or not-yet-approved change.
6. **If unsure, ask rather than rewrite.** "Section X describes a three-step flow; current code has five steps. Should I expand the description, or do you want to preserve the original scope and note that MFA and rate-limiting live elsewhere?"

## Pattern: Design doc (ADR-style)

File typically at `docs/design-docs/<topic>.md`. Structure: Context → Decision → Rationale → Consequences → Related.

### What drifts

- **Decision** (often): the specific mechanism may have changed. Example: "We use Zod for boundary parsing" → team switched to Valibot.
- **Code examples** under Decision: API changes.
- **Related links**: targets moved or deleted.
- **Consequences**: sometimes — new constraints emerged.

### What rarely drifts

- **Context**: the problem statement usually holds.
- **Rationale**: the reasons for the decision. If the rationale itself is wrong, the decision has probably been reversed — which is a deprecation, not an update.

### Update procedure

1. Rewrite the specific stale sentences/paragraphs in Decision. Replace example code blocks with current API usage pulled from referenced files.
2. Fix Related links.
3. Read Rationale and Consequences end-to-end. If any claims are now false (e.g. "This costs no performance" but benchmarks have since shown otherwise), surface that as a separate finding rather than silently rewriting — the user may want to revisit the decision.
4. Update `Last reviewed`. Keep `Status: verified` unless the Decision changed substantially — in that case, set `Status: draft` and ask the user to verify.

### When to deprecate instead of update

If the whole decision has been reversed, **do not rewrite**. Instead:

1. Set `Status: deprecated`.
2. Add a header note: `> **Superseded by [<new-doc>](<path>) on YYYY-MM-DD.** <One-line summary of what changed.>`
3. Leave the rest of the content intact as historical record.
4. Create or point to the successor doc.

## Pattern: Architecture doc

File: `ARCHITECTURE.md` at root.

### What drifts

- **Domain list**: new domains added, old ones removed or merged.
- **Layer table**: example file paths go stale as files move.
- **Provider list**: new cross-cutting concerns added, old ones removed.
- **Diagram**: out of date when structure changes.
- **Known violations**: items resolved (or new ones introduced).

### What rarely drifts

- The overall layered model (Types → Config → Repo → Service → Runtime → UI). This changes only on major refactors.
- The dependency-direction rule. Same.

### Update procedure

1. Re-list domains from `src/` (or equivalent). Add new ones, remove deleted ones. Keep summaries short.
2. Update example file paths in the layer table — these are the most likely to rot.
3. Regenerate the provider list from current imports. If new providers emerged, add them; if one was removed, delete the row.
4. Regenerate the mermaid diagram if structure changed meaningfully.
5. Update "Known violations" — cross-reference `tech-debt-tracker.md`.
6. If the overall model itself has drifted (e.g. dependency direction is now bidirectional in practice), **do not normalize the doc to match reality**. That's papering over architectural decay. Instead, flag it as a tech-debt item and leave the doc describing the intended architecture with a "Current violations" note.

## Pattern: AGENTS.md (or CLAUDE.md)

Root-level entry point, ~100 lines.

### What drifts

- **"Start here" table** rows: target docs moved or were renamed.
- **Repository layout** bullets: top-level directories added/removed.
- **docs/ index**: entries added, removed, renamed.
- **Core invariants**: occasionally — an invariant was relaxed or added.

### What rarely drifts

- The one-paragraph description.
- The overall structure.

### Update procedure

1. Verify every link target exists.
2. Re-list top-level directories.
3. Sync the docs/ index with what actually exists under `docs/`.
4. Core invariants: if an invariant is listed here but the code no longer enforces it, **do not remove silently**. Surface as a finding — the invariant may be aspirational, or may have been accidentally relaxed. User decides.
5. Keep under ~120 lines. If adding content pushes it past, move something into `docs/` instead.

## Pattern: Index files (`docs/*/index.md`)

### What drifts

- The list of siblings — files added or removed in the directory.
- Status / Last reviewed columns — need to be pulled fresh from each file's header.

### What rarely drifts

- The "Status vocabulary" or explanation sections.

### Update procedure

Index files are mostly mechanical. Treat them like generated content:

1. List files in the directory.
2. For each, read its `Status:` and `Last reviewed:` headers and its top-level description.
3. Regenerate the table.
4. Keep any hand-written sections (vocabulary, usage notes) unchanged.

Consider suggesting to the user that these be script-generated rather than hand-maintained — gardening them is cheap but repetitive.

## Pattern: Core beliefs (`docs/design-docs/core-beliefs.md`)

### What drifts

Rarely. Core beliefs are meant to be stable. What can happen:

- A belief became mechanically enforced, so it's no longer just a belief — worth noting ("enforced by lint X").
- A belief was quietly abandoned and the code now routinely violates it.

### Update procedure

1. For each belief, grep the code to see if it's broadly followed. If it isn't, **do not edit the belief out**. Flag it prominently: the question is whether to enforce or deprecate, and that's a team decision, not a gardening decision.
2. If a new shared belief has emerged in multiple design docs (same principle restated three times), consider promoting it here. Suggest to the user; don't unilaterally add.
3. This file changes by human decision, not by drift-fixing. Be very hesitant to edit.

## Pattern: Product spec (`docs/product-specs/<flow>.md`)

### What drifts

- Step counts in user flows.
- Screenshot / UI references.
- Copy text quoted from the UI.
- Error messages and their triggering conditions.

### Update procedure

1. Read the flow's implementation in the code.
2. Compare the sequence of steps; update if the flow has grown or shrunk.
3. Quoted UI copy: verify against source strings (i18n files or component strings).
4. Do not fabricate content for flows you haven't traced end-to-end. If you can't verify a section, flag it rather than guessing.

## Pattern: Generated docs (`docs/generated/*`)

### What drifts

By definition, these should always match the source. If they don't, the generator is broken or not being run.

### Update procedure

**Do not hand-edit.** Instead:

1. Re-run the generator command noted at the top of the file.
2. If the generator doesn't exist or is broken, add a tech-debt entry and do not update the doc.
3. If the user wants the doc updated anyway, regenerate from current source as a one-off, and add a tech-debt entry to get the automatic generation re-established.

## Pattern: Tech debt tracker (`docs/exec-plans/tech-debt-tracker.md`)

### Updates from this skill

- Add items discovered during gardening (new orphan domains, violated invariants, broken generators).
- Mark items resolved if the code now handles them.
- Don't rewrite existing items' descriptions — they reflect the state at intake.

### Never do

- Don't delete resolved items. Move them to the "Resolved" section with a link to the fixing PR/commit.

## Pattern: Plans (`docs/exec-plans/active/*.md`, `.../completed/*.md`)

### What drifts

- **Active plans**: their Steps checklist may be out of sync with what actually shipped.
- **Completed plans**: should be immutable. Don't edit them.

### Update procedure

For active plans:

1. Read the plan's steps and check each against the code.
2. Mark complete steps with `[x]`.
3. If a plan is actually done, ask the user whether to move it to `completed/`.
4. If a plan was abandoned, ask whether to delete or move to completed with a "Superseded" note.

For completed plans: **never edit**. If you find an error, add an errata note at the top, don't revise the body.

## Pattern: References (`docs/references/*-llms.txt`)

### What drifts

- The library's actual docs changed.
- Library version bumped.
- Library was removed from the project entirely.

### Update procedure

If the library is gone from the manifest: move the reference file to `docs/references/deprecated/` (or equivalent) rather than deleting — some historical context may still be useful.

If the library is still used: these files are usually best regenerated from upstream docs rather than hand-edited. Treat like generated content — note who / what generates them and when.

If there's no generator: add a tech-debt entry. Don't try to rewrite library docs by hand.

## Diff preview format

When showing the user a proposed update, use this format:

```
📄 docs/design-docs/auth.md
Grade: 🔴 Critical
Evidence: 2 broken path references, 1 invalid code example

--- before
+++ after
@@ Decision @@
-We verify tokens using the `verifyToken` helper from `@app/auth`:
+We verify tokens using the `verifySession` helper from `@app/auth` (renamed in #2341):

-import { verifyToken } from "@app/auth";
+import { verifySession } from "@app/auth";

@@ metadata @@
-Last reviewed: 2025-09-14
+Last reviewed: 2026-04-19
```

Then: "Apply this update? (yes / no / edit)".

Don't batch multiple docs into one diff view — each doc gets its own preview. The exception is bulk date-only bumps, which can be shown as a compact list.
