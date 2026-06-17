---
name: morning-brief
description: Daily morning briefing for the wiki owner. Use for `/morning-brief`, "brief du matin", "what did I miss", "quoi de neuf depuis hier", "résume-moi la journée", the first session of the day, or `/morning-brief --night`. Aggregates Slack, Confluence, Outlook calendar and Claude Code sessions since the last run; ranks items into must-read/watch/low-signal; surfaces scan gaps; prepares non-routine meetings; tracks actions/goals; and feeds recurring topics back into the wiki.
---

# morning-brief

Aggregate what {{profile.owner.name}} missed since the last brief, prepare the working day anchored by `REF_DATE`, and feed durable wiki pages from recurring topics. The final brief is written in French using the literal headings and labels in `references/brief-template.md`.

## Core Invariants

- Run from `$OBSIDIAN_VAULT_PATH` resolved via the Config Resolution Protocol. Abort clearly otherwise.
- Keep the ingestion window as `[last_brief_ts, now]` in real time for every mode. `state/last-brief.txt` is always stamped with real `now`, never `REF_DATE`.
- Use `REF_DATE` only as the presentation anchor: journal filename, calendar sections, task overdue/due-soon checks, retro-day nudge, and meeting prep.
- Do not run automatically on Sat/Sun unless explicitly invoked. When computing a next working day, skip Sat/Sun and obvious holidays.
- Write user-facing output in French, with the exact section order from `references/brief-template.md`. Do not add a Claude footer.
- Organize Slack and Confluence by score tier, not by source. Each scored Slack/Confluence item appears exactly once; actions, meetings and goals may link back but must not re-summarize a developed item.
- Keep the brief under 1,200 words and use permalinks/web URLs, not plain-text source descriptions.
- Morning-brief orchestrates, writes the journal, and persists state. It does not write durable wiki pages directly; it stages raw notes and delegates to existing skills.

## References

Read these files only when their step needs them:

| File | Use |
|---|---|
| `references/agent-a1-slack-triage.md` | A1 prompt: Slack fetch + KEEP/DROP triage on `<triage_model>` |
| `references/agent-a2-slack-synth.md` | A2 prompt: Slack clustering/scoring on `<synth_model>` |
| `references/agent-b-claude-sessions.md` | B prompt: Claude sessions + `claude-history-ingest` |
| `references/agent-c-confluence.md` | C prompt: Confluence changed pages + scoring |
| `references/agent-d-calendar.md` | D prompt: calendar, attendee resolution, meeting prep |
| `references/agent-e-daily-update.md` | E prompt: final `daily-update` maintenance |
| `references/brief-template.md` | Journal skeleton, refresh merge rules, meeting/goals rendering rules |
| `references/person-entity-convention.md` | Person page/stub naming and frontmatter contract |
| `references/sources-monitored.md` | Coverage-audit source inventory |
| `references/architecture-notes.md` | Cost/delegation rationale for maintainers |

When spawning any subagent prompt file, read the file and pass only the fenced block after substituting concrete `<...>` placeholders. Headers above the fence are orchestration notes, not part of the prompt.

## Date Modes

The brief has two date roles:

| | Normal mode | `--night` mode |
|---|---|---|
| Ingestion window | `[last_brief_ts, now]` | `[last_brief_ts, now]` |
| `REF_DATE` | today | next working day strictly after today |
| Calendar "Today" | `REF_DATE` | `REF_DATE` |
| Calendar "Next working day" | next working day after `REF_DATE` | next working day after `REF_DATE` |
| Journal file | `journal/<REF_DATE>-brief.md` | `journal/<REF_DATE>-brief.md` |
| Retro/task checks | anchored to `REF_DATE` | anchored to `REF_DATE` |

If `--night` is absent and local time is >= 16:00, ask once via `AskUserQuestion` before computing `REF_DATE`:

- Question: `Il est <HH:MM> — tu voulais le brief de <next working day> (\`--night\`) ou celui d'aujourd'hui ?`
- Recommended option: `Oui, \`--night\` (brief de <next working day>)`
- Other option: `Non, mode normal (aujourd'hui)`

On cancel or ambiguous answer, default to normal mode. Before 16:00 with no flag, use normal mode directly. An explicit `--night` is always honored without asking.

## Process

### Step 1 - Resolve Context

1. Compute mode and `REF_DATE` from **Date Modes**.
2. Detect refresh: if `journal/<REF_DATE>-brief.md` already exists, set `REFRESH=true`; otherwise `REFRESH=false`.
3. Read `state/last-brief.txt`; missing/corrupt means a 24h fallback.
4. Set `window=[last_brief_ts, now]` and compute `oldest_unix`.
5. Read `state/channels.yml` for `team_channels`, `canvases` and `excluded_patterns`.
6. Convert the window start for Confluence CQL as `lastmodified >= YYYY-MM-DD`.
7. Read unchecked tasks from `state/open-actions.md`, ignoring Tasks query code blocks. Parse `@personne`, description, tags, `➕ YYYY-MM-DD`, optional `📅 YYYY-MM-DD`, and priority emoji. Flag tasks overdue before `REF_DATE` or due within 2 days; fall back to age-from-`➕` when no due date.

