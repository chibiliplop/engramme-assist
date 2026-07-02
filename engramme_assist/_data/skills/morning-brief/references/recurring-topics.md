# Recurring / initiative-matched topics — shared rule

Canonical matching + aggregation logic for the `recurring_topics` output, shared by Agents
**A2** (Slack), **B** (Claude sessions) and **C** (Confluence). This file is the single source of
truth: edit the rule here and all three agents change together.

**Inclusion mechanism** — the orchestrator inlines the text inside the fenced block below into each
agent prompt at its `<recurring_topics_rules>` placeholder, verbatim, exactly like the other
`<...>` substitutions (see SKILL.md → References). Subagents only receive their spawn prompt, so
they never read this file directly — they get its content already substituted in.

The rule is source-agnostic. Each agent's own prompt defines what an "item" is for it (a Slack
message/thread, a Claude session, a Confluence page); this rule governs when items become a
recurring topic and how each topic is tagged.

```
Emit a topic into `recurring_topics` when ANY of:
(a) ≥3 items on the same theme within this window, or the theme spans multiple channels / pages /
    sessions;
(b) it maps to an existing **active** initiative in the index (alias / title / Jira / codebase
    match) — **even at a single mention**, so the orchestrator can absorb the fact into that
    initiative page;
(c) the **topics-counter** (slug → cumulative `hits`, `first_seen`, `last_seen`) shows cumulative
    `hits ≥ 3` OR a **multi-day span** (`first_seen` ≠ `last_seen`, i.e. the theme recurred on more
    than one day).
The trigger is "a page already exists" (→ UPDATE), not "it recurred this run". The orchestrator
turns these into wiki page updates downstream.

You receive the **initiative index** (slug, title, aliases, team, jira_keys, status, codebases).
For each recurring topic:
- set `project` to the matched initiative slug (else `null`);
- set `project_confidence` to `high` (Jira key, alias/title, or codebase match) or `low` — on an
  alias collision, let the item context and any Jira key decide; if unclear, use `low`;
- set `new_project_candidate` to `{"proposed_slug": "...", "proposed_title": "...", "signal": "..."}`
  **only** when the topic shows a strong initiative signal (a Jira/epic key plus a named initiative)
  **and** matches no indexed initiative; otherwise `null`.
```
