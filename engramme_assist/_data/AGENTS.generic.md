# Obsidian Wiki — Agent Context

A **skill-based framework** for building and maintaining an Obsidian knowledge base. No scripts or dependencies — everything is markdown instructions that you execute directly.

## Configuration

Resolve config using the Config Resolution Protocol in `llm-wiki/SKILL.md`:

1. **Walk up from CWD** — look for a `.env` file in the current directory, then each parent, up to `$HOME`. Stop at the first `.env` that contains `OBSIDIAN_VAULT_PATH`.
2. **Global config** — if no local `.env` is found, read `~/.obsidian-wiki/config`.
3. **Prompt setup** — if neither exists, tell the user to run `wiki-init`.

The resolved config sets `OBSIDIAN_VAULT_PATH` (where the wiki lives). It may also set `OBSIDIAN_WIKI_REPO` (where this repo is cloned) and other optional variables.

**After reading config, always read `$OBSIDIAN_VAULT_PATH/AGENTS.md` if it exists.** It contains owner-specific conventions (domain vocabulary, ingest preferences, writing style, project scoping) that override framework defaults for all skills. Apply it for the duration of the session.

## Chargement du profil (résolution étendue)

Au démarrage de session, après avoir résolu `OBSIDIAN_VAULT_PATH`, charge le profil et garde-le
en contexte pour toute la session :

1. Lire `~/.obsidian-wiki/profile.yml` (global — identité).
2. Lire `$OBSIDIAN_VAULT_PATH/_meta/profile.yml` (vault) et **merger** par-dessus le global
   (le vault écrase le global, clé par clé).
3. Lire `$OBSIDIAN_VAULT_PATH/AGENTS.md` (conventions).

Les skills référencent les valeurs du profil par notation moustache `{{profile.*}}`
(ex. `{{profile.owner.name}}`, `{{profile.sources.slack.user_id}}`, `{{profile.brief.scoring_axes}}`).
Résous chaque `{{profile.*}}` depuis le profil mergé. Si un champ requis manque, demande-le une
fois et propose de l'écrire dans le profil (via la skill `wiki-profile`).

Si aucun `profile.yml` n'existe, invite à lancer `wiki-init` (ou `wiki-profile`).

## Vault Structure

```
$OBSIDIAN_VAULT_PATH/
├── index.md                # Master index — every page listed, always kept current
├── log.md                  # Chronological activity log (ingests, updates, lints)
├── hot.md                  # Session hot cache — ~500-word semantic snapshot of recent activity
├── .manifest.json          # Tracks every ingested source: path, timestamps, pages produced
├── _meta/
│   ├── taxonomy.md         # Controlled tag vocabulary
│   └── *.base              # Obsidian Bases dashboard definitions (wiki-dashboard skill)
├── _insights.md            # Graph analysis output (hubs, bridges, dead ends)
├── _raw/                   # Staging area — drop rough notes here, next ingest promotes them
├── concepts/               # Abstract ideas, patterns, mental models
├── entities/               # Concrete things — people, tools, libraries, companies
├── skills/                 # How-to knowledge, techniques, procedures
├── references/             # Factual lookups — specs, APIs, configs
├── synthesis/              # Cross-cutting analysis connecting multiple concepts
├── journal/                # Time-bound entries — daily logs, session notes
└── projects/
    └── <project-name>/      # One folder per project synced via wiki-update
        ├── <project-name>.md   # Project overview/hub page (named after the project)
        ├── concepts/           # Project-specific ideas, architectures
        ├── skills/             # Project-specific how-tos, patterns
        └── references/         # Project-specific source summaries
```

Every wiki page has required frontmatter: `title`, `category`, `tags`, `sources`, `created`, `updated`. Pages connect via internal links — `[[wikilinks]]` by default, or standard Markdown links when `OBSIDIAN_LINK_FORMAT=markdown` is set in config.

## Project Scoping — initiative vs codebase

`projects/` holds **initiatives**, never codebases. The two are distinct natures and must not be mixed (a repo aggregates dozens of unrelated efforts → a catch-all):

- **Initiative → `projects/<slug>/`** — a *bounded* effort (goal, status, team, often a tracker key). Frontmatter: `team:` (wikilink to a team entity), `status:` (`active` | `done` | `paused`), `codebases:` (the repo[s] it touches), tracker key (if known). `review_due` = `updated` + 14 days.
- **Codebase → `entities/<Repo>.md`** — a *durable* repo/library that persists and accrues work across many initiatives. `category: entities`, `tags: [codebase, …]`, `review_due` = +90 days, **no `team:`** (a shared repo belongs to no single squad), **no hardcoded `## Key Projects` list** (backlinks from initiatives replace it). Durable facts live here: git path, architecture, harness setup, conventions, build/test.