### Step 1b - Inbox Perso

Read `_raw/inbox.md`. If it has non-empty, non-comment content below the `---` separator, route each line through `jot` rules:

- explicit prefixes `objectif:`, `task:`, `note:`, `fait:`
- then heuristics to `goals.md`, `state/open-actions.md`, direct page update, or `_raw/notes/`

Reset `_raw/inbox.md` to its header through `---`. Keep routed lines for the optional `## 📥 Inbox` section. Empty inbox means skip the section silently.

### Step 2 - Profile + A1 Slack Triage

Before spawning any subagent, resolve and substitute concrete profile values:

- `owner_name`, `owner_full_name`, `owner_role`
- `owner_user_id`
- `confluence_spaces`
- `scoring_axes`, `thresholds`, `role_fallback`; if `scoring_axes` is absent, derive it from `owner_role` via `role_fallback`
- `retro_day`
- `triage_model`, `synth_model`

Never pass unresolved `{{profile.*}}` placeholders into subagent prompts.

Spawn A1 from `references/agent-a1-slack-triage.md` on `<triage_model>` with the window, `oldest_unix`, owner Slack ID, and channel/canvas config. The orchestrator must not read Slack itself; A1 fetches and triages raw Slack and returns compact KEEP JSON.

After A1 returns:

- If `raw_count == 0`, skip A2 and record no Slack activity in the window.
- Persist any `new_canvases` or `new_channels` into `state/channels.yml` for future runs, and suggest the channel additions to the user when relevant.
- Load `references/sources-monitored.md` plus `state/channels.yml` for the coverage audit. For A1-read sources that errored, were access-denied, or returned null due to network, record `unscanned`.
- Pass A1 `kept` and `unscanned` verbatim to A2.

**Initiative index** — run the helper once and keep its JSON for Step 3 and Step 5:
`OBSIDIAN_VAULT_PATH="$OBSIDIAN_VAULT_PATH" python3 "$OBSIDIAN_VAULT_PATH/_meta/scripts/initiative_index.py"`.
Pass a compact form (`slug, title, aliases, team, jira_keys, status, codebases`) to agents A2 and C
so they can tag each recurring topic with the initiative it matches.

### Step 3 - Parallel Synthesis Agents

Spawn A2, B, C and D in one parallel batch on `<synth_model>`:

| Agent | Prompt | Input |
|---|---|---|
| A2 Slack synth | `references/agent-a2-slack-synth.md` | A1 `kept` + `unscanned` |
| B Claude sessions | `references/agent-b-claude-sessions.md` | window `[<start>, <end>]` |
| C Confluence | `references/agent-c-confluence.md` | spaces + scoring grid |
| D Calendar | `references/agent-d-calendar.md` | `REF_DATE`, owner identity, Slack/Confluence context, person convention |

Merge A2 and C scoring blocks in Step 4: concatenate `must_read` and `watch` sorted by score, sum counts, and concatenate `items_low_links`. Persist any A2 `new_channels` like A1 channel discoveries. D `new_people` feeds Step 5.

### Step 3.5 - Overflow Gates

Only A2 and B can trigger overflow prompts. If either returns `remaining_count > 0`, ask once via `AskUserQuestion` with at most two questions:

- Show `<Agent>: N traités, M restants. Preview: <titles>`
- Options: `Tout traiter`, `Top N supplémentaires`, `Stop ici`

Re-spawn selected agents in parallel before Step 4.

### Step 4 - Write Journal Brief

Read `references/brief-template.md` before writing. It defines the section order, omitted-section rules, refresh merge behavior, meeting prep rules, goals injection and low-signal appendix.

Write or refresh `journal/<REF_DATE>-brief.md`:

- Fresh run: create the file from the template using `REF_DATE` in frontmatter/title.
- Refresh run: do not overwrite wholesale. Add the morning refresh banner, replace calendar sections fully, merge Slack/Confluence/Claude deltas with `(maj matin)`, rewrite actions/tasks against `REF_DATE`, keep original `created`/first window, extend `window` end to `now`, and add `refreshed: <now>`.

Render scoring and action sections from agent outputs:

- `must_read`: score >= `thresholds.must_read`
- `watch`: `thresholds.watch <= score < thresholds.must_read`
- low signal: count in `## 👀 À surveiller`, links in `## 🗂 Faible signal — liens`
- `## ⚡ Action required today`: A2 `action_needed`, D expected decisions, and newly detected actions; one terse action line each

For `## 🎯 Objectifs`, read `goals.md`. For each active objective, scan `state/open-actions.md` and the 5 most recent journal entries for this week's matching actions. Omit the section if no active objective exists.

### Step 5 - Feed Wiki Pages

Aggregate `recurring_topics` from A2, B and C.

1. Update `state/topics-counter.json`:
   ```json
   {"<topic-slug>": {"hits": N, "first_seen": "...", "last_seen": "...", "sources": [...]}}
   ```
