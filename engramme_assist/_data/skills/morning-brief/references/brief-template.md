# Brief Journal Template

Read this before writing `journal/<REF_DATE>-brief.md`. The fenced block gives the section order and user-facing labels. Fill it with run data; do not emit placeholder comments. Omit optional sections when their rule says to omit.

## Rendering Rules

- Write all user-facing text in French and keep the literal headings below.
- Use the digest-first / single-mention rule: organize by priority, not by source. Every Slack/Confluence item appears exactly once in its score tier with its source inline (`Slack · <canal>` or `Confluence · <espace>`). Do not add per-source dump sections. Claude sessions and calendar are not scored, so they keep dedicated sections.
- If any source is unscanned, place the `⚠️ Couverture incomplète` block immediately below the title, one line per source. Omit it entirely when all sources were reached.
- Must-read items use a score badge, source tag, 2-sentence summary and permalink.
- Watch items are one-line compact bullets. Low-signal items are counted in `## 👀 À surveiller` and listed with links in `## 🗂 Faible signal — liens`.
- `## ⚡ Action required today`, `## 🎯 Préparation réunions` and `## 🎯 Objectifs` may reference must-read items by permalink/wikilink but must not re-summarize them.
- When a must-read or action item is a decision {{profile.owner.name}} must make or defend, append `→ /sparring` to that line so he can pressure-test his position (the `sparring` skill runs the debate).
- Keep the brief under 1,200 words.

## Day-framing Rules — Plan du jour / Top-3 semaine / Clôture

These three sections open (and, for Clôture, close) the brief so it leads with {{profile.owner.name}}'s **own** workload for `REF_DATE`, not only incoming information.

### `## ☀️ Plan du jour`

Always emit this section — it is the answer to "what do I do today". Keep it to **≤6 lines**. Derive the **top 3 of the day** by ranking these candidates and keeping the 3 highest-priority:

1. The week's Top-3 (`## 🎯 Top-3 semaine`) items still `⏳` — these are THE priorities.
2. `state/open-actions.md` tasks overdue before `REF_DATE` or due within 2 days.
3. `porteur` initiatives in `_meta/portfolio.json` that are `is_stale` OR have an imminent MEP / `next`.
4. `REF_DATE`'s decision-heavy meetings (Agent D items flagged "décision attendue").
5. The Clôture "important demain" answer, when Step 1c captured one.

Render each as one numbered line: the action + why-now (échéance / MEP / réunion) + a `[[wikilink]]` or permalink. Do not re-summarize a must-read item — reference it. Then one **capacity line**: `Capacité : ~Xh utiles` where X ≈ a working day (~8h) minus the total meeting hours on `REF_DATE` (from Agent D start–end times). When the plan is heavier than the capacity (more must-do items than the hours reasonably allow, or capacity < 3h), append exactly **one** defer/delegate suggestion — `→ reporter <item>` or `→ déléguer <item> à @<personne>`, the single most offloadable item. In `--night` mode the plan targets `REF_DATE` (the next working day), like the rest of the brief.

### `## 🎯 Top-3 semaine`

One compact line framing the current week's three priorities — kept **distinct** from the generic `## ⚡ Action required today` / `## 📋 Actions en cours` lists so it never loses its "these are THE priorities" framing. Source: the most recent `retros/*-retro.md`, its `## 🎯 Top 3 — semaine prochaine` section (its "next week" = the current week); fallback when no retro exists: the open `#retro` tasks in `state/open-actions.md`. State each item `✅` (a matching `#retro` task is checked, or this week's closed actions/briefs clearly satisfy it) or `⏳` (still open). Render as ONE line:

```markdown
- 1) <libellé court> ✅ · 2) <libellé> ⏳ · 3) <libellé> ⏳ — <week>, [[retros/<week>-retro]]
```

Omit the section only when there is neither a retro Top-3 nor any open `#retro` task.

### `## 🌙 Clôture` (`--night` only)

Populated from Step 1c's close-out answers (asked once at `--night` launch, fully skippable):

```markdown
## 🌙 Clôture
- **Bougé aujourd'hui :** <réponse 1>
- **Important demain :** <réponse 2>
```

Omit the whole section when the run is not `--night`, when {{profile.owner.name}} skipped, or on a `REFRESH` run (the block was already written by the originating `--night` run). The weekly retro reads this block straight from the journal brief as accomplishments / next-day signal — no separate state file.

## Refresh Rules

When `REFRESH=true`, an existing brief from a prior `--night` run already exists for `REF_DATE`. Do not overwrite it wholesale:

- Add this banner below the title: `> 🔄 Rafraîchi le matin à <HH:MM> — agenda re-vérifié + delta depuis le brief de la veille.`
- Replace `## 📅 Today` and `## 📅 Next working day — prepare today` fully from fresh Agent D output.
- Recompute `## ☀️ Plan du jour` and `## 🎯 Top-3 semaine` fresh against `REF_DATE`. Keep the `## 🌙 Clôture` block as-is — it was captured at the originating `--night` launch; never re-ask it on a refresh.
- Merge Slack, Confluence and Claude-session deltas into existing sections: prepend new items, tag them `(maj matin)`, and keep yesterday's items. If a delta is empty, leave that section as-is.
- Recompute and rewrite actions/tasks against `REF_DATE`.
- Keep existing frontmatter `created` and first `window`; extend `window` end to `now` and add `refreshed: <now>`.
- Continue Steps 5-7 on the delta only; no double ingestion.

## Meeting Prep Rules

