---
name: wiki-profile
description: >
  Fills or updates the engramme-assist profile (identity, sources, tool prefs, the brief's
  scoring grid), verifies the MCP servers the skills depend on, and resolves concrete IDs
  (Slack channels, Confluence spaces). Interactive, exhaustive, non-destructive. Triggers:
  called by wiki-init at setup; or "update my profile", "change my channels",
  « mets à jour mon profil », « ajoute un canal Slack ».
---

# wiki-profile

> In this document, `$VAULT` is shorthand for `$OBSIDIAN_VAULT_PATH`.

Builds the profile read by every skill, **verifies the MCP servers** they depend on, and
**resolves concrete IDs**. **Non-destructive**: an existing profile is completed, never overwritten.

## Invariant — interactive, never a pass-through

This skill **converses** with the user, one family at a time, and **waits for their answer**
before continuing. Offering existing values as defaults is allowed, but:
- **never** silently auto-accept a default nor rubber-stamp the whole thing;
- **never** fabricate an answer on the user's behalf;
- **never** degrade into a pass-through (writing the profile without having asked the questions).
When called by `wiki-init`, interactive mode stays mandatory.

## Locations (layers)
- Global, stable identity → `~/.obsidian-wiki/profile.yml` (`owner:`)
- Vault, vault-specific context → `$VAULT/_meta/profile.yml` (`sources`, `tools`, `brief`). The vault overrides the global on merge.
- Sensitive values (channels, user_id) → always in the **vault** profile (private).

## Required-MCP map (source of truth)

Each profile source depends on an MCP server. Before collecting an enabled source, **verify**
its availability with a lightweight call; see the **MCP preflight** step in the Procedure.

| Profile source       | MCP server    | Consuming skills            | Check (lightweight call)   |
|----------------------|---------------|-----------------------------|----------------------------|
| `sources.slack`      | Slack         | morning-brief, weekly-retro | `slack_search_users`       |
| `sources.confluence` | Atlassian     | morning-brief, weekly-retro | `getConfluenceSpaces`      |
| `sources.calendar`   | Microsoft 365 | morning-brief, weekly-retro | `outlook_calendar_search`  |

## `brief` (scoring) schema — explicit

The setup agent has **no context beyond this skill**: the schema is given here in full, and a
**complete example profile ships next to this skill** in `profile.example.yml` (same folder as this
`SKILL.md`). Read it to see a profile filled in end to end (`owner` / `sources` / `tools` / `brief`);
its `brief:` block shows `scoring_axes` with their `weight`.

`brief.scoring_axes` is a **list** of axes. Each axis is a mapping with **three required keys**:

| Key           | Type            | Role                                                                      |
|---------------|-----------------|---------------------------------------------------------------------------|
| `name`        | text            | short axis label (human-readable, used in the recap).                     |
| `weight`      | **integer ≥ 1** | **required** — points added to an item's score when it matches this axis. |
| `description` | text (1 line)   | match clause read by the LLM: "does this item touch on …?".               |

Exact syntax (inline YAML, **one line per axis**):
```yaml
brief:
  scoring_axes:
    - { name: <label>, weight: <integer ≥ 1>, description: "<match clause>" }
    - { name: …,       weight: …,             description: "…" }
  thresholds: { must_read: <integer>, watch: <integer> }   # must_read > watch
```

`brief.thresholds` — two integers, **`must_read > watch`**:
- score ≥ `must_read` → item is "must read";
- `watch` ≤ score < `must_read` → "to watch";
- score < `watch` → counted only.

`portfolio` is a **root-level** block (sibling of `brief`, not nested inside it). It controls
the derived project portfolio view:
```yaml
portfolio:
  enabled: true
  stale_days:
    porteur: 10
    contributeur: 21
    observateur: 45
```

**How the score is computed** (on the `morning-brief` side, to calibrate weights/thresholds): an
item's score = sum of the `weight` of the axes whose `description` matches (judgment, not a
mechanical sum); no axis matches → score 1. So pick thresholds consistent with the sum of weights
(e.g. weights `3+3+2+2` → `must_read: 7`, `watch: 5`).

**Complete filled-in template** (role "software architect"; adapt to the real role):
```yaml
brief:
  scoring_axes:
    - { name: Architectural relevance,  weight: 3, description: "Affects system design, ADRs, technical debt, cross-team dependency." }
    - { name: Product/business impact,  weight: 3, description: "Touches user experience or key product metrics." }
    - { name: Technical urgency,        weight: 2, description: "Vulnerability, deprecation, prod incident, breaking change." }
    - { name: Actionable change signal, weight: 2, description: "RFC, tooling choice, team reorg, explicit request." }
  thresholds: { must_read: 7, watch: 5 }
```
Whole filled-in profile (all families): `profile.example.yml`, shipped in this folder.

## Procedure

