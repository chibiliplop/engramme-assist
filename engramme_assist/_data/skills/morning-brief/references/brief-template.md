# Brief Journal Template

Read this before writing `journal/<REF_DATE>-brief.md`. The fenced block gives the section order and user-facing labels. Fill it with run data; do not emit placeholder comments. Omit optional sections when their rule says to omit.

## Rendering Rules

- Write all user-facing text in French and keep the literal headings below.
- Use the digest-first / single-mention rule: organize by priority, not by source. Every Slack/Confluence item appears exactly once in its score tier with its source inline (`Slack · <canal>` or `Confluence · <espace>`). Do not add per-source dump sections. Claude sessions and calendar are not scored, so they keep dedicated sections.
- If any source is unscanned, place the `⚠️ Couverture incomplète` block immediately below the title, one line per source. Omit it entirely when all sources were reached.
- Must-read items use a score badge, source tag, 2-sentence summary and permalink.
- Watch items are one-line compact bullets. Low-signal items are counted in `## 👀 À surveiller` and listed with links in `## 🗂 Faible signal — liens`.
- `## ⚡ Action required today`, `## 🎯 Préparation réunions` and `## 🎯 Objectifs` may reference must-read items by permalink/wikilink but must not re-summarize them.
- Keep the brief under 1,200 words.

## Refresh Rules

When `REFRESH=true`, an existing brief from a prior `--night` run already exists for `REF_DATE`. Do not overwrite it wholesale:

- Add this banner below the title: `> 🔄 Rafraîchi le matin à <HH:MM> — agenda re-vérifié + delta depuis le brief de la veille.`
- Replace `## 📅 Today` and `## 📅 Next working day — prepare today` fully from fresh Agent D output.
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

## 🔗 Related
- [[previous brief]]
```

Omit `## 🗓 Rétro`, `## 📥 Inbox`, `## 🎯 Objectifs`, `## 🗂 Faible signal — liens` and any empty scored section when they have no content. In the low-signal appendix, the `one_liner` comment is required so {{profile.owner.name}} can judge relevance at a glance.
