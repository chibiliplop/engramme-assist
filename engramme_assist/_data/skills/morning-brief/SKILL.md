---
name: morning-brief
description: Daily morning briefing for the wiki owner. Two-stage Slack pipeline (triage model → synth model) plus parallel Claude Code sessions, Confluence and calendar agents. Output is BOTH a journal brief AND wiki page updates (topical pages when signal is strong), feeding the wiki the way wiki-ingest / claude-history-ingest already do. Includes pre-meeting briefs (non-routine meetings — participants, open threads, past decisions, points à préparer), must-read scoring 1–10 per item (archi / métier / urgence / signal) with coverage audit (unscanned sources surfaced at top of brief), and active-goals injection from goals.md.
---

# morning-brief

Aggregate everything {{profile.owner.name}} may have missed since the last brief + flag what they must prepare for today/tomorrow + feed the wiki on recurring topics. Run each working morning.

## When to use

- Manual invocation `/morning-brief` (or natural request "brief du matin", "what did I miss").
- First Claude Code session of the day.
- **`/morning-brief --night`** — run it the **evening before** the working day you'll read it. Convenient when the morning is tight: launch it tonight, read it tomorrow. See **Modes** below.

## Inputs

- **Working directory** — must be `$OBSIDIAN_VAULT_PATH` (résolu via le Config Resolution Protocol). Abort with a clear message otherwise.
- **Last brief timestamp** — `state/last-brief.txt` (ISO). Missing → 24h fallback.
- **Team channels config** — `state/channels.yml`. Lists team channels {{profile.owner.name}} wants to follow even without a mention. Can evolve.
- **`--night` flag** — optional. Shifts the date anchor to the next working day (see **Modes**). Absent → normal morning mode.

## Modes — `REF_DATE` (the date anchor)

The brief has two date roles, and `--night` only touches the second:

