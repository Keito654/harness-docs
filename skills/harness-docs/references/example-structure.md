# Example docs structure (annotated)

This is the canonical target layout the skill aims at. It is based directly on the structure shown in OpenAI's *Harness engineering: leveraging Codex in an agent-first world* article. Each entry below includes **what it's for** and **when to include it**.

Treat this as a menu, not a recipe. Omit any node that doesn't match the repo you're documenting.

## Root-level files

### `AGENTS.md` — always create
The entry point an agent loads first. **Strict ~100 line budget.** Its job is to answer "where do I look?", not "what should I do?". Structure:

1. One-paragraph description of the repository (what it is, who uses it).
2. A "Start here" table: maps common agent tasks → which doc to read.
3. A terse index of `docs/` with one line per top-level entry.
4. Non-negotiable invariants (no hand-written code, dependency direction, etc.) — max 5 bullets. Anything longer goes into a design doc.

If you find yourself writing coding conventions, architectural explanations, or examples in AGENTS.md, stop and move them to `docs/design-docs/` with a pointer.

### `ARCHITECTURE.md` — always create
Top-level map. Covers:

- **Domains**: the business areas (auth, billing, onboarding, etc.).
- **Layers**: the fixed stack each domain is divided into (e.g. Types → Config → Repo → Service → Runtime → UI). Include a mermaid diagram if useful.
- **Dependency direction**: which layer can import from which.
- **Providers** (cross-cutting concerns): auth, telemetry, feature flags, connectors. Note that these are the *only* sanctioned way to cross domains.
- **Known exceptions**: places the architecture is violated, with links to the tech-debt tracker.

If the repo doesn't have a clear layered architecture, say so honestly. Write "Observed structure" and describe what's there. Don't invent layers that aren't enforced.

## `docs/` — the system of record

### `docs/design-docs/` — always create
One document per significant design decision. Examples: "why we use Zod at boundaries", "our approach to rate limiting", "how we handle idempotency".

- **`index.md`** (required): lists every design doc with a one-line summary and its verification status. Sorted with verified docs first, drafts/deprecated last.
- **`core-beliefs.md`** (required): short declarative statements the team stands by. Examples: "Parse data shapes at the boundary." "Prefer shared utility packages over bespoke helpers." "No YOLO with data — validate or use typed SDKs." Derived from core-beliefs the user mentions + principles you extract from existing docs.
- **`<topic>.md`** (as discovered): one file per design topic. Each has a `Status:` and `Last reviewed:` header.

### `docs/exec-plans/` — always create
Plans as first-class, versioned artifacts.

- **`active/`** — in-progress plans checked into the repo. On first scaffold, create a `.gitkeep` or `README.md` explaining what goes here. Don't fabricate plans.
- **`completed/`** — finished plans with decision logs. Same treatment initially.
- **`tech-debt-tracker.md`** (required): running list of known tech debt. Seed it with items you noticed during Phase 1 (e.g. "layer X depends on layer Y, should be reversed").

### `docs/generated/` — create only if applicable
Auto-generated documentation. Each file starts with a **DO NOT EDIT** banner and a pointer to the script that generates it.

- **`db-schema.md`** — if the project has a relational DB with migrations. On first scaffold, extract what you can from schema/migration files; if you can't, leave a placeholder with generation instructions.
- Other candidates: API route maps, event catalogs, permission matrices.

Skip this directory entirely if nothing in the repo can be auto-generated.

### `docs/product-specs/` — create if user-facing flows exist
Descriptions of what the product does, written from a user/flow perspective (not an implementation perspective).

- **`index.md`**: one-line summary per spec.
- **`<flow>.md`**: one per major flow (e.g. `new-user-onboarding.md`, `checkout.md`).

Skip for libraries, dev tools, or anything without end-user flows.

### `docs/references/` — create if there are major external deps
External library reference material, formatted for agent consumption. The typical pattern is `<library>-llms.txt` — a flattened, LLM-friendly dump of that library's docs.

- Create one placeholder per major framework/SDK (don't fetch actual docs in the scaffold — just note where it should come from).
- Examples from the original article: `design-system-reference-llms.txt`, `nixpacks-llms.txt`, `uv-llms.txt`.

Skip if the project has no significant external dependencies beyond stdlib.

### `docs/DESIGN.md` — create if the project has a UI
Visual/interaction design principles, design-system summary, link to component library, color/typography tokens. Short — detail goes into the design system's own repo or `docs/references/design-system-reference-llms.txt`.

### `docs/FRONTEND.md` — create if the project has a UI
Frontend-specific conventions: state management, routing, data fetching, component structure, styling approach. One page max; detail goes into design docs.

### `docs/PLANS.md` — always create
Index into `exec-plans/`. A rendered view: active plans by owner/date, recently completed, link to tech-debt-tracker. Can be regenerated periodically.

### `docs/PRODUCT_SENSE.md` — optional
Product principles, taste, voice, non-goals. Useful when agents make product decisions autonomously. Skip for pure infrastructure or tooling projects.

### `docs/QUALITY_SCORE.md` — always create
Grades each product domain × architectural layer. Tracks gaps over time. Seed with honest assessments from Phase 1:

| Domain | Types | Config | Repo | Service | Runtime | UI |
|--------|-------|--------|------|---------|---------|-----|
| auth | A | B | B | C | — | — |
| billing | — | — | — | — | — | — |

Use A/B/C/D grades or similar. The point is to make the gap visible so future work is prioritized.

## What NOT to create

Avoid these — they signal misunderstanding of the pattern:

- **`docs/API.md`** as a blob. Either auto-generate into `generated/` or split per-domain.
- **`docs/GLOSSARY.md`**. If terms need definition, define them inline in the relevant design doc and link back. Central glossaries rot.
- **`docs/TODO.md`**. Use `tech-debt-tracker.md` — it's the same idea done better.
- **`docs/HISTORY.md`** or `CHANGELOG.md` (inside docs/). Changelogs belong at the root, not inside docs.
- **Deeply nested hierarchies**. If a section needs 3+ levels of directory nesting, the boundary is probably wrong. Flatten.

## Sizing heuristics

Rough targets. Not rules, but if you're far outside these, reconsider:

| File | Target size |
|------|-------------|
| AGENTS.md | 80–120 lines |
| ARCHITECTURE.md | 150–300 lines |
| Any `index.md` | 20–60 lines |
| core-beliefs.md | 30–80 lines |
| Individual design doc | 60–200 lines |
| Individual product spec | 40–150 lines |
| QUALITY_SCORE.md | 30–100 lines |
