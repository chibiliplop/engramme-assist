# Hermes — data format

**Path:** `HERMES_HISTORY_PATH`, default `~/.hermes` (or `$HERMES_HOME`). Typically **absent on this machine** → report absent, 0 pages.

## Layout
```
~/.hermes/
├── memories/*.md | *.json        # persistent curated memories — highest signal
├── sessions/YYYY-MM-DD/<id>.jsonl # transcripts (only if logging.sessions: true)
├── skills/<name>/SKILL.md         # installed skills — skip (source material, not knowledge)
├── config.yaml                    # model, paths, logging flags — metadata only
└── .hub/                          # lock.json / audit.log / quarantine — skip entirely
```

## Delta markers
Enumerate `memories/` + `sessions/**/*.jsonl`. New = not in manifest; Modified = file mtime newer than `ingested_at`.

## Parsing
**Memories first (highest value).** Two shapes:
- Markdown `*.md`: optional frontmatter (`tags`, `created_at`, `project`) + prose body. `tags` → wiki tags (kebab-case); `project` → route to `projects/<project>/`.
- JSON `*.json`: `{content, created_at, tags, project, source}` — same semantics; `source` links back to a session.
Extract the core claim per memory and **merge into the right existing page** — never one memory = one page.

**Session JSONL** (if present): first line `{type: session_meta, id, cwd, model, started_at}` — `cwd` is the best project signal. Turns: `{role: user|assistant, content}`; `{type: tool_use, name, input}` / `{type: tool_result, content}` = context only. Keep assistant conclusions/decisions; skip low-info follow-ups and tool plumbing.

## Value ranking
1. `memories/*.md` 2. `memories/*.json` 3. `sessions/**/*.jsonl` assistant turns. Skip `.hub/`, `skills/`, `config.yaml`.

## Gotchas
- Sessions exist only when `config.yaml: logging.sessions: true` — memory-only installs are normal.
- Redact secrets; summarize, don't quote transcripts verbatim.

## Manifest & log
- `source_type`: `hermes_memory` | `hermes_session`.
- Per-tool block `hermes`: `{source_path, last_ingested, memories_ingested, sessions_ingested, pages_created, pages_updated}`.
- log.md: `- [TS] HERMES_HISTORY_INGEST memories=N sessions=M pages_updated=X pages_created=Y mode=append|full`
- hot.md example: "Ingested N Hermes memories and M sessions; themes: reasoning strategies, tool-use patterns."