1. **Resolve the vault** via the Config Resolution Protocol (`.env` → `~/.obsidian-wiki/config`).
2. **Load the existing profile**: read `~/.obsidian-wiki/profile.yml` and `$VAULT/_meta/profile.yml`
   if they exist. Use them as **proposed defaults** — but always confirm (cf. invariant).
3. **Q&A per family** (one at a time, wait for the answer):
   - **Identity** → `owner.name` (**required**), `owner.full_name`, `owner.role` (**required**),
     `owner.team`, `owner.lang`. `full_name`/`team`/`lang` may be **explicitly declined**
     ("skip it") — never silently skipped.
   - **Tools** → `tools.model_tiers` (offer the default `{triage: haiku, synth: sonnet, deep: opus}`),
     `tools.link_format`, `tools.retro_day`.
   - **Brief (scoring)** → present the **"`brief` (scoring) schema" above**, offer a starting grid
     derived from `owner.role` (cf. `brief.role_fallback`), and let the user confirm or edit. The
     schema's rules are binding here: every axis needs a `weight`, `thresholds` needs `must_read > watch`.
   - **Portfolio** → offer the root-level `portfolio` defaults above; let the user disable it or adjust
     stale-day thresholds by engagement tier.
   - **Sources** — for EACH source (Slack, Confluence, Calendar), first ask
     **« Tu utilises X ? »** (opt-in). If **no** → don't write the source, move to the next.
     If **yes**:
     1. **MCP preflight** (hybrid): verify the server via the call in the map above.
        - **Available** → continue.
        - **Absent** → offer the user: *(a)* wire it up now (give the steps, wait, re-test)
          **or** *(b)* **defer** this source — mark it `pending` (config collected but IDs left `null`).
     2. **Assisted discovery** (MCP available) — **advise, never impose**. First ask
        **« Tu veux que je liste ce qui existe et que je te propose une sélection ? »**.
        If **no** → manual entry (step 3). If **yes** → enumerate, then present **two explicit
        lists — "✅ proposed to keep" and "🚫 proposed to ignore" — with one reason per line**,
        and ask the user to decide (keep, drop, add). **The user always has the last word**;
        write nothing they haven't approved.
        - **Slack** → `slack_search_channels` to enumerate candidate channels (by team name
          `owner.team`, common prefixes). **Keep** = channels tied to the team/role; **ignore**
          = noise (`*-bots`, `*-alerts`, `*-notif`, `random`) → proposed as `excluded_patterns`.
        - **Confluence** → `getConfluenceSpaces` to list the spaces. **Keep** = spaces that match
          `owner.team` / `owner.role` (role keywords); **ignore** = the rest, listed by name so the
          user can add some back. Always show both sides.
        - **Calendar** → nothing to select (access only); no discovery.
     3. **Collection** (the outcome of discovery, or manual entry if declined):
        - **Slack** → `sources.slack.user_id`; the **list of channels to follow**;
          `excluded_patterns` (Slack channel-name patterns, **never** file globs).
        - **Confluence** → the **list of spaces** (`sources.confluence.spaces`).
        - **Calendar** → access only (`sources.calendar: true`).
     4. **Immediate resolution** (if MCP available):
        - Slack: for each kept channel, `slack_search_channels` → write the real `id`.
          If not found, leave `null` and flag it.
        - Confluence: `getConfluenceSpaces` → validate that each space key exists; flag unknowns.
        - Calendar: `outlook_calendar_search` (short window) → confirm that reads work.
4. **Write the files**:
   - `owner:` → `~/.obsidian-wiki/profile.yml`
   - `sources` / `tools` / `brief` / `portfolio` → `$VAULT/_meta/profile.yml`
   - Format: YAML, one line per axis `{ name, weight, description }` (cf. schema) — never an axis
     without a `weight`, never a bare label nor a wall of text.
5. **Bootstrap `state/channels.yml`** (vault-relative): if it **doesn't exist**, write it with the
   `team_channels` (with resolved `id`s, else `null`) + `excluded_patterns`. Exact schema
   (the example isn't shipped next to the skill — template given here):
   ```yaml
   team_channels:
     - { name: "team-eng",  id: "C0123ABCD", type: public_channel }  # id resolved via slack_search_channels
     - { name: "incidents", id: null,        type: public_channel }  # null if unresolved (resolved on 1st run)
   excluded_patterns: ["*-bots", "random"]   # Slack channel-NAME patterns, not file globs
   ```
   If it **exists**, DO NOT overwrite it — offer to add the new channels only.
6. **Confirm**: recap of the files written, the fields filled, and per source: ✅ resolved /
   ⏳ `pending` (MCP deferred).

## Rules
- Interactive is mandatory (cf. invariant); at most one family at a time.
- **Discovery advises, the user decides.** Never keep or drop a channel/space silently and never
  impose a selection — the user has the last word.
- Never **invent** a `user_id` or a channel `id`. Instead, actively **resolve** via
  `slack_search_channels` / `getConfluenceSpaces` when the MCP is available.
- Idempotent: re-running completes a partial profile without losing anything, and tries to
  resolve the still-`null` IDs.
