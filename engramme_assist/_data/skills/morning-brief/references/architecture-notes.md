# Architecture Notes

Maintenance reference for why the pipeline is split this way. Normal morning-brief
runs do not need to read this file.

## Cost Notes

- A1 runs on `<triage_model>` and does both Slack fetch and KEEP/DROP triage. Raw Slack
  volume stays in A1's context; only compact KEEP JSON reaches the orchestrator.
- A2 runs on `<synth_model>` and sees only the KEEP subset for clustering/scoring.
- B/C/D also run as `<synth_model>` subagents. The orchestrator passes config and relays
  compact JSON; it does not hold raw Slack.
- B delegates local session ingestion to `claude-history-ingest`.
- C is constrained by Confluence CQL space filters.
- D reads attachments only when present; `wiki-query` runs index-only.
- If A1 returns `raw_count == 0`, skip A2.
- Step 5 uses two parallel one-pass subagents (people and topics) to avoid a large partial
  agent and expensive resume.
- QMD reindexes once per run in Agent E. Step-5 agents pass `QMD=skip` to `wiki-ingest`
  and `cross-linker`.

## Delegation Map

| Concern | Delegated to |
|---|---|
| Claude session -> wiki pages | `claude-history-ingest` (Agent B) |
| Slack/Confluence topic -> wiki pages | `wiki-ingest` (Step 5, via `_raw/morning-brief/`) |
| Meeting attendee -> person page | `entities/` lookup (Agent D); new people staged -> `wiki-ingest` |
| Meeting title -> relevant wiki context | `wiki-query` index-only (Agent D) |
| Cross-linking new pages | `cross-linker` after Step 5 staging |
| Tag consistency | `tag-taxonomy` inside `wiki-ingest` |
| Wiki maintenance | `daily-update` (Agent E final pass) |
| Ambient topic -> initiative page | `morning-brief` Step 5 (high-confidence active match, gate bypass) via `wiki-ingest` `PROJECT_CREATE=false`; index from `initiative_index.py` |
| New-initiative creation | human-confirmed in the brief (batched `AskUserQuestion`); never silent from ambient sources |