`team:` uses the **functional team name** (not a rotating codename, which stays as an `aliases:` entry on the team entity). If an initiative needs a team that has no entity yet, ask and create the team entity.

**Effect on `wiki-update`**: run from a repo, it updates the **codebase entity** (durable facts) and creates/updates the relevant **initiatives** separately — never a catch-all `projects/<repo>/` folder. Session-log noise (one-off debugging, meeting prep, MR chatter) does not belong on the codebase entity; it is distilled into the relevant initiative or dropped.

## Skill Routing

Skills live in `.skills/<name>/SKILL.md`. Match the user's intent to the right skill:

| User says something like… | Skill |
|---|---|
| "set up my wiki" / "initialize" / "initialise mon wiki" | `wiki-init` |
| "update my profile" / "change my channels" / "add a Slack channel" / "mets à jour mon profil" | `wiki-profile` |
| "/jot <text>" / "quick note" / "remember that…" / "capture this for me" / "note rapide" | `jot` |
| "/weekly-retro" / "retro" / "weekly review" / "bilan de la semaine" | `weekly-retro` |
| "/morning-brief" / "morning briefing" / "daily brief" / "brief du matin" | `morning-brief` |
| "/wiki-history-ingest claude" / "/wiki-history-ingest codex" / "/wiki-history-ingest hermes" / "/wiki-history-ingest pi" | `wiki-history-ingest` |
| "ingest" / "add this to the wiki" / "process these docs" / "process this export" / "ingest this data" / logs, transcripts / "/ingest-url <url>" / "add this URL" / "ingest this link" / "save this page" | `wiki-ingest` |
| "import my Claude history" / "mine my conversations" | `claude-history-ingest` |
| "import my Codex history" / "mine my Codex sessions" | `codex-history-ingest` |
| "import my Hermes history" / "mine my Hermes memories" / "ingest ~/.hermes" | `hermes-history-ingest` |
| "import my OpenClaw history" / "mine my OpenClaw sessions" / "ingest ~/.openclaw" | `openclaw-history-ingest` |
| "import my Copilot history" / "mine my Copilot sessions" / "ingest ~/.copilot" | `copilot-history-ingest` |
| "import my Pi history" / "mine my Pi sessions" / "ingest ~/.pi" | `pi-history-ingest` |
| "what's the status" / "what's been ingested" / "show the delta" | `wiki-status` |
| "wiki insights" / "hubs" / "wiki structure" | `wiki-status` (insights mode) |
| "what do I know about X" / "find info on Y" / any question | `wiki-query` |
| "audit" / "lint" / "find broken links" / "wiki health" | `wiki-lint` |
| "dedup my wiki" / "find duplicate pages" / "merge duplicates" / "identity resolution" / "consolidate my wiki" | `wiki-dedup` |
| "rebuild" / "start over" / "archive" / "restore" | `wiki-rebuild` |
| "link my pages" / "cross-reference" / "connect my wiki" | `cross-linker` |
| "fix my tags" / "normalize tags" / "tag audit" | `tag-taxonomy` |
| "update wiki" / "sync to wiki" / "save this to my wiki" | `wiki-update` |
| "export wiki" / "export graph" / "graphml" / "neo4j" / "export to OKF" / "OKF bundle" / "open knowledge format" | `wiki-export` |
| "import wiki" / "import from export" / "load graph.json" / "import vault" / "import OKF bundle" / "/wiki-import" | `wiki-import` |
| "color my graph" / "color code obsidian" / "color by tag/category/visibility" | `graph-colorize` |
| "save this" / "/wiki-capture" / "capture this" / "file this conversation" / "/wiki-capture --quick" / "quick capture" / "capture this finding" / "save this gotcha" / "drop to raw" | `wiki-capture` |
| "/wiki-research [topic]" / "research X" / "find everything about Y" | `wiki-research` |
| "create a dashboard" / "vault dashboard" / "show all X as a table" / "dynamic view" | `wiki-dashboard` |
| "synthesize my wiki" / "find connections" / "what concepts keep coming up together" / "/wiki-synthesize" | `wiki-synthesize` |
| "create a new skill" | `skill-creator` |
| "/vault-skill-factory" / "make a skill from my wiki" / "turn these pages into a skill" / "package my notes on X as a skill" / "build a domain-expert skill from my vault" | `vault-skill-factory` |
| "/wiki-claude [topic]" / "/wiki-codex [topic]" / "/wiki-hermes [topic]" / "/wiki-openclaw [topic]" / "/wiki-copilot [topic]" / "/wiki-pi [topic]" | `wiki-agent` |
| "/memory-bridge" / "browse codex memory" / "what did codex know about X" / "compare tool memories" / "cross-tool memory" | `memory-bridge` |
| "/daily-update" / "morning sync" / "refresh the wiki index" / "set up the daily cron" / "install terminal notification" | `daily-update` |
| "/impl-validator" / "check this implementation" / "validate what you did" / "is this correct?" | `impl-validator` |
| "/wiki-switch NAME" / "switch to my work wiki" / "switch vault" / "change wiki" / "list my wikis" / "show my vaults" / "create a new vault config" | `wiki-switch` |
| "/wiki-digest" / "what did I learn this week" / "weekly digest" / "knowledge summary" / "what's new in my wiki" / "summarize my recent learning" / "monthly review" | `wiki-digest` |
| "/wiki-verify" / "valide l'inféré" / "vérifie ce qui est incertain" / "passe en revue les pages non sûres" / "promote verified pages" / "what needs validating" | `wiki-verify` |

