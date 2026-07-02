---
name: wiki-history-ingest
description: >
  Unified entrypoint for ingesting agent/session history into the Obsidian wiki. Handles Codex, Copilot,
  Hermes, OpenClaw, and Pi inline; dispatches Claude to the dedicated claude-history-ingest skill. Use when
  the user says "/wiki-history-ingest <tool>" (claude | codex | copilot | hermes | openclaw | pi), or asks to
  mine past sessions of any of those agents — e.g. "process my Codex history", "add my Copilot sessions to the
  wiki", "ingest ~/.hermes", "process my OpenClaw history", "what have I worked on in Pi", "ingest ~/.pi",
  "import my agent history". Also triggers on mentions of ~/.codex rollouts, session-store.db, ~/.hermes
  memories, ~/.openclaw MEMORY.md, or ~/.pi/agent/sessions in the context of building the wiki.
  Use wiki-ingest (not this) for documents/URLs/text sources.
---

# Wiki History Ingest — Unified Agent Session Mining

One skill for **history sources** (agent/session logs). Documents and URLs go to `wiki-ingest` instead.
You extract *durable knowledge* from noisy session logs and compile it into the wiki — never dump transcripts.

## Dispatch

Invoked as `/wiki-history-ingest <tool>` (or `$wiki-history-ingest <tool>`). Resolve `<tool>`, then:

| `<tool>` | Handling |
|---|---|
| `claude` | **Invoke the `claude-history-ingest` skill** and stop — it owns its own richer workflow (desktop sessions, audit logs, codebase/initiative resolution). Do not run the workflow below. |
| `codex` | Run the Common Workflow inline using `references/codex-format.md` |
| `copilot` | Run the Common Workflow inline using `references/copilot-format.md` |
| `hermes` | Run the Common Workflow inline using `references/hermes-format.md` |
| `openclaw` | Run the Common Workflow inline using `references/openclaw-format.md` |
| `pi` | Run the Common Workflow inline using `references/pi-format.md` |
| `auto` / none | Infer from context (see Routing) |

### Routing when the tool isn't named explicitly
- A path hints the tool: `~/.codex`/rollout → codex · `~/.copilot`/`session-store.db`/copilot-chat → copilot · `~/.hermes` → hermes · `~/.openclaw`/MEMORY.md → openclaw · `~/.pi/agent/sessions` → pi · `~/.claude` → claude.
- If several tools are requested in one call (e.g. weekly-retro asks for "codex, pi, copilot, hermes, openclaw"), run the Common Workflow **once per tool, in sequence**.
- Ambiguous → ask one short question: "Which history: claude, codex, copilot, hermes, openclaw, or pi?"

## Common Workflow (codex · copilot · hermes · openclaw · pi)

Each tool differs **only** in how its data dir is laid out and parsed — that lives in `references/<tool>-format.md`. Everything else is identical and written here once.

### Step 0 — Absent-dir guard (do this first)
Resolve the tool's history path (`<TOOL>_HISTORY_PATH` from config, else the default in the reference). If the directory is missing or empty, **report `<tool>: absent, 0 pages` and return cleanly — no error, no narration.** This is the normal case for tools not installed on this machine (pi/hermes/openclaw are typically absent here; copilot often has no sessions).

### Step 1 — Resolve config & load state
Follow the Config Resolution Protocol in `llm-wiki/SKILL.md` (walk up CWD for `.env` → `~/.obsidian-wiki/config` → prompt) for `OBSIDIAN_VAULT_PATH` and `<TOOL>_HISTORY_PATH`. Read `.manifest.json` (what's already ingested) and `index.md` (what the wiki already covers) at the vault root.

### Step 2 — Survey & compute delta
Enumerate the tool's source files (per the reference's layout). Classify each against `.manifest.json`:
- **New** — not in manifest → ingest
- **Modified** — in manifest but the incremental marker (mtime / `updated_at` / index entry — see reference) is newer → re-ingest
- **Unchanged** — skip in append mode

**Append mode** (default) processes New+Modified only. **Full mode** (after `wiki-rebuild`, or on explicit request) processes everything. Report a one-line delta before deep parsing: `<tool>: N new, M modified, K unchanged`.

### Step 3 — Parse & distill (knowledge, not chronology)
Parse selected sources following `references/<tool>-format.md` (ranked sources, event/role fields, what to skip). Then:
- **Cluster by topic**, not by session — merge recurring themes across dates; split a mixed session into separate topics. One page per topic, never one page per session.
- **Distill the knowledge**, not the dialogue. No "on date X we discussed…"; state the fact/pattern/decision itself.
- **Privacy filter** — never copy raw transcripts verbatim; strip API keys, tokens, passwords, credentials; summarize command output that carries paths/env/secrets. If content is personal/sensitive and you cannot ask (ambient/retro runs), **skip or redact — never store-on-question**.

### Step 4 — Stage to `_raw/` and delegate placement to `wiki-ingest`
This skill distills and stages; **`wiki-ingest` owns all placement and writes** (it holds the initiative-vs-codebase decision — `projects/` is for initiatives, codebases live in `entities/<Repo>.md`; never create a catch-all `projects/<repo>/`). For each distilled piece, write a `_raw/` note titled as its intended target, with a placement hint in frontmatter (`codebase: <Repo>` for durable repo facts, or `project: <slug>` for initiative work; global concepts/skills/entities need no hint). Then **invoke `wiki-ingest`** to place them. On ambient/retro runs, do not create new initiatives — attach to an existing one or fall back to global.

### Step 5 — Writing rules (applied by wiki-ingest on the staged notes)
Every new page carries: a `summary:` field (1–2 sentences, ≤200 chars); `base_confidence: 0.42`, `lifecycle: draft`, `lifecycle_changed: <today>`. Leave `lifecycle`/`lifecycle_changed` untouched on update. Mark provenance: `^[extracted]` for claims grounded in explicit content (memories, compaction/checkpoint summaries), `^[inferred]` for patterns synthesized across sessions, `^[ambiguous]` when sources conflict; add a `provenance:` block summarizing the mix.

### Step 6 — Update manifest, log, index, hot.md
- `.manifest.json` — per processed source file: `ingested_at`, `size_bytes`, `modified_at`, the `source_type` from the reference, `pages_created`, `pages_updated`; plus the per-tool summary block shown in the reference.
- `index.md` and `log.md` — append the log line from the reference (`- [TS] <TOOL>_HISTORY_INGEST … mode=append|full`).
- `hot.md` — read it (create from the `wiki-ingest` template if missing), update **Recent Activity** with a one-line summary, keep the last 3 operations, and **bump the `updated:` frontmatter** (easy to forget).

### Step 7 — QMD refresh (only after vault writes)
QMD is a search index, not the source of truth. If `$QMD_WIKI_COLLECTION` is empty/unset, skip. Otherwise run `${QMD_CLI:-qmd} update` (then `${QMD_CLI:-qmd} embed` if it reports stale vectors), verify with `${QMD_CLI:-qmd} ls "$QMD_WIKI_COLLECTION"`. Report one of: `QMD refreshed: update (+embed) + verified` / `QMD skipped: collection unset` / `QMD skipped: cli unavailable` / `QMD failed: <error>`. Never roll back vault writes if QMD fails.

## Output contract (per tool)
Return: `<tool>: <P created / U updated> pages, <S> sessions` — or `<tool>: absent, 0 pages` / `<tool>: no new sessions`. weekly-retro Step 9 Phase A calls this once per tool and expects exactly this shape; a missing dir must never surface as an error.
