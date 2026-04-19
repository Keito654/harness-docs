---
name: harness-docs
description: Analyze an existing codebase and generate an agent-first "system of record" docs/ directory following OpenAI's Harness Engineering pattern. Use this skill whenever the user asks to bootstrap documentation, scaffold a docs/ folder, set up AGENTS.md, make the repository more legible to coding agents (Claude Code, Codex, Cursor), or "document the architecture" of an existing project — even if they don't explicitly mention Harness Engineering. Also use when the user has an under-documented repo and wants agents to operate on it reliably. Reads the codebase and any existing markdown files first, then produces AGENTS.md + ARCHITECTURE.md + a structured docs/ tree with progressive-disclosure entry points.
---

# harness-docs

Generate an **agent-first documentation layout** for an existing repository, following the "repository knowledge as the system of record" pattern described in OpenAI's *Harness engineering: leveraging Codex in an agent-first world* (Feb 2026).

The output is a `docs/` tree plus root-level `AGENTS.md` and `ARCHITECTURE.md` that together form a **map, not an encyclopedia** — agents start from a short entry point (~100 lines) and descend into deeper, verifiable documents only when needed.

## Core philosophy

Four ideas drive every decision in this skill. Internalize them before generating anything:

1. **AGENTS.md is a table of contents, not a manual.** One giant instruction file fails in predictable ways: context is scarce and gets crowded out, everything marked "important" becomes non-guidance, rules rot, and a single blob can't be mechanically verified. Keep the entry point short (~100 lines) and make it point outward.
2. **Progressive disclosure.** The agent starts with a stable, small entry point and is taught where to look next. Deep information lives in `docs/`, reached only when relevant.
3. **Repo-local, versioned artifacts only.** Anything that isn't in the repository effectively does not exist for the agent. Slack threads, Google Docs, and tacit knowledge must be encoded as markdown/schemas/plans in the repo.
4. **Mechanical verifiability.** Structure the docs so linters and CI can check freshness, cross-links, and ownership. Prefer many small indexed files over one giant one.

If a design decision in this skill seems to contradict these four, the four win.

## When to run this skill

Trigger on requests like:
- "Set up docs for this repo so Claude Code / Codex / Cursor can work on it"
- "Bootstrap an AGENTS.md / CLAUDE.md for this project"
- "Document the architecture of this codebase"
- "I want agent-first / harness engineering style docs"
- "Scaffold a docs/ folder following the OpenAI harness pattern"
- Any case where the user has a working repo but documentation is sparse, scattered, or stale, and they want agents to navigate it reliably.

Also trigger when the user shares a link to the harness engineering article and asks to apply it.