- **Ingestion window** = `[last_brief_ts, now]` — a pure *diff* against the stored timestamp. **Identical in both modes** (and `state/last-brief.txt` is always stamped at the real `now`). Whether you run at 20:00 or 08:00, the diff catches everything since the last brief, so an evening run loses nothing as long as nothing material happens overnight.
- **Presentation anchor** = `REF_DATE`, the working day the brief is *for* (the morning you'll read it). Everything "today"-anchored uses `REF_DATE`, NOT the calendar date of the run:

| | Normal mode | `--night` mode |
|---|---|---|
| `REF_DATE` | today | **next working day strictly after today** (Fri night → Monday; skip Sat/Sun + obvious holidays) |
| Calendar "Today" section | `REF_DATE` | `REF_DATE` |
| Calendar "Next working day" section | next working day after `REF_DATE` | next working day after `REF_DATE` |
| Journal filename `journal/<date>-brief.md` | `REF_DATE` | `REF_DATE` |
| Retro-day nudge | `REF_DATE` weekday == configured `retro_day` | `REF_DATE` weekday == configured `retro_day` |
| Task ⚠️ overdue/due-soon | `REF_DATE` as "today" | `REF_DATE` as "today" |

So a Tuesday-evening `--night` run produces the **Wednesday** brief (Today=Wednesday, Next=Thursday, file `journal/<Wednesday>-brief.md`); an evening run before the configured retro day produces that retro-day brief and shows the retro nudge.

**Evening auto-prompt** — if `--night` is absent AND the local run time is **≥ 16:00**, {{profile.owner.name}} likely forgot the flag (they run the brief in the evening for the next morning). Before computing `REF_DATE`, ask ONCE via `AskUserQuestion`:
- Question: "Il est <HH:MM> — tu voulais le brief de <next working day> (`--night`) ou celui d'aujourd'hui ?"
- Options: **"Oui, `--night` (brief de <next working day>)"** (recommended) → night mode · **"Non, mode normal (aujourd'hui)"** → normal mode.
On any other answer / cancel → default to **normal mode** (never block the brief on this). Before 16:00 with no flag → straight to normal mode, no prompt. An explicit `--night` is always honoured without asking.

## Pipeline overview

```
window → [A1 triage fetch+triage Slack] → [A2 synth Slack]
       ↘ [B   synth Claude sessions ]            ↘
       ↘ [C   synth Confluence       ]  →  Step 4: brief journal
       ↘ [D   synth Calendar         ]  →  Step 5: wiki pages (wiki-ingest)
                                         →  Step 6: manifest + log + state
                                         →  Step 7: [E synth daily-update]
```

Agent E (`daily-update`) runs **last**, as the final maintenance pass — AFTER all ingestion (Step 5). Running it at the end is the whole point: index reconcile, `hot.md` regen and QMD refresh then reflect today's freshly-written pages. It's independent of the brief's session context, so it goes in a subagent.

Two-stage Slack pipeline is the cost-control mechanism — the triage model both **fetches and triages** (so the raw Slack volume stays in its cheaper context, never the orchestrator's), and only the kept items cross to the synth model.

## Process

### Step 1 — Resolve window + load config

0. **Detect mode.** Explicit `--night` → night mode (no prompt). No flag → check the local clock: **≥ 16:00** → run the **Evening auto-prompt** (see Modes) and use the answer (default normal mode if cancelled/ambiguous); **< 16:00** → normal mode directly. Then compute `REF_DATE` per the **Modes** table: normal → today; night → the next working day strictly after today (Fri→Mon, skip Sat/Sun + obvious holidays). All "today"-anchored steps below use `REF_DATE`. The ingestion window is unaffected by mode.
0b. **Detect refresh.** After computing `REF_DATE`, check whether `journal/<REF_DATE>-brief.md` already exists (i.e. a `--night` run yesterday already produced this morning's brief). If it does → this is a **refresh run**, not a fresh brief. Set `REFRESH=true` and remember the existing file. See Step 4 for how the write merges instead of overwrites. The ingestion window stays the natural delta `[last_brief_ts, now]` — no widening, no re-ingest of yesterday's content. If no such file → `REFRESH=false`, normal write.
1. Read `state/last-brief.txt`. Parse ISO. Missing/corrupt → 24h.
2. Window = `[last_brief_ts, now]` (always real `now`, both modes). Convert `start` to Unix timestamp (`oldest_unix`).
3. Read `state/channels.yml` → `team_channels` list (with `id` fields) + `excluded_patterns`.
4. Convert window to Confluence `lastmodified >= YYYY-MM-DD`.
5. Read `state/open-actions.md` → extract all unchecked task lines (`- [ ] #task …`, ignore the `tasks` query code-blocks). These use Obsidian **Tasks** plugin syntax. Per line parse: `@personne`, description, `#tag`, created date `➕ YYYY-MM-DD`, optional due date `📅 YYYY-MM-DD`, optional priority (`🔺`/`⏫`/`🔼`/`🔽`/`⏬`). Flag as ⚠️ any task that is **overdue** (`📅` < `REF_DATE`) or **due within 2 days of `REF_DATE`**; fall back to age-from-`➕` when no due date. Load into context for Step 4.

### Step 1b — Inbox perso (`_raw/inbox.md`)

Read `_raw/inbox.md`. If it contains content lines below the `---` separator (non-empty, non-comment), route EACH line through the `jot` skill's routing rules (explicit prefixes `objectif:`/`task:`/`note:`/`fait:`, then heuristics → goals.md / `state/open-actions.md` / page UPDATE / `_raw/notes/`). Then reset the file to its header (everything up to and including `---`). Routed objectives and tasks flow naturally into this brief's « Objectifs » and « Actions en cours » sections. Record the routed lines for the `## 📥 Inbox` brief section. Empty inbox → skip silently, omit the section.

### Step 2 — Phase A1: triage model fetches Slack AND triages (one subagent)

Phase A1 is a single triage-model subagent that does BOTH the raw fetch and the KEEP/DROP triage. This is the cost-control core: the raw Slack volume (every channel read, every canvas, every search result) lands in the triage model's context, never the orchestrator's. Only the compact KEEP JSON crosses back. The orchestrator does NOT read Slack itself — it hands the triage subagent the config + window and waits for the JSON.

Why this matters: if the orchestrator fetched and then pasted the raw list into the triage prompt, the full Slack volume would hit the session model twice — once as tool results, once re-emitted as prompt text. Doing the reads inside the triage subagent keeps all of it on the cheaper tier.

The triage model does only reading + binary classification — no synthesis, no clustering, no thread-following. All judgment is deferred to A2.

### Résolution du profil (orchestrateur, AVANT tout spawn)

Les sous-agents (A1, A2, C, D) **n'héritent pas du contexte de session** : ils ne voient pas le profil. Avant de les lancer, résous depuis le profil mergé et **passe les valeurs concrètes** dans chaque prompt (substitue les `{{profile.*}}` ci-dessous par leur valeur réelle au moment du spawn) :
- `owner_name` = `{{profile.owner.name}}` · `owner_full_name` = `{{profile.owner.full_name}}`
- `owner_user_id` = `{{profile.sources.slack.user_id}}`
- `confluence_spaces` = `{{profile.sources.confluence.spaces}}`
- `scoring_axes` = `{{profile.brief.scoring_axes}}` · `thresholds` = `{{profile.brief.thresholds}}` · `role_fallback` = `{{profile.brief.role_fallback}}` · `owner_role` = `{{profile.owner.role}}`
- `retro_day` = `{{profile.tools.retro_day}}`
- modèles : `triage_model` = `{{profile.tools.model_tiers.triage}}`, `synth_model` = `{{profile.tools.model_tiers.synth}}`
Si `brief.scoring_axes` est absent, dérive la grille depuis `owner_role` via `role_fallback` et passe la grille dérivée.
Les prompts de sous-agent ci-dessous doivent recevoir uniquement les valeurs concrètes (`<triage_model>`, `<synth_model>`, `<owner_user_id>`, etc.) ; aucun `{{profile.*}}` ne doit être copié dans un prompt au moment du spawn.

Spawn:

```
Subagent type: general-purpose
Model: <triage_model>

Task — fetch raw Slack for window [<start>, <end>] (oldest_unix=<oldest_unix>) and triage it.
Reading + KEEP/DROP classification ONLY. No synthesis, no clustering, no thread-following.

Config (passed by the orchestrator from state/channels.yml — do NOT read the file yourself):
- team_channels: <list of {name, id} with non-null id>
- canvases: <list of {channel, canvas_id}>
- owner_user_id: <owner_user_id passé par l'orchestrateur>
- excluded_patterns: <from channels.yml>

FETCH (issue the reads in parallel batches of up to 8 tool calls per message):

1. Team channels — for EACH channel with a non-null id:
   slack_read_channel(channel_id=<id>, oldest=<oldest_unix>, limit=50).
   Do NOT use slack_search_public_and_private with in:#name for private channels —
   its index is incomplete. Always read by channel_id.

2. Canvases (standing docs — agendas, runbooks — NOT in the message feed, high-value):
   for each canvas, slack_read_canvas(canvas_id=<id>). A large canvas (the tech-archis
   agenda is ~111k chars) must STILL be processed — never skip it because it's big. Scan
   for the most-recent dated section/heading (e.g. the next meeting's agenda) + open TODOs
   + anything changed since <start>; report those. Do NOT abandon a canvas on size.
   Tag kept canvas items bucket_hint=canvas.
   If any slack_read_channel output mentions "made updates to a canvas tab: FXXXXXXX",
   report that ID under new_canvases so the orchestrator can persist it.

3. `<owner_name>`'s DMs / mentions / own activity:
   ⚠️ CRITICAL — the date window goes in the dedicated `after`/`before` PARAMETERS as a
   **Unix timestamp** (after=<oldest_unix>), NOT as `after:YYYY-MM-DD` inside the query text.
   Putting the date in the query string silently returns wrong/zero results — this is the
   #1 cause of missed DMs. Also use `sort="timestamp"`. The `to:me` modifier is the most
   reliable for incoming DMs. Run the IM and MPIM (group-DM) sweeps SEPARATELY — bundling
   `im,mpim` under-returns. Paginate (follow `cursor`) until the oldest result predates
   <oldest_unix>, so no conversation partner is cut off. Required queries:
   - slack_search_public_and_private(query="to:me", channel_types="im", after=<oldest_unix>, sort="timestamp", include_context=false)
   - slack_search_public_and_private(query="to:me", channel_types="mpim", after=<oldest_unix>, sort="timestamp", include_context=false)
   - slack_search_public_and_private(query="from:<@<owner_user_id>>", channel_types="im", after=<oldest_unix>, sort="timestamp")  (`<owner_name>`'s own sent DMs — reveals threads he is driving)
   - slack_search_public_and_private(query="from:<@<owner_user_id>>", after=<oldest_unix>, sort="timestamp")  (catches active public/private channels not in the config)
   - slack_search_public_and_private(query="\"<owner_user_id>\"", after=<oldest_unix>, sort="timestamp")  (mentions of `<owner_name>` ANYWHERE, incl. inside threads — a mention is often a direct "valide ça" ask that channel-head reads miss)
   Group every distinct DM/group-DM channel (D… or C… mpim) found into ONE kept item per
   conversation (dedupe the many per-message hits) so A2 sees the conversation, not 20 lines.
   Note: team-channel reads (step 1) only surface TOP-LEVEL messages — thread replies are
   NOT included. The from:/mention searches above are what catch the owner's in-thread activity
   and asks; keep every channel thread where the owner is mentioned or replies (bucket_hint=mention),
   so A2 can follow it. Channel date-windowing itself is correct (slack_read_channel oldest=
   <oldest_unix>) — the date bug only ever affected the search queries, not the channel reads.

TRIAGE — for each message OR thread head, decide quickly (no deep reasoning):
- KEEP — has substance (decision, blocker, design note, incident, RFC, demo,
  question awaiting an answer, FYI worth a tech lead's attention)
- **DM / group-DM (bucket_hint=dm/mpim) → ALWAYS KEEP, never DROP.** DMs and group DMs
  are high-priority by default — a DM `<owner_name>` initiated almost always flags a topic
  they are actively driving. Keep even short-looking ones; A2 follows the thread.
- DROP — logistics ("j'arrive", "ok", "merci", emoji-only, sticker, "tu peux venir",
  TT announcements, bot join/leave, daily standup bot messages) — **but only in
  team/public channels, never in DMs**.
- BOT/ALERT — bot-only or alert noise → DROP
NO cap. When in doubt, KEEP — A2 re-checks ambiguous items on the synth model, so a false keep is
cheap but a false drop is lost forever.

Return STRICTLY this JSON, no prose:
{
  "raw_count": <total messages fetched, before triage>,
  "new_canvases": [{"channel": "...", "canvas_id": "F..."}],
  "new_channels": [{"name": "...", "id": "..."}],   // active channels seen via from:/mention search but absent from config
  "kept": [
    {"permalink": "...", "channel": "...", "author": "...", "ts": "...", "thread_ts": "...|null", "bucket_hint": "dm|mention|owner-active|team-channel|canvas", "one_liner": "<≤120 chars raw context, no synthesis>"}
  ]
}
```

After A1 returns:
- If `raw_count == 0` → skip A2 entirely, note "no Slack activity in window".
- If `new_canvases` / `new_channels` are non-empty → add them to `state/channels.yml` for future runs (suggest to the user when adding channels).
- **Coverage audit** — before passing to A2, check which sources were successfully scanned. Load the full source list from `references/sources-monitored.md` (if it exists) and `state/channels.yml`. For each source that A1 could NOT read (tool error, access denied, null result due to network), record it as `unscanned`. Pass `unscanned` alongside `kept` to A2. If `unscanned` is non-empty, the brief MUST open with a `⚠️ Couverture incomplète` block listing each unscanned source — never silently omit a scan failure.
- Pass `kept` and `unscanned` verbatim to A2 as its input.

### Step 3 — Spawn remaining agents in parallel

Single message with 4 `Agent` tool calls (A2, B, C, D). Each spawns as a subagent, so each carries its own concrete `Model:` — A2/B/C/D run on `<synth_model>` (synthesis + wiki writing don't need the deep tier; the session model would otherwise leak in). Only override these because they are subagents. The orchestrator itself does no heavy reading — A1 (`<triage_model>`) fetches + triages Slack, so the only thing on the session model is light relaying of compact JSON between subagents.

#### Agent A2 — Slack synth

```
Subagent type: general-purpose
Model: <synth_model>

Input: JSON list from Phase A1 (paste verbatim).

Task — cluster kept Slack items into topic items and write the brief section.

For each cluster:
- Read the thread via slack_read_thread when one_liner is ambiguous OR when
  bucket_hint=mention/dm and action is unclear.
- **DMs / group DMs are high priority — always read their thread.** If a reply
  redirects elsewhere ("je te réponds sur notre support", "voir dans #canal"), follow
  it: find that channel (slack_search_channels) and read it for the actual answer. Add
  any newly-discovered support channel to `state/channels.yml` via `new_channels`.
- Cluster across messages by TOPIC (3 messages on same decision = 1 item).
- Per cluster output:
  - 1-sentence summary (who + what)
  - Action expected from `<owner_name>` (yes/no — if yes, what)
  - Most representative permalink
  - Channel
  - is_action_needed: true/false (true = `<owner_name>` must act → feeds the "Action required today" list; the rendering of every cluster in the brief is by SCORE, not by bucket, so there is no informational/side-noise section to fill)

Also identify RECURRING TOPICS — same theme appearing across ≥3 messages or
across multiple channels. Flag these for the wiki-write phase (Step 5).

Also detect NEW ACTIONS for `<owner_name>` — patterns like: "est-ce que tu peux", "tu peux me", "j'attends ta réponse", "relance-moi", "on attend `<owner_name>`", "waiting on you", direct questions in DMs/mentions left unanswered. Flag with the person's name and a 1-line description.

**Scoring** — l'orchestrateur te passe la grille (`scoring_axes` + `thresholds`). Assigne à chaque
cluster gardé un score : pour chaque axe de `scoring_axes`, ajoute son `weight` si le cluster
correspond à sa `description` (lis la clause, ce n'est pas une somme mécanique). Aucun axe ne
correspond → score 1 (pas 0).

scoring_axes (passés par l'orchestrateur) : <scoring_axes>
thresholds (passés par l'orchestrateur) : <thresholds>

Tier output :
- score ≥ thresholds.must_read → **must_read** : liste `must_read` avec résumé 2 phrases + permalink.
- thresholds.watch ≤ score < thresholds.must_read → **watch** : bullet compact dans « à surveiller ».
- score < thresholds.watch → **counted only** : ne pas développer ; enregistrer `{permalink, one_liner, channel}`
  dans `items_low_links` (et incrémenter `items_low`) pour l'appendice liens-seuls.

(Agent C applies the same scoring grid to Confluence items on its side — A2 and C run in parallel and never see each other's output; the orchestrator merges both `scoring` blocks in Step 4.)

Output structure:
{
  "action_needed": [
    {"summary": "...", "action": "what `<owner_name>` must do", "permalink": "...", "channel": "..."}
  ],
  "scoring": {
    "must_read": [
      {"score": 9, "summary": "2-sentence summary", "permalink": "...", "channel": "..."}
    ],
    "watch": [
      {"score": 6, "one_liner": "≤80 chars", "permalink": "..."}
    ],
    "items_low": <count of score ≤4 items>,
    "items_low_links": [
      {"permalink": "...", "one_liner": "≤80 chars raw context", "channel": "..."}
    ],
    "items_scored": <total items scored>,
    "sources_scanned": "<N scanned>/<M total>",
    "unscanned": ["<source name>", ...]
  },
  "recurring_topics": [
    {"topic": "...", "channels": [...], "permalinks": [...], "summary": "..."}
  ],
  "new_actions": [
    {"person": "@name", "action": "description ≤80 chars", "permalink": "..."}
  ]
}

Overflow rule — if clusters > 30, return top 30 by priority
(action-needed > mention > team-channel) + count remaining + 5-title preview.
Under 900 words on the prose side.
```

#### Agent B — Claude Code sessions veille

Delegate to existing skill `claude-history-ingest` instead of re-implementing JSONL parsing.

```
Subagent type: general-purpose
Model: <synth_model>

Two-part task:

Part 1 — Invoke skill `claude-history-ingest` in APPEND mode with window
constraint [<start>, <end>]. The skill already knows ~/.claude layout, JSONL
parsing, privacy rules, manifest update. Pass:
- mode: append
- window: [<start>, <end>] (only process sessions with mtime in window)
- skip memory files (auto-ingest)

Capture from its output:
- list of pages created/updated in vault
- list of projects touched

Part 2 — Brief-only summary (in addition to wiki writes already done by the skill):
For each project touched in window, output:
- Project (decoded path)
- 1-sentence purpose
- Files written/edited (deduplicated)
- End state — committed | uncommitted | branch pushed | PR opened | blocked
- Open TODOs / blockers from last assistant messages

Identify RECURRING TOPICS — same area touched ≥3 sessions cumulatively
(check state/topics-counter.json for prior hits — see Step 6).

Output JSON:
{
  "brief_sections": {...by project},
  "recurring_topics": [...],
  "skill_result": {"pages_created": [...], "pages_updated": [...]}
}

Soft cap 25 topics. If more, top 25 by priority + count remaining + 5-title preview.
```

#### Agent C — Confluence updates

```
Subagent type: general-purpose
Model: <synth_model>

CQL: lastmodified >= "<start>" AND space in (<confluence_spaces joints par ", ">)
Spaces priority : dans l'ordre de `confluence_spaces` (passé par l'orchestrateur).

Per page:
- Title, space, author
- 1-sentence why-it-matters (read page if title ambiguous)
- Web URL form: your Confluence cloud base URL + `/wiki/spaces/...`

Follow once any link to a pertinent RFC/ADR/spec in another space.

Identify RECURRING TOPICS — multiple pages on same theme or follow-up to existing
wiki content. Flag for wiki-write phase.

Scoring — apply the SAME scoring as Agent A2, depuis les `scoring_axes` + `thresholds` que l'orchestrateur te passe (mêmes que ceux d'A2).

scoring_axes (passés par l'orchestrateur) : <scoring_axes>
thresholds (passés par l'orchestrateur) : <thresholds>

Include the same `scoring` block in the output JSON
(must_read with 2-sentence summary per the must_read threshold, watch per the watch threshold, items_low count + the
`items_low_links` list — for each low-signal page record `{permalink: <web URL>, one_liner, channel: <space>}`). The
orchestrator merges A2's and C's scoring blocks in Step 4 (concatenate must_read
and watch sorted by score, sum the counts, concatenate the `items_low_links`).

Soft cap 25 pages — Confluence volume per day is low; overflow gate not needed.
If somehow >25, take top 25 by recency × space priority and mention the rest in
one line.

Output JSON same shape as Agent A2.
```

#### Agent D — Calendar today + next working day (with attendee resolution + attachment + wiki cross-ref)

```
Subagent type: general-purpose
Model: <synth_model>

The orchestrator passes `REF_DATE` (the date anchor — see Modes). Normal mode: `REF_DATE` = today. Night mode (`--night`): `REF_DATE` = the next working day after the real today (the morning the owner will read this). Build BOTH calendar sections off `REF_DATE`, never off the run's calendar date.

`<owner_name>` does NOT work weekends (Sat/Sun). The two sections are:
- **"Today"** = `REF_DATE` (full day).
- **"Next working day"** = the next working day strictly AFTER `REF_DATE`:
  - `REF_DATE` is Mon–Thu → next working day = `REF_DATE` + 1 day.
  - `REF_DATE` is Friday → next working day = the following MONDAY (skip Sat + Sun).
  - (If a public holiday is obvious, skip it too and take the following working day.)

outlook_calendar_search for `<owner_full_name>` (orchestrator passes REF_DATE=<ref_date>):
- `REF_DATE` (full day) — the "Today" section
- Next working day after `REF_DATE` (full day) — computed per the rule above, NOT literally tomorrow

For EACH meeting, build "what to prepare":

1. Resolve participants — WHO they are + WHAT they own (the people directory)
   The brief must not just list names; it must say who each key attendee is and
   what perimeter (scope/domain of responsibility) they hold. Source of truth =
   the wiki `entities/` person pages (see "Person-entity convention" below).

   For each attendee that is NOT the owner (`<owner_name>`; skip the owner himself; skip large
   distribution lists / rooms — only resolve named humans):
   a. Match against entities/ person pages. Grep the frontmatter of
      `entities/*.md` (pages tagged `person`) for the attendee, matching on
      `title`, any `aliases:` entry, the `email:`, or the `slack_id:`. Email is
      the most reliable key (Outlook gives it) — match the email local part too.
   b. FOUND → surface from the page: `role`, `team`, `perimeter`, and the
      [[wikilink]] to the page. One line: "Prénom Nom — <role>, <team> — périmètre : <perimeter>".
      **Always link by the page `title` (`[[Prénom Nom]]`), which is the actual
      filename — never by a kebab slug like `[[prenom-nom]]`, which resolves to
      nothing.** If unsure of the exact title, read it from the matched page's
      frontmatter rather than guessing.
   c. NOT FOUND → the attendee is new to the directory. Enrich + create a stub so
      the next brief knows them:
      - Pull identity signal: slack_search_users / slack_read_user_profile (match
        on name or email) for title + Slack ID; Atlassian lookupJiraAccountId /
        atlassianUserInfo if they appear there for job title + department.
      - Infer perimeter from the meeting title + recent Slack/Confluence context
        (Agents A2/C output) — e.g. someone organising "Platform Review" likely owns
        the platform. Mark inferred perimeter as "(à confirmer)".
      - Stage a minimal person stub at `_raw/morning-brief/people/<slug>.md`
        following the Person-entity convention (below) and let skill `wiki-ingest`
        distil it into `entities/Prénom Nom.md` in Step 5 (the final file is named
        after the `title`, NOT the slug). Do NOT write entities/ directly.
      - In the brief, link this 🆕 person by their display name `[[Prénom Nom]]`
        (which will match the page `wiki-ingest` creates in Step 5) — never
        `[[prenom-nom]]`. The stub's `aliases:` must also carry the `prenom-nom`
        kebab form as a safety net so any slug-style link still resolves.
      - In the brief, render the line with a "🆕 fiche créée" marker.
   d. If identity genuinely can't be resolved (external guest, no signal), list
      the raw name with "(inconnu — externe ?)" and do NOT create a stub.

   Keep this proportionate: small meetings → resolve all named attendees; big
   meetings (>8) → resolve the organiser + the 3–4 most relevant attendees only,
   and say "+ N autres".

2. Read meeting attachments
   - If meeting has attachments (agenda, doc, slide deck) → read them via the
     appropriate MCP (Microsoft 365 read_resource for OneDrive/SharePoint links;
     Confluence fetch for HW Confluence links; direct URL otherwise).
   - Extract key topics, decisions expected, open questions.

3. Wiki cross-reference (delegate to skill `wiki-query`)
   - Take meeting title + key topic words.
   - Invoke skill `claude-obsidian:wiki-query` in fast/index-only mode with query =
     "<title> <topic words>".
   - If wiki-query returns relevant pages, surface them as background reading.
   - This is how the brief stays connected to the owner's accumulated knowledge —
     a meeting on "Platform Refactoring" should surface [[Platform Refactoring]],
     [[Search Service Redesign]], [[Indexing Benchmark]] etc.
   - Also surface the resolved participants' [[person pages]] here as context.

4. Recent Slack signal
   - If Agent A2 output contains threads relevant to the meeting title, include
     up to 2 most recent permalinks per meeting.

Per meeting output:
- Time (start–end), title, organiser, key attendees
- Participants — one line per resolved key attendee: "Prénom Nom — <role>, <team> — périmètre : <perimeter> [[Prénom Nom]]" (🆕 if just created, "(à confirmer)" if inferred). The wikilink is the page **title** (= filename), never a `[[prenom-nom]]` slug.
- Attachments read (titles + 1-line each)
- Wiki context: bullet list of relevant wiki pages (with [[wikilinks]])
- Recent Slack context: up to 2 permalinks
- "What to prepare" — synthesized 1–3 bullets (factoring in who's in the room and what they own — e.g. "X owns indexation, prépare la question latence pour lui")
- Flag: owner organiser? decisions expected?

Output JSON additionally returns `new_people` so Step 5 can confirm directory growth:
{ "new_people": [ {"slug": "...", "name": "...", "inferred_perimeter": "..."} ] }

Skip purely recurring 1:1 (same title weekly, no attachment change) — BUT still
resolve the 1:1 counterpart once if they're not yet in entities/. Under 700 words.
```

##### Person-entity convention (the people directory)

Person pages live in `entities/` (one file per human) and are tagged `person`. The
final file is named after the page **`title`** — `entities/Prénom Nom.md` — so links
must use `[[Prénom Nom]]`. The `prenom-nom` kebab form is only the staging stub name
under `_raw/morning-brief/people/` and an alias; it is never the entities/ filename.
These pages double as the directory the calendar agent resolves attendees against.
Required-where-known frontmatter:

```markdown
---
title: Prénom Nom
category: entities                       # REQUIRED — always `entities` for person pages
aliases: [Prénom N., pnom, prenom.nom, prenom-nom]   # display variants + email local part + kebab slug (link safety net) — match keys
email: prenom.nom@company.com
slack_id: U0XXXXXXX
role: Tech Lead                          # job title
team: Search                             # squad / team / tribe
perimeter: search, indexing, platform   # what they OWN, short phrase
tags: [person, visibility/internal]
summary: <one line — who they are in your organisation>
sources:                                 # REQUIRED — where the identity was learned
  - <meeting / Slack profile / Atlassian>
provenance: <where this was learned — meeting attendee, Slack profile, Atlassian>
created: YYYY-MM-DD                       # REQUIRED
updated: YYYY-MM-DD                       # REQUIRED
---

# Prénom Nom

<1–3 sentences: role, team, perimeter, notable projects. Link [[teams]] / [[projects]] they touch.>
```

`perimeter` is the field that answers "à quel périmètre" — keep it a short, scannable
phrase, not a paragraph. When a meeting or Slack thread reveals a person's perimeter
shifted (new team, new ownership), update their page (delegate to `wiki-ingest`) rather
than creating a duplicate.

### Step 3.5 — Overflow gates (A2 + B only)

Only Agent A2 (Slack synth) and Agent B (Claude sessions) trigger gates — they are the volume-prone ones. Confluence and Calendar use soft caps without user prompt.

If `remaining_count > 0` from A2 or B, batch into a single `AskUserQuestion` (max 2 questions).

Per agent with overflow:
- Show: `<Agent>: N traités, M restants. Preview: <titles>`
- Options:
  - "Tout traiter" → re-spawn wave 2, no cap
  - "Top N supplémentaires" (suggest sensible N)
  - "Stop ici" → keep wave 1 only

Re-spawn chosen agents in parallel before Step 4.

### Step 4 — Write brief journal

Write `journal/<REF_DATE>-brief.md` — the filename is `REF_DATE`, NOT the run's calendar date (so a `--night` run dated tonight still produces tomorrow-morning's brief file). All `YYYY-MM-DD` in the frontmatter/title below are `REF_DATE`. Leave the `## 🧹 Maintenance` line as a placeholder — Step 7 fills it in once Agent E has run.

**Refresh run (`REFRESH=true` from Step 0b)** — the brief already exists from last night's `--night` run. Do NOT overwrite it wholesale (the morning window is only the overnight delta, so a fresh write would blank the rich evening sections). Instead:
- Add a banner just under the title: `> 🔄 Rafraîchi le matin à <HH:MM> — agenda re-vérifié + delta depuis le brief de la veille.`
- **Calendar sections (`## 📅 Today` / `## 📅 Next working day`)** — replace fully with Agent D's fresh output. These are date-anchored and idempotent; overnight changes (new invites, cancellations, moved rooms) are exactly what the morning refresh is for.
- **Slack / Confluence / Claude-sessions sections** — MERGE the overnight delta into the existing sections rather than replacing: prepend new items, tag them `(maj matin)`, keep yesterday's items. If the delta is empty, leave the section as-is.
- **Actions / tasks sections** — recompute against `REF_DATE` (a task may have crossed into overdue overnight) and rewrite those two sections.
- Keep the existing frontmatter `created`/first `window`; extend `window` end to the new `now` and add `refreshed: <now>`.
Then continue to Steps 5–7 normally on the delta only (no double ingestion).

**Pre-meeting briefs** — for each meeting on `REF_DATE` that is NOT a routine recurring meeting (daily standup, weekly sync with unchanged agenda), generate a concise encart of fewer than 15 lines in `## 🎯 Préparation réunions`. Routine recurring meetings are skipped UNLESS at least one open action in `state/open-actions.md` is tagged or described with a keyword matching the meeting title — in that case include them with the relevant thread flagged.

For each qualifying meeting:
- **Participants** — list resolved attendees as `[[Prénom Nom]]` wikilinks (exact page title, never a kebab slug). Agent D already resolved these; reuse the result. Mark 🆕 if the page was just created this run.
- **Open threads** — cross-reference `state/open-actions.md` (unchecked `#task` lines) and the last 3 journal entries: surface any action or topic mentioning a participant or keyword from the meeting title. At most 3 lines.
- **Past decisions** — run `qmd query "<meeting title> <key topic words>"` on the wiki collection; also scan `decisions/` folder if it exists. Surface up to 3 relevant past decisions or wiki pages with `[[wikilinks]]`.
- **Points à préparer** — 2–3 actionable bullets (e.g. "Prépare la question latence pour [[Prénom Nom]] qui owns indexation").

Format rules: short and scannable. Open threads and past decisions first. Never a narrative summary. Skip the encart entirely if the meeting has no signal (no thread, no past decision, no known participant). The `REF_DATE` rule applies: on `--night` mode `REF_DATE` is the next working day — Friday-night runs target Monday's meetings, never the weekend.

**Retro-day nudge** — if the weekday of `REF_DATE` matches `<retro_day>`, add the `## 🗓 Rétro` section shown below near the top of the brief, reminding {{profile.owner.name}} to run `/weekly-retro`. Omit the section on other days. (In `--night` mode this means an evening run before `<retro_day>` correctly shows the nudge, since `REF_DATE` is the retro day.) The retro is interactive, so this is a reminder only — `morning-brief` never runs it.

```markdown
---
title: Morning Brief — YYYY-MM-DD
aliases: ["Morning Brief — YYYY-MM-DD"]
date: YYYY-MM-DD
type: journal
tags: [journal, brief, daily]
window: [<start>, <end>]
sources: [slack, claude-sessions, confluence, outlook]
sources_scanned: N/M
items_scored: N
must_read: N
---

# Morning Brief — YYYY-MM-DD

⚠️ Couverture incomplète : <source> non balayée
(Include this warning block at the very top if any source was unscanned — one line per unscanned source. Omit entirely if all sources were reached.)

> **Digest-first / single-mention rule.** This brief is organised by PRIORITY, not by source. Every Slack/Confluence item appears EXACTLY ONCE — in its score tier (Must read / À surveiller / Faible signal), with its source shown inline. There is no per-source dump section (no "Slack — what you missed", no "Confluence — fresh pages"): re-listing scored items by source is pure duplication. Claude sessions and the calendar are NOT scored, so they keep their own sections. "Action required today", "Préparation réunions" and "Objectifs" reference items by permalink/wikilink — they never re-summarise a Must-read entry.

## 📌 Must read
(Items scored ≥7 — one entry per item: score badge, **source tag inline** (`Slack · <canal>` or `Confluence · <espace>`), 2-sentence summary, permalink. Omit section if none.)

## 👀 À surveiller
(Items scored 5–6 — compact bullet list, one line each, **source tag inline**. Omit section if none. Items ≤4: counted only here, shown as "N items low-signal non développés (liens en bas)" — their permalinks live in the `## 🗂 Faible signal — liens` appendix at the bottom.)

## 🗓 Rétro (jour de rétro uniquement)
- C'est le jour de rétro → pense à lancer `/weekly-retro` pour le bilan de la semaine (accomplissements, objectifs, actions). Voir [[retros/index]].
- (Si le backlog de vérification est non trivial — voir règle ci-dessous —, ajouter :) 🔎 N claims inférés sur M pages attendent validation — la rétro proposera une mini-session `/wiki-verify`.

## 📥 Inbox
- (Step 1b — une ligne par item routé : `<texte court> → objectif / tâche / [[page]] / note`. Omettre la section si l'inbox était vide.)

## 📋 Actions en cours
- (tasks ouvertes de state/open-actions.md — **en retard** (`📅` passé) ou échéance ≤ 2 j marquées ⚠️ ; sinon triées par priorité puis ancienneté du `➕`)

## ⚡ Action required today
- (A2 `action_needed` + D decisions expected + `new_actions` détectées ce brief. ONE terse action line each + permalink — do NOT re-summarise an item already developed in Must read; just state the action and link.)

## 🎯 Préparation réunions
- (Per non-routine meeting on REF_DATE: participants [[wikilinks]], open threads, past decisions, 2-3 points à préparer. <15 lines per meeting. Omit if no signal. Skipped for daily/weekly-sync unless a hot open action matches.)

## 📅 Today
- (D today — per meeting: heure, titre, organiser, **Participants** (qui + périmètre, [[fiches]]), prep)

## 📅 Next working day — prepare today
- (D next-working-day, prep items only, same per-meeting shape incl. **Participants**. When `REF_DATE` is Friday this is MONDAY — never Saturday. Use a heading that names the actual day, e.g. "📅 Monday 2026-06-01 — prepare today".)

## 🛠 Claude Code sessions (veille)
- (B grouped by project — not scored, so this is the only place these appear)

## 🎯 Objectifs
- (Per active objective from goals.md: objectif → dernière action liée cette semaine → prochaine action suggérée. 3 lines max per objective. Omit section entirely if goals.md absent or no active objective.)

## 🌱 Recurring topics (fed to wiki)
- (list of topics that triggered wiki page creation/update in Step 5, with links)

## 🧹 Maintenance
- (one line from Agent E / daily-update: fresh/stale/missing, index added, hot.md refreshed, QMD status)

## 🗂 Faible signal — liens (non développés)
- (One line per item from the merged `items_low_links` of A2 + C, format: `[<short title>](<permalink>) — <one_liner commentaire> (<channel/space>)`. The `one_liner` comment is REQUIRED — it's what lets {{profile.owner.name}} judge at a glance whether a dropped item is truly irrelevant; never collapse it into the link title and never omit it. These are the low-signal items kept by A1 but not worth developing — listed here so a dropped subject stays one click away. Omit the section entirely if `items_low_links` is empty.)

## 🔗 Related
- [[previous brief]]
```

**Goals injection** — read `goals.md` at the vault root. For each active objective (i.e. not marked done/archived), generate a 3-line-max block:
```
**<Objectif>** → dernière action liée cette semaine : <action from journal/open-actions> → prochaine action suggérée : <suggestion>
```
Detect "this week" actions by scanning `state/open-actions.md` and the 5 most recent journal entries for keywords matching the objective title. If no action was found this week, write "aucune action cette semaine" for that objective. If `goals.md` does not exist or has no active objective, omit the `## 🎯 Objectifs` section entirely — never create a placeholder.

Brief under 1 200 words. Permalinks, not plain text.

### Step 5 — Wiki page updates on recurring topics (delegate)

Goal: feed the wiki. Daily brief is one-shot (journal). Wiki pages persist across time. Both are kept — different purpose.

For each entry in `recurring_topics` aggregated from A2 + B + C:

1. **Update cumulative topic counter** in `state/topics-counter.json`:
   ```json
   {"<topic-slug>": {"hits": N, "first_seen": "...", "last_seen": "...", "sources": [...]}}
   ```
   Increment `hits` by the number of new occurrences this run.

2. **Threshold check**:
   - `hits >= 3` cumulatively (across runs) → create/update wiki page
   - Confluence RFC merged → immediate page regardless of count
   - Explicit decision logged in Slack → immediate page
   - Otherwise → mention in brief only, NO page yet (counter still incremented)

**People directory growth** — separately from the recurring-topic counter, if Agent D returned `new_people`, the staged stubs in `_raw/morning-brief/people/*.md` must be routed to `entities/` via `wiki-ingest`. This is unconditional — a freshly-met attendee always gets a page on first encounter (no 3-hit threshold; knowing who's in the room is the point). List each created person under `## 🌱 Recurring topics` with a "🆕 fiche personne" tag.

3. **Delegate page creation via TWO PARALLEL subagents** — single message, two `Agent` calls (both on `<synth_model>`). They touch disjoint files (`entities/` vs topic pages) so they never conflict, and splitting avoids one fat agent that returns partial and forces an expensive `SendMessage` resume (the resume re-loads the whole transcript → the same context paid twice). **Give each agent an explicit checklist it MUST complete in one pass — it returns only when every item is done, never partial.**
   - **Agent 5a — people** (spawn only if `new_people` is non-empty): invoke skill `wiki-ingest` on `_raw/morning-brief/people/*.md` → it creates `entities/Prénom Nom.md` (named after the title, kebab alias as link safety net). Checklist: ingest all stubs → verify each page named after its title.
   - **Agent 5b — topics**: for each Slack/Confluence topic over threshold, (i) stage `_raw/morning-brief/YYYY-MM-DD-<topic-slug>.md` (permalinks + 1-paragraph context), (ii) invoke skill `wiki-ingest` (it picks page kind, frontmatter, provenance, wikilinks, sources, manifest), (iii) invoke skill `cross-linker` ONCE to weave the new pages in (prevents orphans), (iv) persist the run's deltas into `state/topics-counter.json`. Sessions-Claude topics are already handled by Agent B — nothing to do.
   - morning-brief writes NO wiki pages directly — both agents stage raw notes and delegate distillation to the existing pipeline.

4. **QMD — defer to the single end-of-run reindex.** Both Step-5 agents pass `QMD=skip` to `wiki-ingest` AND `cross-linker`. The QMD reindex happens EXACTLY ONCE, at the very end, inside Agent E (Step 7) — by then every page written this run exists, so one pass covers them all. Never let Step-5 agents (or their resumes) refresh QMD: re-embedding on each write triples the embedding cost on overlapping content for no benefit.

5. **Tag consistency**: `wiki-ingest` already consults `tag-taxonomy`. Nothing to add.

Append a one-liner per new/updated page in `## 🌱 Recurring topics` section of the brief journal (from `wiki-ingest` and `claude-history-ingest` return values).

### Step 6 — State, manifest, log

`.manifest.json` and `index.md` updates are already done by `wiki-ingest` and `claude-history-ingest` delegations.

Morning-brief's own bookkeeping:

1. **`log.md`** (vault root) — append:
   ```
   - [<now>] MORNING_BRIEF window=<start>..<end> pages_created=X pages_updated=Y slack_clusters=N claude_sessions=M confluence_pages=K
   ```
2. **`state/last-brief.txt`** ← real `now` (ISO) — the actual run time, NEVER `REF_DATE`, in both modes. This keeps the next diff window correct: a Tuesday-20:00 `--night` run followed by a Wednesday-20:00 run yields a clean ~24h window with no gap or overlap.
3. **`state/topics-counter.json`** ← persisted (already updated in Step 5).
4. **`state/open-actions.md`** — append new actions from A2's `new_actions` field, **under the `## Actions` heading** (never inside the `tasks` query blocks), using Obsidian **Tasks** plugin syntax:
   ```
   - [ ] #task @person — description #tag ➕ <today> [📅 <due>] [priority emoji] (source: permalink)
   ```
   - Always include the `#task` tag (it is the plugin's global filter) and the created date `➕ <today>`.
   - Add `📅 <due>` only when a real deadline is known (explicit date, or "semaine prochaine" → that Monday). Add a priority emoji (`⏫`/`🔺` for urgent/deadline-driven, `🔼` default, `🔽` for nice-to-have).
   - Map detected intent to a `#tag`: `#relance` `#decision` `#attente` `#urgent`.
   Never remove or check existing items — only {{profile.owner.name}} does that (clicking the checkbox auto-stamps `✅ date`). Deduplicate: skip if same person + same action already appears unchecked.
5. Echo brief file path to user.

### Step 7 — Final maintenance pass: Agent E (daily-update)

Run **last**, once Step 5 has created/updated every page and Step 6 has persisted state. This is the right moment: the maintenance now reconciles the vault as it actually stands after today's ingestion.

`daily-update` is independent of the brief's session context (it only reads the vault + manifest), so run it in a subagent to keep the file enumeration, `hot.md` regen and QMD work off the orchestrator:

```
Subagent type: general-purpose
Model: <synth_model>

Task — invoke skill `daily-update` in Run Mode (default), as morning-brief's
Agent E (so SKIP its Step-0 idempotence guard — pages were just written).
Run the full maintenance cycle on the vault as it now stands:
source-freshness check, gardener script pass (`_meta/scripts/gardener.py
--apply`: index rebuild, _raw TTL, review queue, archiving, promotions),
hot.md regen, write the vault-scoped state file, validate via
`gardener.py --check`, append the DAILY-UPDATE line to log.md, QMD refresh.
You own the SINGLE QMD reindex for this whole run — the Step-5 agents
skipped QMD on purpose, so reindex now covers every page they wrote.
Do NOT read Slack / calendar / Claude sessions — pure vault maintenance.

Return a one-line summary: fresh/stale/missing counts, index pages added,
hot.md refreshed yes/no, QMD status.
```

After it returns, edit the brief journal's `## 🧹 Maintenance` placeholder (Step 4) with Agent E's one-line summary. No write contention is possible — E is the only writer at this point.

**Verify nudge rule** — Agent E's gardener output includes `verify_backlog_claims` / `verify_backlog_pages`. If `verify_backlog_claims ≥ 20` OR `review_overdue_count ≥ 10`:
- Always: append the backlog one-liner to `## 🧹 Maintenance` (`🔎 N claims inférés sur M pages → /wiki-verify`).
- Retro days (`REF_DATE` weekday == `<retro_day>`): additionally fill the 🔎 line in the `## 🗓 Rétro` section with the real numbers (the retro proposes a mini `/wiki-verify` session — see weekly-retro Step 2b).
Below both thresholds: omit the nudge entirely (no noise).

## Cost notes

- Phase A1 = `<triage_model>` does BOTH the fetch (`slack_read_channel` × N + canvases + 3 searches) AND the KEEP/DROP triage. The raw Slack volume never enters the orchestrator's context — only the compact KEEP JSON returns. Cheapest model, no synthesis. This is the single biggest token saving: the bulk text stays off the session model entirely.
- Phase A2 = `<synth_model>` on the KEEP subset only → does the real work (subagent, so the session model — even the deep tier — never leaks in).
- Agents B/C/D = `<synth_model>` too (subagents). The orchestrator only passes config to A1 and relays the compact JSON between subagents — it never holds raw Slack.
- Agent B delegates to `claude-history-ingest` (local files, no MCP cost).
- Agent C constrained by CQL space filter.
- Agent D reads attachments only when present; wiki-query in index-only mode is cheap.
- If A1 returns `raw_count == 0` → skip A2 entirely (A1 already ran the fetch).
- Agent E (`daily-update`) = `<synth_model>` subagent run **last** (Step 7), after all ingestion, so its index reconcile / `hot.md` regen / QMD refresh cover today's new pages. Sequential by design (it's the finalizer) — the orchestrator only relays its one-line summary, the heavy file enumeration stays in the subagent.
- **Step 5 runs as TWO parallel one-pass subagents** (people ‖ topics), not one fat agent. A single agent that returns partial forces a `SendMessage` resume, and the resume re-loads the full transcript → ~the same context billed twice (measured: a split run cost ~60k extra). Each agent gets an explicit checklist and returns only when complete.
- **QMD reindexes ONCE per run** (inside Agent E). Step-5 agents pass `QMD=skip` to `wiki-ingest` and `cross-linker`. Re-embedding on every write would run 3+ embedding passes on overlapping content for no benefit.

## Delegation map

| Concern | Delegated to |
|---------|--------------|
| Claude session → wiki pages | `claude-history-ingest` (Agent B) |
| Slack/Confluence topic → wiki pages | `wiki-ingest` (Step 5, via `_raw/morning-brief/`) |
| Meeting attendee → person page (who + perimeter) | `entities/` lookup (Agent D); new people staged → `wiki-ingest` (Step 5) |
| Meeting title → relevant wiki context | `wiki-query` index-only (Agent D) |
| Cross-linking new pages | `cross-linker` (post-Step 5) |
| Tag consistency | `tag-taxonomy` (called inside `wiki-ingest`) |
| Wiki maintenance (index reconcile, hot.md, freshness, QMD) | `daily-update` (Agent E, Step 7 — final pass after all ingestion) |

Morning-brief itself only orchestrates + writes the journal + persists state.

## Limits

- Slack: `slack_search_public_and_private` with `in:#name` is unreliable for private channels.
  Always prefer `slack_read_channel(channel_id)` for known channels. IDs are in `state/channels.yml`.
- Slack: `from:<@<owner_user_id>>` search catches {{profile.owner.name}}'s activity in channels not listed in channels.yml.
  Add newly discovered channels to channels.yml after the run.
- Outlook MCP: `outlook_calendar_search` first; `find_meeting_availability` only for slot detail.
- Confluence CQL no "interesting" filter — spaces + recency only.
- {{profile.owner.name}} does not work Sat/Sun. Skip running the brief on weekends unless invoked explicitly.
  The calendar "prepare" section always targets the **next working day**, so a Friday brief previews **Monday**, never Saturday.
- `--night` (evening-before run): only the **presentation anchor** `REF_DATE` shifts to the next working day — the ingestion window (`[last_brief_ts, now]`) and `state/last-brief.txt` stamp stay on real time. Calendar, journal filename, retro-day nudge and task ⚠️ flags all follow `REF_DATE`.
- **Running both (`--night` last night + normal this morning)**: handled by the **refresh run** (Step 0b + Step 4). The morning run detects the existing `journal/<REF_DATE>-brief.md`, re-fetches the calendar fresh, merges the overnight delta into the evening brief (never blanks it), and ingests only the small delta — no double-count, no lost content. This is the recommended combo: rich brief tonight, fresh agenda + overnight catch-up in the morning.
- Corrupted state file → 24h fallback, never crash.
- If a channel in channels.yml has `id: null` → skip read_channel, fall back to search by name.
  Encourage updating the ID when found.
- People directory: `entities/` is the source of truth for who attendees are + their
  perimeter. It grows by encounter — every new named attendee gets a page on
  first sight (no threshold). Match attendees on email first (most reliable), then
  aliases/slack_id/title. Never write `entities/` directly from morning-brief — stage to
  `_raw/morning-brief/people/` and let `wiki-ingest` create the page. Colleague org info
  carries `visibility/internal`. External guests with no signal are listed, not filed.

## Notes

- No Claude footer in brief output.
- Slack permalinks verbatim (stable).
- Confluence: web URL form, not API IDs.
- When channels.yml drifts (channels archived, new teams), suggest user updates it.
- Owner's Slack user ID: `{{profile.sources.slack.user_id}}` (résolu depuis le profil).
