# Codebase analysis guide

Heuristics for Phase 1 — extracting the facts needed to populate the docs. Read this when the repo is large, unfamiliar, or in a language you rarely work with.

## What you actually need to extract

Don't try to understand everything. The docs layout needs these specific facts:

1. **What is this?** One-paragraph description.
2. **What are the domains?** Business areas, not technical concerns.
3. **What layers exist within a domain?** And which way do imports flow?
4. **What are the cross-cutting providers?** Auth, logging, feature flags, etc.
5. **What's already documented, and where?** So you don't duplicate.
6. **What obvious tech debt is visible?** Seeds for `tech-debt-tracker.md`.
7. **What are the external dependencies that agents will need reference for?** Populates `references/`.

Nothing else. Don't read every file.

## Discovery sequence

### Step 1: Shape of the repo

Start with a depth-2 listing. Look for:

- **Monorepo signals**: `packages/`, `apps/`, `services/`, `workspaces` in package.json/pyproject.toml, `Cargo.toml` with `[workspace]`, `go.work`, `pnpm-workspace.yaml`.
- **Single-package signals**: one `src/`, one lockfile, no nested manifests.
- **Language**: dominant file extension and any `Dockerfile`/`go.mod`/`Cargo.toml`/`pyproject.toml`/`package.json`/`Gemfile`/etc.
- **Tests**: `test/`, `tests/`, `__tests__/`, `spec/`, `_test.go` files, etc.
- **CI**: `.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, `Jenkinsfile`.
- **Infra**: `terraform/`, `k8s/`, `deploy/`, `infra/`.

Note what you see. Don't read the files yet.

### Step 2: Find the entry points

The entry points tell you the runtime shape. Look for:

- Scripts in `package.json` (`"scripts"`), `Makefile` targets, `Justfile`, `Taskfile.yml`.
- `main.*`, `index.*`, `app.*`, `server.*`, `cli.*`, `bin/*`, `cmd/*/main.go`.
- A `Dockerfile`'s `CMD` / `ENTRYPOINT`.

Read the one or two most likely entry points. They'll reveal:
- Whether this is a web service, CLI, worker, library, or desktop app.
- What framework (Express/Fastify, FastAPI/Flask, Axum, Actix, Rails, etc.).
- What the top-level control flow looks like.

### Step 3: Identify domains

Inside `src/` (or equivalent), top-level directories are your first candidates for **domains**. Distinguish:

- **Business domains** — named after what the product does: `auth/`, `billing/`, `onboarding/`, `search/`, `orders/`, `inventory/`.
- **Technical concerns** — named after *how*: `db/`, `http/`, `cache/`, `queue/`, `telemetry/`, `utils/`.

The first list goes into `ARCHITECTURE.md` as domains. The second list mostly becomes providers or infrastructure notes.

When in doubt: if the directory name would make sense to a product manager, it's a domain. If only engineers would recognize it, it's a technical concern.

### Step 4: Detect layering

Inside one domain, look at its files and imports. Look for consistent patterns:

- Files named `types.*`, `schema.*`, `model.*` → Types layer.
- `config.*`, `settings.*` → Config layer.
- `repo.*`, `repository.*`, `dao.*`, `store.*` → Data-access layer.
- `service.*`, `logic.*`, `usecase.*` → Business-logic layer.
- `runtime.*`, `wiring.*`, `container.*`, `app.*` → Runtime/wiring.
- `ui/`, `components/`, `views/`, `pages/` → UI layer.
- `handler.*`, `controller.*`, `route.*` → HTTP/API edge (may be a layer or a cross-cutting concern).

If you see these names consistently across domains, there's an enforced layering. If each domain does its own thing, write that down — "Observed: no consistent layering" — and don't fake one in `ARCHITECTURE.md`.

**Check import direction** by grep/sample: do imports in `service.*` files only reference `repo.*` and `types.*`, or do they also pull from `ui/`? If there's no direction, say so.

### Step 5: Find the providers

Cross-cutting concerns are things many domains use but none own. Signs:

- A module imported from many places but importing little itself (leaf-ish).
- Directories named `providers/`, `context/`, `middleware/`, `plugins/`.
- Singleton-ish objects: a single `logger`, `telemetry`, `featureFlags`, `authContext`.

List these by name. They go into `ARCHITECTURE.md` under "Cross-cutting providers".

### Step 6: Inventory existing docs

- All `*.md` at any depth.
- `README` / `README.*`.
- `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.
- `docs/`, `doc/`, `documentation/`, `wiki/`.
- `adr/`, `decisions/`, `rfcs/`.
- Top comments in key source files — sometimes the real architecture doc is a comment block in `main.*`.

Read the first page of each. Note:
- **Facts** that should survive into the new docs.
- **Principles** that feed `core-beliefs.md`.
- **Staleness** — claims that don't match the code. These become tech-debt items or prompts to the user.

### Step 7: Spot tech debt

Grep for these signals:

- `TODO`, `FIXME`, `XXX`, `HACK`, `@deprecated`, `// NOTE:` in code.
- Ignored tests, `.skip(`, `xit(`, `@Ignore`.
- Long functions (>200 lines in one file without clear structure).
- Circular imports or very deep import graphs in one domain.
- Two implementations of the same concept (two loggers, two HTTP clients).
- `any` / `unknown` in typed languages at high frequency.

Write the top 5–10 items into `tech-debt-tracker.md` as seed. Be specific (file path + one-line description). Don't invent; only list what you saw.

### Step 8: Note the external dependencies

From the package manifest: list dependencies that are either (a) core frameworks agents will repeatedly need to reason about (e.g. React, FastAPI, Rails, Axum), or (b) unusual enough that agents are likely to get them wrong.

These become `docs/references/<lib>-llms.txt` placeholders — one per library, with a pointer to where current reference material should be pulled from.

Skip stdlib, test libraries, and small utilities.

## When to stop analyzing

The point of Phase 1 is *enough* understanding, not *full* understanding. Stop when you can:

- Write `AGENTS.md` "Repository layout" and "Start here" sections.
- List domains and (if applicable) layers for `ARCHITECTURE.md`.
- Name the providers.
- Identify 3–10 tech debt items.
- List which existing docs to preserve/link to.

If you can do those five things, move to Phase 2. Going deeper is usually procrastination.

## Ambiguity and honesty

The biggest failure mode is inventing structure that isn't there. Three rules:

1. **If you can't verify, say so.** Write "Observed" or "Unverified — needs human review" rather than guessing. Agents will act on fabricated docs.
2. **If the repo doesn't have something, skip the doc.** Don't create empty `product-specs/` for a CLI tool. Don't create `FRONTEND.md` for a data pipeline.
3. **If you're not sure whether to include something, ask the user.** A short question at the Phase 3 checkpoint saves bad output.

## Language and conventions

Match the repo's primary language for all doc content. If existing docs are in Japanese, the new docs should also be in Japanese. If the repo is mostly English with one Japanese README, match per-file based on what the neighboring content uses.

Code identifiers, filenames, and technical terms (API, SDK, HTTP) stay in their original form regardless of surrounding language.
