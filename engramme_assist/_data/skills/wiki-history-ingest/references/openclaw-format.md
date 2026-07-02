# OpenClaw — data format

**Path:** `OPENCLAW_HISTORY_PATH`, default `~/.openclaw`. Typically **absent on this machine** → report absent, 0 pages.

## Layout
```
~/.openclaw/
├── workspace/MEMORY.md                 # long-term durable memory — highest signal
├── workspace/DREAMS.md                 # optional end-of-day summaries — supplement
├── workspace/memory/YYYY-MM-DD.md      # daily notes (today+yesterday auto-loaded)
├── agents/<agentId>/sessions/sessions.json   # session index [{id,name,created_at,updated_at,message_count}]
├── agents/<agentId>/sessions/<id>.jsonl      # transcripts (append-only JSONL)
├── credentials/                        # skip entirely
└── openclaw.json                       # global config (agents.defaults.workspace) — metadata
```

## Delta markers
Enumerate `MEMORY.md`, `DREAMS.md`, `workspace/memory/*.md`, `sessions.json`, `sessions/*.jsonl`. New = not in manifest; Modified = file mtime (or `updated_at` in `sessions.json`) newer than `ingested_at`.

## Parsing
1. **`MEMORY.md` first** — plain markdown, no fixed frontmatter (sections like User Preferences / Projects / Patterns). Read fully, extract concept-level knowledge, cluster by topic (never one entry = one page).
2. **Daily notes** — prioritise recent (last 30–90 days); older files have sharply diminishing signal (summarize in bulk). Extract active project context, decisions, solved blockers.
3. **`DREAMS.md`** — skim for novel insights not already in MEMORY.md.
4. **Session JSONL** — `{role: user|assistant|tool|tool_result, content, timestamp}`; `role` is the dispatch field; cross-reference `sessions.json` for names before opening transcripts. Keep assistant conclusions; tool pairs are context only.

## Gotchas
- Telegram-topic sessions are named `<sessionId>-topic-<threadId>.jsonl` — same schema, parse identically.
- `content` may be a string or a structured multi-part object.
- Bootstrap files (`AGENTS.md`/`SOUL.md`/`USER.md`/…) are truncated at `bootstrapMaxChars` (default 20000).

## Manifest & log
- `source_type`: `openclaw_memory` | `openclaw_daily_note` | `openclaw_session` | `openclaw_dreams`; add `agent_id` when applicable.
- Per-tool block `openclaw`: `{source_path, last_ingested, memory_updated_at, daily_notes_ingested, sessions_ingested, pages_created, pages_updated}`.
- log.md: `- [TS] OPENCLAW_HISTORY_INGEST memory=updated daily_notes=N sessions=M pages_updated=X pages_created=Y mode=append|full`
- hot.md example: "Ingested OpenClaw MEMORY.md + N daily notes; automation and multi-agent coordination patterns."
