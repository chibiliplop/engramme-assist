# Pi — data format

**Path:** `PI_HISTORY_PATH`, default `~/.pi/agent/sessions` (or `$PI_CODING_AGENT_SESSION_DIR`). Typically **absent on this machine** → report absent, 0 pages.

## Layout
```
~/.pi/agent/sessions/
└── --<cwd-with-slashes-as-dashes>--/
    └── <ISO-timestamp>_<uuid>.jsonl     # one session; parent dir encodes the cwd
```
Decode the parent dir `--<path>--` → `/path` to get the session's `cwd` (project scope).

## Delta markers
`find "$PI_HISTORY_PATH" -name "*.jsonl"`. New = not in manifest; Modified = file mtime newer than `ingested_at`. Record per file: path, decoded cwd, `session_info.name` (if any), mtime.

## Session JSONL — tree structure
First line is a `session` header; later lines are tree entries with `id` + `parentId`. **Reconstruct the active branch before extracting:** map entries by `id`, find the leaf (last `message`/no children), walk `parentId` to root, reverse to chronological.

Entry `type`s: `session` (header: cwd, version, id, timestamp, parentSession) · `message` (**primary**) · `session_info` (name via `/name`) · `compaction` (**gold** — pre-synthesized) · `branch_summary` (**good** — abandoned branches) · skip `model_change`, `thinking_level_change`, `custom`, `label`.

`message` roles: `user` (content = string or content[]) · `assistant` (extract `text` blocks; **skip `thinking`**; note `toolCall` blocks = what it did) · `toolResult` (summarize outcome, don't dump) · `bashExecution` (`command`+`exitCode`; recurring commands reveal build/test/deploy workflow).

## Value ranking
1. `message` user+assistant 2. `compaction.summary` (verbatim-distilled) 3. `branch_summary.summary` 4. `bashExecution` 5. `session_info.name` (topic hint).

## Gotchas
- It's a tree, not a flat log — a naive line-by-line read mixes abandoned branches; always walk the active `parentId` chain.
- Skip `thinking` blocks and image content; summarize tool outputs >500 chars.
- `compaction`/`branch_summary` are pre-distilled → mark `^[extracted]`; conversation synthesis → `^[inferred]`; `^[ambiguous]` when a compaction contradicts later turns.

## Manifest & log
- `source_type`: `pi_session`.
- Per-tool block `pi`: `{source_path, last_ingested, sessions_ingested, sessions_total, pages_created, pages_updated}`.
- log.md: `- [TS] PI_HISTORY_INGEST sessions=N pages_updated=X pages_created=Y mode=append|full`
- hot.md example: "Ingested N Pi sessions across K projects; patterns in CLI tooling and API design."
