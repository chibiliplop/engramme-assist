# Codex — data format

**Path:** `CODEX_HISTORY_PATH`, default `~/.codex`. If absent → report absent, 0 pages.

## Layout
```
~/.codex/
├── sessions/YYYY/MM/DD/rollout-<ts>-<id>.jsonl   # primary structured session logs
├── archived_sessions/                            # archived rollouts (only if user asks)
├── session_index.jsonl                           # {id, thread_name, updated_at} — one/line
├── history.jsonl                                 # transcript history (config-dependent) — fallback
├── config.toml                                   # history.persistence, history.max_bytes
└── state_*.sqlite / logs_*.sqlite                # runtime DBs — skip
```

## Delta markers
- Enumerate `session_index.jsonl` (inventory backbone: id, title, freshness) + `sessions/**/rollout-*.jsonl`.
- New = not in manifest; Modified = file mtime (or `updated_at` in the index) newer than `ingested_at`.

## Parsing rollout JSONL
Each line is an envelope: `{timestamp, type, payload}`. `type` ∈ `session_meta | turn_context | event_msg | response_item`.
- **Keep:** `response_item` messages (user intent, assistant conclusions/decisions); high-signal tool outputs encoding reusable knowledge.
- `event_msg.payload.type` of interest: `user_message`, `agent_message`; skip `token_count`, `exec_command_end` plumbing.
- `session_meta` = metadata (id, cwd, model) — use `cwd` for project scope, not as knowledge.
- **Skip:** telemetry (`token_count`), reasoning traces, verbose exec dumps with no durable insight.

## Value ranking
1. `session_index.jsonl` (inventory) 2. `sessions/**/rollout-*.jsonl` (rich) 3. `history.jsonl` (timeline fallback).

## Gotchas
- `codex exec --ephemeral` runs may not persist rollout files; `history.persistence = "none"` in `config.toml` disables history entirely — expect gaps.
- Rollouts embed injected instructions/tool payloads/secrets — redact, never quote verbatim.

## Manifest & log
- `source_type`: `codex_rollout` | `codex_index` | `codex_history`.
- Per-tool summary block key `codex`: `{source_path, last_ingested, sessions_ingested, sessions_total}`.
- log.md: `- [TS] CODEX_HISTORY_INGEST sessions=N pages_updated=X pages_created=Y mode=append|full`
- hot.md example: "Ingested N Codex sessions; recurring patterns in CLI tooling and shell scripting."