Do NOT trigger for:
- Single-file README generation (too small — just write a README)
- User API documentation for external consumers (that's a different audience)
- Merely updating an existing well-structured docs/ (unless the user wants a full restructure)

## Workflow

The skill runs in five phases. Do them in order; don't skip ahead.

### Phase 1 — Discover the repository

Build a mental model of what the codebase is before writing anything.

1. **Read the root listing.** List the top of the repo (depth 1–2). Note the language, package manager, framework, monorepo vs single-package, test setup, CI config.
2. **Find entry points.** Look for `main.*`, `index.*`, `app.*`, `cmd/`, `bin/`, `src/`, `apps/`, `packages/`, `cli.*`, server/router files. These reveal the runtime shape.
3. **Identify domains.** Scan for top-level directories under `src/` or similar that look like business domains (`auth/`, `billing/`, `onboarding/`, etc.) vs infrastructure concerns (`db/`, `http/`, `telemetry/`).
4. **Detect layering.** Look for signs of a layered architecture (types → config → repo → service → runtime → UI, or similar). Note the direction of imports if visible.
5. **Inventory cross-cutting concerns.** Authentication, feature flags, logging, telemetry, connectors — these become "providers" in the ARCHITECTURE map.

Time-box this. For a medium repo, ~5–10 tool calls is enough. Don't read every file; sample.

### Phase 2 — Read existing documentation

Before writing anything new, harvest what's already there.

1. **Find all markdown.** Search for `*.md`, `*.mdx`, `*.rst`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README*`, `docs/**`, `.github/`, and any architecture/ADR folders.
2. **Read them in priority order:** root README → any AGENTS.md/CLAUDE.md → existing docs/ → CONTRIBUTING → ADRs.
3. **Extract three things from each:**
   - **Facts about the system** — architecture claims, component names, flows. These are raw material for the new docs.
   - **Stated principles or conventions** — become candidates for `docs/design-docs/core-beliefs.md`.
   - **Staleness signals** — references to removed code, TODO markers, outdated version numbers. Flag these; don't propagate them.
4. **Preserve, don't rewrite.** If an existing doc is accurate and well-placed, the new scaffold should reference it, not duplicate it. The goal is consolidation, not replacement.

### Phase 3 — Plan the docs layout

Decide what to create before creating it. The canonical layout is in `references/example-structure.md` — read that file now. Adapt it to the repo:

- **Always create**: `AGENTS.md`, `ARCHITECTURE.md`, `docs/design-docs/index.md`, `docs/design-docs/core-beliefs.md`, `docs/exec-plans/tech-debt-tracker.md`, `docs/PLANS.md`, `docs/QUALITY_SCORE.md`.
- **Create if the repo has a UI**: `docs/FRONTEND.md`, `docs/DESIGN.md`.
- **Create if there's a data layer**: `docs/generated/db-schema.md` (with a note that it's auto-generated — leave content as a placeholder or extract from migrations/schema files if available).
- **Create if there are product flows**: `docs/product-specs/index.md` + one spec per major flow you identified.
- **Create if there are notable external dependencies**: `docs/references/` with `*-llms.txt` placeholders for each major framework/SDK the project uses.
- **Skip** anything that doesn't apply. Empty scaffolding is worse than no scaffolding — it rots faster.

Present the planned tree to the user in a single message before writing files. This is a checkpoint: the user may want to add, remove, or rename sections.

### Phase 4 — Generate the files

Now read `references/file-templates.md` for the content shape of each file. Key rules when filling them in:

- **AGENTS.md stays under ~120 lines.** If it grows past that, move content into `docs/` and leave a pointer.
- **Every index file lists its siblings with a one-line summary each.** No index file should be longer than one screen.
- **Include a verification status** at the top of every design doc: `Status: draft | verified | deprecated` + `Last reviewed: YYYY-MM-DD`. This is what lets future lint jobs find stale docs.
- **Core beliefs are short and declarative.** "We parse data shapes at the boundary." "We prefer shared utility packages over bespoke helpers." Not essays.
- **ARCHITECTURE.md is a map, not a tutorial.** Domains × layers, dependency direction, cross-cutting providers. Diagrams are fine (mermaid works); walls of prose are not.
- **Cross-link everything.** Any mention of a domain or concept in one file should link to its authoritative doc. This is how agents navigate.
- **Match the repo's language.** If the existing README is in Japanese, write the docs in Japanese. If it's mixed, match the dominant language per-file. Code identifiers stay in their original form regardless.

Write files one by one, not in a single batch. After each, briefly confirm with the user or proceed if they've said to go ahead.

### Phase 5 — Wire up mechanical enforcement (optional, recommend it)

The original article emphasizes that docs only work if CI enforces them. Offer the user, as a follow-up, to add any of:

- A `.github/workflows/docs.yml` (or equivalent CI job) that runs the mechanical lint on PRs touching `docs/` or code referenced by docs. The companion `doc-gardener` skill ships a ready-made `scripts/docs_lint.py` that checks metadata validity, `Last reviewed` freshness, internal link resolution, code-fence path references, and index coverage. Don't reimplement it here — point the user at the `doc-gardener` skill.
- A "doc gardener" prompt file at `docs/design-docs/doc-gardening-prompt.md` that an agent can be pointed at periodically to scan for drift and open fix PRs. (Essentially, a saved invocation of the `doc-gardener` skill.)

Don't build these unprompted — they're scope creep for the initial run. Just mention them at the end.

## Output structure (canonical)

```
<repo-root>/
├── AGENTS.md                       # ~100 lines — table of contents / map
├── ARCHITECTURE.md                 # Top-level map: domains × layers × providers
└── docs/
    ├── design-docs/
    │   ├── index.md                # List of all design docs w/ verification status
    │   ├── core-beliefs.md         # Agent-first operating principles
    │   └── <topic>.md              # One per significant design decision
    ├── exec-plans/
    │   ├── active/                 # In-progress plans (checked in)
    │   ├── completed/              # Finished plans w/ decision logs
    │   └── tech-debt-tracker.md    # Known debt, versioned
    ├── generated/                  # Auto-generated docs — header says DO NOT EDIT
    │   └── db-schema.md            # (if applicable)
    ├── product-specs/
    │   ├── index.md
    │   └── <flow>.md               # One per major user-facing flow
    ├── references/                 # External library refs, often *-llms.txt
    │   └── <lib>-llms.txt          # (one per major dependency)
    ├── DESIGN.md                   # Design-system / visual-design summary (if UI)
    ├── FRONTEND.md                 # Frontend conventions (if UI)
    ├── PLANS.md                    # Index into exec-plans/
    ├── PRODUCT_SENSE.md            # Product principles (optional)
    └── QUALITY_SCORE.md            # Grades per domain × layer; tracks gaps
```

Details and full templates for each file are in `references/file-templates.md`. Read it before Phase 4.

## References

- `references/example-structure.md` — Annotated canonical tree with rationale for each node. Read during Phase 3.
- `references/file-templates.md` — Concrete templates for every file the skill produces, including front-matter conventions. Read during Phase 4.
- `references/analysis-guide.md` — Heuristics for extracting domains, layers, and providers from a codebase. Read during Phase 1 if the repo is large or unfamiliar.

## Common mistakes to avoid

- **Writing a giant AGENTS.md.** If you catch yourself putting conventions, rules, examples, and history all in AGENTS.md, stop. That's the failure mode the article explicitly warns against. Move content into `docs/` and leave a one-line pointer.
- **Copying the canonical layout literally.** The layout is a starting point. A CLI tool with no UI doesn't need `FRONTEND.md`. A prototype with no users doesn't need `product-specs/`. Omit what doesn't apply.
- **Inventing architecture.** If you can't tell from the code whether layer X depends on layer Y, write "Unverified — needs review" rather than guessing. Fabricated architecture docs are worse than missing ones because agents will act on them.
- **Skipping the existing-docs read.** Phase 2 is non-optional. Users whose docs you silently ignore will (rightly) be annoyed.
- **Forgetting verification status.** Every design doc needs `Status:` and `Last reviewed:` at the top. Without these, the docs rot invisibly.
- **Scaffolding empty directories.** `docs/exec-plans/active/` with no content is clutter. Either put a placeholder `README.md` explaining what goes there, or skip the directory until it's needed.