## Cross-Project Usage

The main use case: you're working in some other project and want to sync knowledge into your wiki or query it. Two global skills handle this — `wiki-update` and `wiki-query`. They work from any directory.

### wiki-update (write to wiki)

1. Resolve config using the Config Resolution Protocol to get `OBSIDIAN_VAULT_PATH`
2. Scan the current project: README, source structure, git log, package metadata
3. Distill what's worth remembering (architecture decisions, patterns, trade-offs — not code listings)
4. Write to `$VAULT/projects/<project-name>/` (overview in `<project-name>.md`, deeper notes in the folder's `concepts/`, `skills/`, `references/`), cross-linking to concept/entity pages as needed
5. Update `.manifest.json`, `index.md`, and `log.md`

On repeat runs, it checks `last_commit_synced` in `.manifest.json` and only processes the delta via `git log <last_commit>..HEAD`.

### wiki-query (read from wiki)

1. Resolve config using the Config Resolution Protocol to get `OBSIDIAN_VAULT_PATH`
2. Scan titles, tags, and `summary:` frontmatter fields first (cheap pass)
3. Only open page bodies when the index pass can't answer
4. Return a synthesized answer with `[[wikilink]]` citations

## Visibility Tags (optional)

Pages can carry a `visibility/` tag to mark their intended reach. **This is entirely optional** — untagged pages behave exactly as they always have (visible everywhere). The system stays single-vault, single source of truth.

| Tag | Meaning |
|---|---|
| *(no tag)* | Same as `visibility/public` — visible in all modes |
| `visibility/public` | Explicitly public — visible in all modes |
| `visibility/internal` | Team-only — excluded when querying in filtered mode |
| `visibility/pii` | Sensitive data — excluded when querying in filtered mode |

**Filtered mode** is opt-in, triggered by phrases like "public only", "user-facing answer", "no internal content", or "as a user would see it" in a query. Default mode shows everything.

`visibility/` tags are **system tags** — they don't count toward the 5-tag limit and are listed separately from domain/type tags in the taxonomy.

See `wiki-query` and `wiki-export` skills for how the filter is applied.

## Core Principles

- **Compile, don't retrieve.** The wiki is pre-compiled knowledge. Update existing pages — don't append or duplicate.
- **Track everything.** Update `.manifest.json` after ingesting, `index.md`, `log.md`, and `hot.md` after any write operation.
- **Connect with `[[wikilinks]]`.** Every page should link to related pages. This is what makes it a knowledge graph, not a folder of files.
- **Frontmatter is required.** Every wiki page needs: `title`, `category`, `tags`, `sources`, `created`, `updated`.
- **Single source of truth.** Visibility tags shape how content is surfaced — they don't duplicate or separate it.
- **Keep context warm.** `hot.md` is a ~500-word semantic snapshot of recent activity. Every write skill updates it so the next session can pick up where the last one left off without crawling the full vault.
- **Concision over noise — keep the wiki coherent, never a fourre-tout.** Every edit must add signal. Specifically:
  - **No refutation traces.** When a claim is wrong, delete it — never write "X réfuté (retiré)" or annotate what was removed.
  - **No who/how meta.** Don't add `lifecycle_reason` (or prose) like "human-edited … via wiki-verify — corrigé par le propriétaire". The editor is always the owner and the tool/date is irrelevant to the knowledge.
  - **No negative phrasing.** State what *is*, delete what *isn't*. If a person reports to A (not B), remove them from B's page — don't keep them with "(et non directement à B)".
  - Facts belong in the body and `summary`; frontmatter meta and contrastive notes are clutter. Prune marginal links rather than accumulate them.

## Data Lifecycle

The vault must stay dense, current, and bounded: growth comes from pages absorbing facts, not from page count. Three mechanisms enforce this — frontmatter conventions every write skill applies, an ingest discipline, and a daily gardener pass in `daily-update`.

### Review horizon (`review_due`)

Every page in a knowledge category carries two lifecycle fields:

```yaml
review_due: 2026-09-10     # updated + category half-life (table below)
last_verified: 2026-06-12  # last time content was checked against reality
```

| Category | review_due offset |
|---|---|
| `projects/` | +14 days |
| `entities/` | +90 days |
| `references/` | +180 days |
| `skills/` | +180 days |
| `synthesis/` | +270 days |
| `concepts/` | +365 days |
| `journal/`, `retros/` | none — immutable archives |

Any skill that creates or substantively updates a page recomputes `review_due` from today. A page past `review_due` is *due for review*, not wrong — `daily-update` surfaces it; `wiki-verify` and re-ingests clear it by bumping `last_verified`.

### Ingest discipline — absorb, don't accumulate

For every fact extracted at ingest, classify explicitly before writing:

- **UPDATE** (default) — an existing page covers this entity/concept: it absorbs the fact. Bump `updated`, recompute `review_due`.
- **ADD** — no existing page covers it (check `index.md` + QMD first). Creating a page is the exception, not the rule.
- **DELETE** — the new fact contradicts existing content: replace it (consistent with "state what is, delete what isn't").
- **NOOP** — already known; touch nothing.

For evolving facts (a person's role, a project's status), prefer dated fields over prose history: `role: Head of B2C` + `role_since: 2026-04`.

### Programmatic-first

If an operation is mechanical (date comparisons, file enumeration, frontmatter field checks, link counting, index generation), it is done by a script — never by LLM file crawling. The scripts live in `_meta/scripts/`:

- `gardener.py` — the whole gardener pass: `_raw/` TTL, review-due audit, archiving, auto-promotion, `index.md` rebuild. `--apply` mutates, default is dry-run, `--check` validates a run, `--skip-if-fresh` short-circuits when nothing changed.
- `insights.py` — link-graph stats (`--apply` rewrites `_insights.md`, preserving the LLM-written Observations/Questions sections).

LLMs interpret script output and write prose (hot.md, observations, briefs); they do not re-implement what the scripts do. If a script errors, fix or flag it — don't silently fall back to manual crawling.

### Skill ownership (no overlapping fixes)

- **Identity & alias normalization belongs to `wiki-dedup` only.** `wiki-lint --consolidate` must not rename aliases or merge identities — it owns links, frontmatter, tags-format and contradiction call-outs.
- **Graph stats belong to `insights.py`** — `wiki-status` insights mode runs the script and adds interpretation, it does not recount links.

### Gardener rules (applied by `daily-update`)

- **`_raw/` TTL** — a staged file already promoted (tracked in `.manifest.json`) and older than 7 days is deleted. Unpromoted and older than 14 days: flagged once in the report, moved to `_archives/` on the next pass.
- **`index.md` is derived** — rebuilt from page frontmatter on every pass, never patched by diff appends. It is an artifact, not a source of truth.
- **Archiving** — a page 60+ days past `review_due`, with no inbound wikilinks, moves to `_archives/YYYY-MM/` (inbound references already absent by definition). Archives stay greppable but leave `index.md` and the QMD collection.
- **Auto-promotion** — `lifecycle: draft` → `reviewed` when `base_confidence ≥ 0.8`, no `^[inferred]`/`^[ambiguous]` markers remain in the body, and the page cites ≥2 sources. Promotion to `verified` stays human-only, via `wiki-verify`.

## Architecture Reference

For the full pattern (three-layer architecture, page templates, project org), read `.skills/llm-wiki/SKILL.md`.

The vault format is structurally conformant with the [Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — markdown files with YAML frontmatter, category subfolders, reserved `index.md`/`log.md`. `wiki-export` (OKF mode) and `wiki-import` are the bridge: they translate between our native frontmatter (`title`/`category`/`tags`/`sources`/`created`/`updated` + `summary`) and OKF (`type`/`title`/`description`/`resource`/`tags`/`timestamp`), making vaults exchangeable with any OKF tool. The OKF round-trip is lossless; the `graph.json` round-trip is not.