For each meeting on `REF_DATE` that is not a routine recurring meeting, generate a concise box under `## 🎯 Préparation réunions`. Skip routine daily/weekly syncs unless a hot open action in `state/open-actions.md` matches the meeting title.

Per qualifying meeting:

- Participants: resolved attendees as `[[Prénom Nom]]` wikilinks, exact page title, never kebab slug. Mark `🆕` if just created.
- Open threads: cross-reference unchecked `#task` lines in `state/open-actions.md` and the last 3 journal entries; max 3 lines.
- Past decisions: run `qmd query "<meeting title> <key topic words>"` and scan `decisions/` if present; surface up to 3 relevant decisions/pages with wikilinks.
- Points à préparer: 2-3 actionable bullets.

Keep each meeting box under 15 lines. Open threads and past decisions come first. Skip the box if the meeting has no signal.

## Goals Rules

Read `goals.md` at the vault root. For each active objective, emit at most 3 lines:

```markdown
**<Objectif>** → dernière action liée cette semaine : <action from journal/open-actions> → prochaine action suggérée : <suggestion>
```

Detect this week's actions by scanning `state/open-actions.md` and the 5 most recent journal entries for keywords matching the objective title. If none were found, write `aucune action cette semaine`. If `goals.md` is absent or has no active objective, omit `## 🎯 Objectifs`.

### `## 📁 Portefeuille`

Source: `_meta/portfolio.json`. **Why compact**: the brief must be glanceable, so name only what needs a decision and collapse the rest into a counter.

Rules:
- Omit the whole section if `projects` is empty or the script returned `{"disabled": true}`.
- One line per engagement tier present, ordered porteur → contributeur → observateur, prefixed `🔴`/`🟡`/`⚪`.
- On a tier line, name only initiatives that are `status: active` AND (`is_stale` OR have a `next`). For each: bold title; if `is_stale`, append `stagne {days_stale}j`; else if `next`, append `→ {next}`.
- Collapse active-but-calm initiatives (not stale, no `next`) into a trailing `· +N au calme`. Collapse all non-stale observateur into `⚪ observateur — N en veille (RAS)`.
- Omit a tier line if it has no active initiative.

Example:

```markdown
## 📁 Portefeuille
- 🔴 porteur — **Doublons/Reboost** → MEP juillet · **Golden path** stagne 12j
- 🟡 contributeur — **Alerting serial** stagne 18j · +2 au calme
- ⚪ observateur — 3 en veille (RAS)
```

## Template

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

## ☀️ Plan du jour
- **1.** <action prioritaire> — <pourquoi maintenant> — <lien>
- **2.** <action> — <pourquoi maintenant> — <lien>
- **3.** <action> — <pourquoi maintenant> — <lien>
- Capacité : ~<X>h utiles après réunions [· → reporter/déléguer <item> si surchargé]

## 🎯 Top-3 semaine
- 1) <libellé> ✅ · 2) <libellé> ⏳ · 3) <libellé> ⏳ — <week>, [[retros/<week>-retro]]

## 📌 Must read
- <score> — <source> — <résumé 2 phrases> — <permalink>

## 👀 À surveiller
- <score> — <source> — <ligne compacte> — <permalink>
- N items low-signal non développés (liens en bas)

## 🗓 Rétro
- C'est le jour de rétro → pense à lancer `/weekly-retro` pour le bilan de la semaine (accomplissements, objectifs, actions). Voir [[retros/index]].
- 🔎 N claims inférés sur M pages attendent validation — la rétro proposera une mini-session `/wiki-verify`.

## 📥 Inbox
- <texte court> → objectif / tâche / [[page]] / note

## 📋 Actions en cours
- <tâche ouverte> <⚠️ si en retard ou échéance ≤ 2 j>

## ⚡ Action required today
- <action brève> — <permalink>

## 🎯 Préparation réunions
### <heure> — <réunion>
- Threads ouverts : <liens/actions>
- Décisions passées : <wikilinks>
- Participants : [[Prénom Nom]] — <rôle>, <équipe> — périmètre : <périmètre>
- Points à préparer : <2-3 points>

## 📅 Today
- <heure> — <titre> — organisateur : <nom> — Participants : <qui + périmètre + [[fiches]]> — prep : <points>

## 📅 Next working day — prepare today
- <jour réel YYYY-MM-DD> — <prep uniquement, participants inclus>

## 🛠 Claude Code sessions (veille)
- <projet> — <but> — fichiers — état — TODO/blocages

## 🎯 Objectifs
- **<Objectif>** → dernière action liée cette semaine : <action> → prochaine action suggérée : <suggestion>

## 🌱 Recurring topics (fed to wiki)
- [[Page]] — créée/mise à jour
- [[Prénom Nom]] — 🆕 fiche personne

## 🧹 Maintenance
- <résumé Agent E>

## 🗂 Faible signal — liens (non développés)
- [<titre court>](<permalink>) — <one_liner commentaire> (<canal/espace>)

## 🌙 Clôture
- **Bougé aujourd'hui :** <réponse 1>
- **Important demain :** <réponse 2>

## 🔗 Related
- [[previous brief]]
```

Omit `## 🎯 Top-3 semaine`, `## 🌙 Clôture`, `## 🗓 Rétro`, `## 📥 Inbox`, `## 🎯 Objectifs`, `## 🗂 Faible signal — liens` and any empty scored section per their rules. `## ☀️ Plan du jour` is always emitted. In the low-signal appendix, the `one_liner` comment is required so {{profile.owner.name}} can judge relevance at a glance.
