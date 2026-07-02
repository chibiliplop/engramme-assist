# GitHub Copilot CLI — data format

**Paths:** `COPILOT_HISTORY_PATH` (default `~/.copilot/session-state`), the global DB `~/.copilot/session-store.db`, and `COPILOT_VSCODE_STORAGE_PATH` (VS Code `workspaceStorage`; platform-specific — ask if absent). If none exist → report absent, 0 pages. On this machine Copilot usually has **no session data** — expect the absent path.

## Three sources (scan all present ones)
1. **`session-store.db` (SQLite) — highest value.** Canonical, pre-summarised. Tables: `sessions(id, cwd, repository, branch, summary, created_at, updated_at, host_type)`, `turns(session_id, turn_index, user_message, assistant_response, timestamp)`, `checkpoints(session_id, checkpoint_number, title, overview, history, work_done, technical_details, important_files, next_steps, created_at)`, `session_files(session_id, file_path, tool_name, turn_index, first_seen_at)`, `session_refs(session_id, ref_type, ref_value)`, `search_index` (FTS5).
2. **`~/.copilot/session-state/<uuid>/`** — `workspace.yaml` (id, cwd, summary_count, created_at, updated_at), `vscode.metadata.json` (workspaceFolder, repositoryProperties, `customTitle` = best session label), `events.jsonl`, `index.md` (session-end summary), `checkpoints/*.json`.
3. **VS Code `<hash>/GitHub.copilot-chat/`** — `transcripts/<uuid>.jsonl` (same format as `events.jsonl`), `memory-tool/memories/<base64-session-id>/plan.md` (user-authored; decode name with `base64.b64decode(name+'==')`).

## Delta markers
One entry per session UUID (unify across the three sources). New = not in manifest; Modified = `sessions.updated_at` (or `workspace.yaml` `updated_at`) newer than `ingested_at`.

## Parsing & value ranking
Process pre-distilled content first: **checkpoints** (`overview`/`work_done`/`technical_details`/`important_files`/`next_steps` = gold) → `sessions.summary` + `index.md` → **memory artifacts** (`plan.md`, treat as user-authored/extracted) → `turns` → `events.jsonl`. In `events.jsonl`: keep `user.message.data.content` (not `transformedContent`) and `assistant.message.data.content`; skim `data.toolRequests` for file/command patterns (ignore `report_intent`). **Skip `data.reasoningOpaque` and `data.reasoningText` entirely** (internal reasoning) and `tool.execution_end`.

## Gotchas
- `session_files` has **no `id`** column — count `COUNT(DISTINCT file_path)`, not `COUNT(DISTINCT id)`.
- VS Code `<hash>` dirs have no human-readable mapping — read each transcript's `session.start.data.context.cwd` to identify the project.

## Manifest & log
- `source_type`: `copilot_session` | `copilot_checkpoint` | `copilot_transcript` | `copilot_memory_artifact`.
- Per-project block: `{repository, cwd, last_ingested, sessions_ingested, sessions_total, checkpoints_ingested, memory_artifacts_ingested}`.
- log.md: `- [TS] COPILOT_HISTORY_INGEST projects=N sessions=M checkpoints=C pages_updated=X pages_created=Y mode=append|full`
- hot.md example: "Ingested M Copilot sessions across N projects; patterns in API design and testing."
