# Sources monitored (coverage audit reference)

The coverage audit (SKILL.md → Step 2, "After A1 returns") compares the sources a run
*should* have scanned against the ones it actually reached, and surfaces any gap as a
`⚠️ Couverture incomplète` block at the top of the brief. This file is the canonical
list of what "complete" means. Keep it in sync as sources are added/retired.

The concrete identifiers (channel names/IDs, Confluence space keys) live in
`state/channels.yml` and the profile — this file lists the **categories** and the rule
for judging each one scanned vs unscanned. A source counts as `unscanned` when its read
errored, was access-denied, or returned null due to network — NOT when it was reached and
simply had no activity.

## Source inventory

| # | Source | Scanned by | "Reached" criterion |
|---|--------|-----------|---------------------|
| 1 | Team channels (each `team_channels` entry in `state/channels.yml`) | A1 | `slack_read_channel(channel_id)` returned without error for every non-null id |
| 2 | Canvases (each `canvases` entry) | A1 | `slack_read_canvas(canvas_id)` returned content (large canvases included — size is never a skip reason) |
| 3 | Owner DMs (IM) | A1 | `to:me` IM search returned (paginated to oldest < window) |
| 4 | Owner group DMs (MPIM) | A1 | `to:me` MPIM search returned |
| 5 | Owner sent / mentioned activity | A1 | `from:<owner>` + mention searches returned |
| 6 | Confluence spaces (each space in `confluence_spaces`) | C | CQL query returned for the space |
| 7 | Calendar (REF_DATE + next working day) | D | `outlook_calendar_search` returned for both days |
| 8 | Claude Code sessions (window) | B | `claude-history-ingest` completed for the window |

## Notes

- Channels with `id: null` in `channels.yml` fall back to name search and are flagged in
  the audit if that fallback fails — encourage filling the real id.
- A source that was reached but empty is NOT unscanned; it simply contributes nothing.
- When you add a new monitored source (a new MCP, a new space), add a row here so the
  audit can detect a future scan failure for it.