2. Create/update a wiki page when any threshold is met:
   - cumulative `hits >= 3`
   - Confluence RFC merged
   - explicit decision logged in Slack
   - otherwise mention only in the brief, keeping the counter

**Initiative routing (per recurring topic, from A2/C tags):**
- `project` non-null + `project_confidence: high` + initiative `status: active` →
  **bypass the recurrence gate**: stage `_raw/morning-brief/<date>-<slug>.md` titled exactly
  as the target page (the index entry's hub title, or an existing `projects/<slug>/references/`
  page), invoke `wiki-ingest` with `PROJECT_CREATE=false`. Still increment the counter for
  traceability, but do not wait for `hits >= 3`.
- `new_project_candidate` present → collect it for the prompt below; do not create anything yet.
- Otherwise → unchanged counter + `hits >= 3` gate (a standalone global page).

**New-initiative prompt** (only when the collected `new_project_candidate` set is non-empty
**and** the run is interactive): ask **one** `AskUserQuestion` (multiSelect) listing up to 4
candidates (beyond 4, take the top 4 by signal strength and list the rest in the brief). Each
option shows `proposed_slug` + `proposed_title`; `Other` lets the owner rename — the slug is the
owner's choice. For each chosen candidate, create `projects/<slug>/` via `wiki-ingest` with
`PROJECT_CREATE=true`, then feed the topic into it. Non-chosen candidates fall back to the
counter/gate rule. In a **non-interactive** run, create nothing — list the candidates under
`## 🌱 Recurring topics` for the next interactive session.

3. If D returned `new_people`, route staged `_raw/morning-brief/people/*.md` stubs through `wiki-ingest` unconditionally; a first encountered named attendee gets a person page immediately.
4. Spawn two parallel one-pass subagents on `<synth_model>`:
   - **5a people** when `new_people` is non-empty: invoke `wiki-ingest` on `_raw/morning-brief/people/*.md`; verify final pages are named `entities/Prénom Nom.md` per `references/person-entity-convention.md`.
   - **5b topics**: stage `_raw/morning-brief/YYYY-MM-DD-<topic-slug>.md`, invoke `wiki-ingest`, invoke `cross-linker` once, and persist `topics-counter` deltas. Claude-session topics are already handled by B.
5. Both Step-5 agents pass `QMD=skip` to `wiki-ingest` and `cross-linker`. QMD refresh happens exactly once in Agent E.
6. Append one line per new/updated page to `## 🌱 Recurring topics`, including `🆕 fiche personne` for new people.

### Step 6 - State, Manifest, Log

`wiki-ingest` and `claude-history-ingest` own `.manifest.json` and `index.md` updates. Morning-brief owns:

1. Append to `log.md`:
   ```
   - [<now>] MORNING_BRIEF window=<start>..<end> pages_created=X pages_updated=Y slack_clusters=N claude_sessions=M confluence_pages=K
   ```
2. Write real `now` ISO to `state/last-brief.txt`.
3. Persist `state/topics-counter.json`.
4. Append A2 `new_actions` under `state/open-actions.md` `## Actions`, never inside Tasks query blocks:
   ```
   - [ ] #task @person — description #tag ➕ <today> [📅 <due>] [priority emoji] (source: permalink)
   ```
   Always include `#task` and `➕ <today>`. Add `📅` only for real deadlines; map "semaine prochaine" to that Monday. Use priority `⏫`/`🔺` for urgent/deadline-driven, `🔼` default, `🔽` nice-to-have. Map intent to `#relance`, `#decision`, `#attente` or `#urgent`. Never remove/check existing tasks; deduplicate by same person + same unchecked action.
5. Echo the brief file path to the user.

### Step 7 - Agent E Maintenance

Spawn Agent E from `references/agent-e-daily-update.md` on `<synth_model>` after Steps 5 and 6. After it returns, replace the brief's `## 🧹 Maintenance` placeholder with Agent E's one-line summary.

If Agent E reports `verify_backlog_claims >= 20` or `review_overdue_count >= 10`:

- Always append `🔎 N claims inférés sur M pages → /wiki-verify` to `## 🧹 Maintenance`.
- On retro days (`REF_DATE` weekday == `<retro_day>`), also fill the `## 🗓 Rétro` verification line with the real numbers.

Below both thresholds, omit the nudge.

## Limits

- Slack private-channel search with `in:#name` is unreliable; prefer `slack_read_channel(channel_id)` for known IDs.
- `from:<@<owner_user_id>>` search catches {{profile.owner.name}} activity in channels not listed in `channels.yml`.
- If a channel has `id: null`, skip `read_channel`, fall back to name search, and encourage filling the real ID when found.
- Outlook: use `outlook_calendar_search` first; `find_meeting_availability` only for slot detail.
- Confluence CQL has no "interesting" filter; use spaces + recency.
- People directory source of truth is `entities/`. Match attendees by email first, then aliases/slack_id/title. Never write `entities/` directly; stage `_raw/morning-brief/people/` and let `wiki-ingest` create/update pages. External guests with no signal are listed, not filed.
- Corrupted state file means 24h fallback, never crash.
- Slack permalinks are verbatim; Confluence links use web URL form, not API IDs.
