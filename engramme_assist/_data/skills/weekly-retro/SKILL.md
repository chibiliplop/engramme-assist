---
name: weekly-retro
description: Weekly retrospective for the wiki owner — interactive Q&A primed by the week's auto-compiled data (daily briefs, closed tasks, sessions, calendar). Captures impact-framed accomplishments, what went well/badly, energy, visibility, learnings, collaboration; reviews prior actions and goals; detects recurring patterns; feeds open-actions.md, goals.md, brag/<YYYY>-inputs.md (continuous brag capture), and a persistent retros/ history usable for the annual review. Offers a ~10-claim wiki-verify mini-session when the inferred-claims backlog reaches 20 (the only recurring trigger for that skill). After the interactive session it runs a non-interactive weekly maintenance tail (non-Claude history ingests, cross-linker, hot-topics regeneration, wiki-lint report; plus monthly rétro mensuelle + brag compilation + synthesize/dedup/tag-audit/digest on the last retro of the month). Triggers on "/weekly-retro", "rétro", "rétrospective", "bilan de la semaine", or on the retro day after the morning brief. The "annual" mode compiles all the year's retros into a self-assessment draft.
---

# weekly-retro

Run a structured weekly retrospective with {{profile.owner.name}} every `{{profile.tools.retro_day}}`. The core principle: **never start from a blank page**. The week's evidence already lives in the vault (daily briefs in `journal/`, closed tasks in `state/open-actions.md`, the topics counter, the calendar). The skill compiles that first, presents a grounded draft, and the interactive Q&A then *interprets and prioritises* — it does not try to reconstruct the week from memory.

## When to use

- Manual invocation `/weekly-retro` (or "rétro", "bilan de la semaine"), typically `{{profile.tools.retro_day}}` afternoon.
- The `{{profile.tools.retro_day}}` `morning-brief` adds a nudge to run it.
- `/weekly-retro annual [year]` → annual review compiler mode (see end of file).

## Inputs

- **Working directory** — must be `$OBSIDIAN_VAULT_PATH` (résolu via le Config Resolution Protocol). Abort with a clear message otherwise.
- **Today + ISO week** — get via `date +"%Y-%m-%d %G-W%V %u"` (weekday 1=Mon…7=Sun). The retro covers the **current ISO week, Monday 00:00 → now** — unless the late-retro catch-up (Step 0.5) retargets it to the previous week or extends the window.
- **Persistent state**:
  - `retros/YYYY-Www-retro.md` — one file per week (this run writes the current one).
  - `goals.md` (vault root) — short/medium/long-term goals, parseable format described in its header.
  - `state/retro-patterns.json` — recurring-theme counters for escalation.
  - `state/last-retro.txt` — ISO week of the last completed retro.
  - `state/maintenance-plan-{iso_week}.json` — Step 9 maintenance plan: the full per-action detail with stable IDs (written by Phase B, consumed by Phase D). Persists deferred actions as a standing worklist across weeks.

## Output language

The interactive session **and** the written retro are in **French**, full sentences ({{profile.owner.name}}'s wiki prose convention — no terse fragments). This SKILL file is in English; what {{profile.owner.name}} reads is French.

## Process

### Step 0 — Guard + bootstrap

1. Confirm working dir is the wiki. Otherwise abort.
2. Run `date +"%Y-%m-%d %G-W%V %u"`. Derive: `today`, `iso_week` (e.g. `2026-W22`), `weekday`. Compute the **Monday of this ISO week** as the window start.
3. Ensure these exist, create from the conventions if missing: `retros/` dir, `goals.md`, `state/retro-patterns.json` (`{}`), `state/last-retro.txt`.
4. If `state/last-retro.txt` already equals `iso_week`, tell {{profile.owner.name}} a retro for this week exists and ask whether to **edit/extend it** or start fresh.
5. **Late-retro catch-up** — compute `prev_week` = ISO week of (today − 7 days). If `retros/{prev_week}-retro.md` does NOT exist (last week was never retro'd) and step 4 didn't trigger:
   - **Weekday 1–3 (Mon–Wed)**: ask ONE question — "La semaine {prev_week} n'a pas eu de rétro — on rattrape la semaine dernière (recommandé) ou on fait la semaine en cours ?" On catch-up (default): set `target_week = prev_week` and `window = Monday 00:00 → Sunday 23:59 of prev_week`. EVERYTHING downstream uses `target_week`, not the calendar week: the retro filename `retros/{target_week}-retro.md`, the `week:` frontmatter, `retro-patterns.json` weeks, the log line, and the **monthly gates** (first/last retro of the month are evaluated against `target_week`'s month). The evidence is already on disk (briefs and tasks are immutable), so the compile works identically. After writing, `state/last-retro.txt` ← `target_week` — the normal `{{profile.tools.retro_day}}` retro for the current week stays possible and unaffected.
   - **Weekday 4–5 (Thu–Fri)**: don't produce two retros back-to-back — extend the current retro's window back to Monday of `prev_week` and title it for both weeks ("Rétro — {prev_week}–{iso_week}", filename stays `retros/{iso_week}-retro.md`, frontmatter `period` covers the full span). Say explicitly in the opening draft that it covers two weeks.
   - If `prev_week`'s retro exists → no-op, normal current-week flow.

### Step 1 — Auto-compile the week (the priming, no questions yet)

Gather in parallel, then synthesise a draft. **Do the work yourself; do not ask {{profile.owner.name}} anything in this step.**

- **Daily briefs** — read every `journal/YYYY-MM-DD-brief.md` with a date in the window (Mon→today). Extract: action-needed items, decisions, recurring topics, Claude-session work per project, Confluence pages, meetings that mattered.
- **Closed tasks** — read `state/open-actions.md`. Collect lines with `✅ YYYY-MM-DD` where the date is in the window (accomplishments) **and** still-open lines (carry-over / blocked).
- **Topics counter** — read `state/topics-counter.json` for themes that crossed the recurrence threshold this week.
- **Previous retro** — read the most recent file in `retros/` (by week). Extract its **action items** (for the accountability loop, Step 2) and its **top-3 next-week intentions** (did they happen?).
- **Goals** — read `goals.md`. Load all non-closed goals with their `revu:` dates.
- **Calendar (optional, if Outlook MCP available)** — `outlook_calendar_search` for the window to recover notable meetings attended. Skip silently if unavailable. For each notable meeting, **resolve the key attendees** against the wiki `entities/` person pages (the people directory built by `morning-brief`): grep `entities/*.md` frontmatter (pages tagged `person`) matching the attendee's `email` / `aliases` / `slack_id` / `title`, and pull `role`, `team`, `perimeter`, and the [[wikilink]]. This lets the retro say not just *that* {{profile.owner.name}} met someone but *who they are and what they own* — the raw material for the Collaboration section (3.7). If an attendee {{profile.owner.name}} clearly worked with this week has no page yet, note it so a stub can be created (delegate to `wiki-ingest` like `morning-brief` does); don't block the retro on it.

Produce a **« Semaine en bref »** draft (in French), grounded in the above:
- Accomplishments observed (bullet list, with the evidence: which brief/task/permalink).
- Carry-over / unfinished.
- Recurring topics surfaced.
- Goals due for review and their last-known progress.

Present this draft to {{profile.owner.name}} as the opening of the session, then move to Step 2. Keep it scannable.

### Step 1b — Continuous brag capture (silent, no user interaction)

**Immediately after** producing the « Semaine en bref » draft, extract notable accomplishments from the evidence gathered in Step 1 and append them to `brag/<YYYY>-inputs.md` (`<YYYY>` = année courante, dérivée de la date du jour, pas du profil). Do this silently — no questions, no confirmation. A notable accomplishment qualifies if it is: a decision arbitrated, a design doc delivered, an incident resolved, a squad unblocked, a delivery shipped, or a cross-team contribution. Each item on one line:

```
- YYYY-MM-DD — <action concise> — impact: <impact pour qui, quel résultat> — preuve: [[page]] ou lien Jira/MR
```

Rules:
- Append under the correct `## <Mois YYYY>` section (create the section header if the month is not yet present).
- Deduplicate: if an identical `<action concise>` already appears in the month's section, skip it (NOOP).
- If the evidence from Step 1 yields no qualifying accomplishment, append nothing.
- The Q&A in Step 3 section 1 (Accomplissements → impact) also feeds this file: for each accomplishment {{profile.owner.name}} confirms or adds, append (or update) a line immediately after his response, before moving to the next Q&A section.

### Step 2 — Accountability loop: review the previous retro's actions

Before generating new actions, close the loop on the old ones. From the previous retro's action items + top-3 intentions, ask {{profile.owner.name}} per item: **fait / pas fait / partiellement — et pourquoi ?**

Use a single `AskUserQuestion` (multiSelect where natural) listing the prior actions; let "Other" capture nuance. For each "pas fait", probe briefly: still relevant? re-roll into this week, or drop? This is what turns the retro from journaling into behaviour change — do not skip it. If there is no previous retro, say so and skip.

### Step 2b — Mini-vérification wiki-verify (gated, ~5 min)

`/wiki-verify` is interactive-only and belongs in no automated queue — this step is its **only recurring trigger**, placed here because the retro is the moment {{profile.owner.name}} is already present and in confirmation mode.

> Interpréteur : `python3` sur macOS/Linux, `python` sur Windows.

Gate: run `python3 _meta/scripts/gardener.py` (dry-run) and read `verify_backlog_claims`. If `≥ 20`, ask ONE question (can be batched into the Step 2 `AskUserQuestion`): "Le backlog de vérification contient N claims sur M pages — on en passe ~10 en revue maintenant (5 min) ?" Options: **Oui (10 claims)** · **Non, pas cette semaine**.

- **Oui** → invoke skill `wiki-verify` scoped to the top pages from `verify_backlog_top5` (≈10 claims max, then stop — this is a mini-session, not a purge). Its bookkeeping (lifecycle bumps, `last_verified`, log) is self-managed.
- **Non** → note it and move on; the backlog count reappears next `{{profile.tools.retro_day}}`. Never insist, never auto-run.
- Below 20 claims → skip this step silently.
- "Express" mode → skip this step.

### Step 3 — Interactive Q&A (Standard depth, ~20 min)

Walk these sections **in order**, each primed with the Step-1 draft so {{profile.owner.name}} reacts/edits rather than recalls. Mix two interaction styles: present the draft and invite free-text reflection in the conversation, and use `AskUserQuestion` for structured choices (ratings, triage, goal status). Batch related prompts (≤4 per `AskUserQuestion` call). Keep momentum — this is `{{profile.tools.retro_day}}`, not a tribunal.

1. **Accomplissements → impact (So What).** Present the observed accomplishments. For each kept one, push for the *impact*, not the activity: pour qui, quel résultat, quelle portée. Use the *So What / Why / Now What* framing. The goal: each line should be liftable verbatim into a self-assessment. Let {{profile.owner.name}} add accomplishments the data missed.
2. **Ce qui va bien.** What worked, what to keep doing. Tie to accomplishments where relevant.
3. **Ce qui va mal.** Frictions, blockers, frustrations. For each, capture a short **theme slug** (e.g. `ci-flaky`, `reunions-trop-longues`, `manque-specs`) — needed for pattern detection in Step 4. Cross-reference: if a theme already has hits in `state/retro-patterns.json`, surface "ça revient pour la Nᵉ fois".
4. **Énergie & soutenabilité.** Qu'est-ce qui t'a nourri / vidé ? Charge tenable cette semaine ? Signaux à surveiller ? (One quick `AskUserQuestion` rating + free text.)
5. **Visibilité.** Qu'as-tu fait que personne ne sait ? Faut-il le rendre visible (post Slack, page Confluence, démo, 1:1 manager) ? Anything here often becomes an action in Step 5.
6. **Apprentissages.** Ce que tu as appris cette semaine ; un truc que tu referais autrement.
7. **Collaboration.** Qui tu as aidé, qui t'a aidé, frictions interpersonnelles/équipe à désamorcer. Prime this from the Step-1 resolved attendees: name the people {{profile.owner.name}} actually worked with this week **with their périmètre** (e.g. "tu as bossé avec X (Tech Lead Search, périmètre indexation) sur …"), so the collaboration map is concrete and tied to who owns what — not a vague "j'ai aidé des gens". Surface cross-team collaboration explicitly (working outside one's own perimeter is visibility-worthy). If the week revealed someone's perimeter changed, that's a cue to update their `entities/` page.
8. **Objectifs.** Walk each active goal from `goals.md`: avancement depuis la dernière revue ? statut (`en-cours`/`atteint`/`abandonné`/`en-pause`) ? Flag any goal with no movement for **2+ weeks** as `⚠️ stallé` and ask whether to renew, re-scope, or drop. Then ask for **new goals** by horizon (court/moyen/long).
9. **Actions d'amélioration.** From everything above, agree on a small set of concrete actions (quality over quantity — 2 to 5). These go to `open-actions.md`.
10. **Top 3 semaine prochaine.** The three priorities for next week → injected into Monday's `morning-brief` context and recorded in the retro.

### Step 4 — Pattern detection + escalation

Update `state/retro-patterns.json`. For each theme from Step 3.3 (and notable frictions from 3.7):

```json
{
  "<theme-slug>": {
    "label": "libellé lisible",
    "type": "negative | friction",
    "hits": N,
    "first_seen": "2026-W20",
    "last_seen": "2026-W22",
    "weeks": ["2026-W20", "2026-W21", "2026-W22"],
    "escalated": false
  }
}
```

Increment `hits` and append `iso_week` to `weeks` (dedupe). **Escalation rule**: when a theme reaches `hits >= 3` and `escalated` is false → it is no longer a one-off; propose to {{profile.owner.name}} creating a structural decision note in `decisions/` (delegate to `wiki-ingest` with a staged note, or draft an ADR-style entry). On acceptance, set `escalated: true` and record the decision link. Surface escalations explicitly in the retro's `## 🔁 Patterns récurrents` section.

### Step 5 — Write the retro file

Write `retros/YYYY-Www-retro.md`:

```markdown
---
title: Rétro — {iso_week}
date: {today}
week: {iso_week}
type: retro
tags: [retro, weekly, review]
period: [{monday}, {today}]
---

# Rétro — {iso_week}

## 🏆 Accomplissements (impact)
- **{accompli}** — *So what:* {impact, pour qui, résultat}. {evidence: lien brief/tâche/permalink}

## ✅ Revue des actions précédentes
- {action} — fait ✅ / pas fait ❌ / partiel 🟡 — {pourquoi / suite}

## 👍 Ce qui va bien
- …

## 👎 Ce qui va mal
- {libellé} `[{theme-slug}]` {× N si récurrent}

## 🔋 Énergie & soutenabilité
- …

## 👀 Visibilité
- …

## 🧠 Apprentissages
- …

## 🤝 Collaboration
- …

## 🎯 Objectifs — revue
- {objectif} — {statut} — {avancement} {⚠️ stallé si applicable}

## 🔁 Patterns récurrents
- {theme} — {N} semaines — {action / escaladé en [[decision]]}

## 🚀 Actions d'amélioration
- {action} → ajoutée à [[open-actions]] (#retro)

## 🎯 Top 3 — semaine prochaine
1. …
2. …
3. …

## 🧹 Maintenance hebdo
- Ingests historiques : {agents + nb sessions, ou "rien de neuf"}
- Cross-linking : {N liens ajoutés}
- Hot topics : {N topics qualifiants régénérés dans [[synthesis/hot-topics]], ou "aucun qualifiant"}
- Lint : {N/N corrections appliquées} {liens cassés / orphelins / contradictions / périmé restants}
- Mensuel (1ʳᵉ rétro du mois) : {synthèse: N pages · dedup: N/N fusionnés · tags: N/N corrigés · digest, ou "—"}
- Mensuel (dernière rétro du mois) : {rétro mensuelle: [[retros/YYYY-MM-monthly]] · brag: N items compilés dans [[brag/<YYYY>]], ou "—"}
- Reporté : {actions « Ignorer » + pointeur skill, ou "—"}

## 🔗 Related
- [[{previous retro}]] · [[goals]] · [[open-actions]]
```

Keep it tight and faithful to what {{profile.owner.name}} actually said — the retro is the durable record for the annual review.

### Step 6 — Update goals.md

Apply the Step-8 outcomes to `goals.md`:
- Update each reviewed goal's `revu:` to `today`, refresh its `- progrès:` line, change `statut:` as decided.
- Mark stalled goals (no `revu:` movement causing progress for 2+ weeks) with `⚠️ stallé` inline.
- Move newly `atteint`/`abandonné` goals to `## ✅ Clôturés` with `✅{today}` or status + date, and a `- bilan:` line. **Never delete** a goal — closed goals are annual-review evidence.
- Append new goals under the right horizon section with `➕{today}` and a target `🎯` date.

### Step 7 — Update open-actions.md

Append the Step-9 improvement actions **and** the Top-3 intentions under the `## Actions` heading (never inside the `tasks` query code-blocks), in Obsidian **Tasks** syntax:

```
- [ ] #task @{{profile.owner.name}} — {description} #retro [#tag contextuel] ➕{today} [📅 échéance] [prio]
```

- Always include `#task` (global filter) and `#retro` (so retro actions are filterable). Add `➕{today}`.
- Add `📅` only with a real deadline; add a priority emoji (`⏫`/`🔼`/`🔽`).
- Deduplicate against existing unchecked lines.
- Never check or remove existing items — only {{profile.owner.name}} does that.

### Step 8 — State, index, log

1. `state/last-retro.txt` ← `iso_week`.
2. `state/retro-patterns.json` ← persisted (already updated Step 4).
3. `retros/index.md` — if it keeps a manual list (no Dataview), append a line for this retro.
4. `log.md` (vault root) — append:
   ```
   - [{now}] WEEKLY_RETRO week={iso_week} accomplishments=X actions_new=Y goals_reviewed=Z patterns_escalated=W
   ```
5. Cross-linking of the new retro is handled by Step 9 (vault-wide pass) — do not run `cross-linker` here, to avoid a double pass in the same run.
6. Echo the retro file path and a 3-line summary.

### Step 9 — Weekly vault maintenance (analyse → confirm → apply)

Runs **after** the retro is written and state persisted (Steps 5–8), while {{profile.owner.name}} is still in the session. The design principle resolves a real tension: **a subagent has no channel to the user, yet a report-only tail does half the job** — it surfaces fixes (consolidation, merges, tag drift) that then get deferred forever and never land. We don't want blind auto-apply either; {{profile.owner.name}} wants to *verify*.

The resolution is to **split each gated skill across the subagent boundary**, putting the confirmation where the user actually is:

- **Analyse** runs in a **subagent** (heavy read, off the orchestrator) → returns a **structured plan**, never asks, never writes.
- **Confirm** runs in the **orchestrator** (connected to {{profile.owner.name}}) → one batched `AskUserQuestion`.
- **Apply** runs in a **subagent** with the **approved subset** → decision already made, so nothing to ask.

This is exactly how `wiki-lint --consolidate` and `wiki-dedup` are built natively (dry-run → confirm → act); we just cut at the subagent boundary so the cost stays off-context and the one human gate lands on the orchestrator. Result: we verify **and** the fixes actually apply, in the same session.

Skills with **no gate** (additive, non-destructive) skip the confirm/apply dance entirely — they just run.

---

#### Phase A — Auto-additive (no gate, run silently, in sequence)

Order matters: new pages must exist before cross-linking.

1. **Non-Claude agent histories** — the weekly gap `morning-brief` doesn't cover (it ingests *Claude* daily via Agent B; **codex / pi / copilot / hermes / openclaw drift all week**). Highest-value piece. Spawn:
   ```
   Subagent type: general-purpose · Model: {{profile.tools.model_tiers.synth}}
   Task — invoke `wiki-history-ingest` in append mode for EACH of: codex, pi, copilot, hermes, openclaw.
   (Skip claude — covered daily by morning-brief Agent B.) Each router call self-manages its delta,
   frontmatter, manifest, index.md, hot.md, QMD. Skip silently any agent whose history dir is absent.
   PRIVACY GATE — you cannot ask: on personal/sensitive content default to SKIP/redact, never store-on-question. Skip memory files.
   Return per agent: pages created/updated + sessions, or "no new sessions".
   ```

2. **Cross-linker** (week-delta scope) — weave the week's new pages + this retro into the graph. **Do NOT run vault-wide** — a full-vault pass costs ~130k tokens and ~95% of the signal is in the handful of pages touched this week. Spawn:
   ```
   Subagent type: general-purpose · Model: {{profile.tools.model_tiers.synth}}
   Task — invoke `cross-linker` SCOPED to the pages created/updated during this ISO week
   (the new retro + the week's brief/topic/project pages) PLUS their direct link neighbours.
   Build the candidate set from git/manifest deltas or the briefs' "Recurring topics" sections —
   do not scan the whole vault. Add missing [[wikilinks]], connect orphans among that set
   (additive only). Return: links added, orphans resolved.
   ```

3. **Hot topics hebdo — `synthesis/hot-topics.md`** (weekly, every retro). Regenerate `synthesis/hot-topics.md` in REPLACE mode (never append) from `state/topics-counter.json` + the pages ingested/updated this ISO week. Selection criteria: topics with `hits >= 3` this calendar month **and** present in at least 2 different `sources` entries (squads or channels) **and** with no identified owner in the vault. These are cross-cutting zones of architectural impact. Page format: frontmatter standard (`category: synthesis`, `tags: [synthesis, hot-topics, architecture]`, `review_due: today + 270 days`) + body = table (Topic | Hits ce mois | Sources | Pourquoi c'est un sujet architecte | Action suggérée). If `topics-counter.json` is empty or yields no qualifying topics, write a minimal page stating "Aucun hot topic qualifiant ce mois." — never skip the regeneration.

4. **Monthly-only additive — `wiki-synthesize` + `wiki-digest`.** Gate: **first retro of the calendar month** (no existing `retros/YYYY-Www-retro.md` dated in the current month). If open:
   - `wiki-synthesize` — **Model: {{profile.tools.model_tiers.deep}}**. Additive (synthesis pages for co-occurring concepts), no gate.
   - `wiki-digest month` — {{profile.tools.model_tiers.synth}}. Generates the monthly knowledge digest. If the period looks thin, proceed anyway — do not offer to widen (you cannot ask).
   (The monthly *gated* skills — `wiki-dedup`, `tag-taxonomy` — are not here; they run in Phases B–D.)

5. **Monthly rétro mensuelle + brag compilation.** Gate: **last retro of the calendar month** — detected by: the ISO week of the *next* `{{profile.tools.retro_day}}` (today + 7 days) falls in the next calendar month. If this gate is open, append to the Phase A queue (additive, non-interactive):

   a. **Rétro mensuelle** — write `retros/YYYY-MM-monthly.md`. Source material: all `retros/YYYY-Www-retro.md` files for the current month + `state/retro-patterns.json` + `state/topics-counter.json`. Content: patterns récurrents (thèmes avec `hits >= 3` across the month's retros, blockers returned ≥ 3 times, goals deferred ≥ 2 weeks, investment imbalances detected from collaboration/visibility sections); delta objectifs/réalisé (goals set vs closed this month); 3 proposed adjustments for next month. Frontmatter: `type: retro-monthly`, `tags: [retro, monthly, review]`, no `review_due` (immutable archive, like weekly retros). Do NOT duplicate content from the weekly retros — synthesise, don't copy.

   b. **Brag compilation** — read the current month's entries from `brag/<YYYY>-inputs.md` (the `## <Mois YYYY>` section). Compile them into `brag/<YYYY>.md` using the Julia Evans brag doc format: update the relevant sections (Projets, Collaboration & Mentorat, Conception & Documentation, Contribution organisationnelle, Apprentissages) — this is an UPDATE (AGENTS.md discipline), never append duplicates. Each raw input line maps to the most relevant section. Preserve the annual Objectifs section pointer to `goals.md`.

#### Phase B — Analyse for fixes (subagents, dry-run, return plans, run in PARALLEL)

These are read-only analyses → safe to spawn concurrently. Each must **STOP at the plan and write it to disk — never ask "proceed?", never mutate vault pages.**

⚠️ **The plan must NOT travel through the orchestrator's context.** A subagent returning a long action list as free text gets summarised on the way back ("12 liens cassés") — the per-action detail (exact file, link target, line, merge target) is lost, and the Phase-D apply-subagent would then have to *re-derive* the plan, which can drift (Phase A just created pages → the vault moved). Instead, **persist the full plan to a file with stable per-action IDs**, and pass only IDs + labels through the orchestrator.

Each Phase-B subagent **appends** its actions to a single shared plan file `state/maintenance-plan-{iso_week}.json`:
```json
{
  "week": "2026-W22",
  "generated": "<ts>",
  "actions": [
    {"id": "lint-001", "cat": "lint", "kind": "broken-link", "label": "fix [[Search Redesign]] → [[Search Service Redesign]] in 3 pages",
     "detail": {"pages": ["concepts/search-redesign.md", "..."], "from": "...", "to": "..."}},
    {"id": "dedup-001", "cat": "dedup", "label": "merge [[RSC]] → [[React Server Components]]",
     "detail": {"target": "concepts/react-server-components.md", "sources": ["concepts/rsc.md"]}},
    {"id": "tag-001", "cat": "tags", "label": "rename tag #archi → #architecture (7 pages)", "detail": {"...": "..."}}
  ]
}
```
- **`wiki-lint` dry-run** (weekly, Sonnet) — run the `--consolidate` *analysis* **scoped to the pages created/updated this ISO week plus the targets of any broken links they contain** — NOT the whole vault. A full-vault lint costs ~80k (analysis) + ~120k (apply) and surfaces mass-frontmatter work that gets deferred anyway; scoping to the week's delta cuts that by ~⅔ with no loss of relevant fixes. Stop at the dry-run preview; write each planned action (broken-link fixes, orphan cross-refs, lifecycle corrections, tag-alias normalisations, contradiction callouts) **for the in-scope pages** as a `lint-NNN` entry with full `detail`. Also return the pure-report counts. (Vault-wide structural sweeps — mass frontmatter backfill, full-vault stale detection — belong to the monthly pass or a manual `/wiki-lint`, not the weekly retro.)
- **`wiki-dedup` audit** (monthly only, Sonnet) — write each candidate cluster as a `dedup-NNN` entry with the proposed merge target + source pages in `detail`. *List and STOP, do not merge.*
- **`tag-taxonomy` audit** (monthly only, Sonnet) — write each proposed fix as a `tag-NNN` entry with the affected pages in `detail`. *List and STOP, change nothing.*

Each subagent returns to the orchestrator ONLY: the plan-file path + a compact list of `{id, cat, label}` (no `detail`). The heavy detail stays on disk.

#### Phase C — Confirm (orchestrator, ONE batched AskUserQuestion)

The orchestrator now holds only the lightweight `{id, cat, label}` list — lossless for the decision, cheap for context. If it's empty, skip C and D. Otherwise present a **single** `AskUserQuestion`, grouped by category (lint / dedup / tags) with the count and a few example labels. Per category: **Tout appliquer · Sélectionner · Ignorer** ("Sélectionner" → follow-up listing the individual labels by id; "Ignorer" → deferred, stays in the plan file marked `deferred`). Keep it to one screen — `{{profile.tools.retro_day}}`, not a review board.

The orchestrator's output of this phase is just a **set of approved action IDs** (e.g. `["lint-001","lint-003","dedup-002"]`) — it does not need to know the details.

#### Phase D — Apply the approved subset (subagents, by ID, decision already made)

Spawn an apply subagent **per category** that has approved IDs. Pass it the **plan-file path + the list of approved IDs** — nothing else. It **reads the full `detail` from the file** (no re-derivation → no drift; it applies exactly what was planned and approved).

**Critical** — these skills have their *own* internal confirmation gate (`wiki-lint --consolidate` asks "Apply these N changes?", `wiki-dedup --merge` confirms each pair). The apply-subagent **holds {{profile.owner.name}}'s approval already** — instruct it explicitly: *the human gate passed for exactly these IDs; when the skill reaches its confirmation step, self-confirm "yes" for the approved actions and skip the rest — do NOT wait for user input (no channel → it would stall). You are executing a decision, not re-deciding it.*
- lint → `wiki-lint --consolidate`, applying only the approved `lint-NNN` actions read from the file.
- dedup → `wiki-dedup --merge`, merging only the approved `dedup-NNN` clusters.
- tags → `tag-taxonomy` apply, applying only the approved `tag-NNN` fixes.

After apply, the subagent marks each action `applied` (or `failed: <reason>`) in the plan file and returns counts. Deferred/unapproved IDs stay in the file as a standing worklist.

#### Phase E — Record

Append the maintenance summary to the retro file under `## 🧹 Maintenance hebdo` (template in Step 5), and add to `log.md`:
```
- [{now}] WEEKLY_MAINTENANCE week={iso_week} ingested={agents+counts} links_added=N lint_applied=N/N dedup_merged=N/N tags_fixed=N/N deferred={list} monthly={yes|no}
```
For anything deferred ("Ignorer"), keep an explicit pointer in the retro section — e.g. "3 clusters de doublons reportés → `/wiki-dedup` quand tu veux". The deferred actions remain in `state/maintenance-plan-{iso_week}.json` (marked `deferred`) as a standing worklist — nothing is lost: a later retro or a manual skill run can pick them up by ID.

## Annual review compiler — `/weekly-retro annual [year]`

A second mode that turns the weekly history into a self-assessment draft. This is the payoff of goal #1.

1. Resolve `year` (default current). Read all `retros/{year}-W*.md`.
2. Aggregate:
   - **Accomplishments by impact** — collect all `## 🏆` lines, cluster by theme/project, keep the *So what*. Rank by scope/result.
   - **Goals** — from `goals.md` `## ✅ Clôturés` + the goal-review history across retros: what was set, achieved, abandoned, and why.
   - **Growth** — `## 🧠 Apprentissages` across the year.
   - **Recurring patterns** — `state/retro-patterns.json` + escalated decisions: what structural problems were identified and what was done.
   - **Collaboration / visibility** — recurring `## 🤝` and `## 👀` items (useful "what I contributed beyond my own work").
3. Write `retros/{year}-annual-review-draft.md` structured for a performance review: Réalisations majeures (impact-framed), Objectifs atteints/manqués, Progression & apprentissages, Contributions transverses, Axes d'amélioration. Cite the source retro week for each major point.
4. Offer a light interactive pass to let {{profile.owner.name}} weight/reorder the top achievements before finalising.

## Delegation map

| Concern | Delegated to |
|---------|--------------|
| Recurring theme → structural decision note | `wiki-ingest` (Step 4 escalation) |
| Meeting attendee → who + perimeter | `entities/` lookup (Step 1); new people staged → `wiki-ingest` |
| Non-Claude agent histories (weekly) | `wiki-history-ingest` (Step 9 Phase A — codex/pi/copilot/hermes/openclaw) |
| New retro page + week's pages → woven into graph | `cross-linker` (Step 9 Phase A, **week-delta scope, not vault-wide**) |
| Brag capture (week's accomplishments → raw inputs) | Step 1b (silent, no gate) + Step 3.1 Q&A → `brag/<YYYY>-inputs.md` |
| Inferred-claims validation (mini-session, ≥20 claims) | `wiki-verify` (Step 2b — the skill's only recurring trigger) |
| Hot topics hebdo → architectural impact radar | Step 9 Phase A item 3 (weekly REPLACE) → `synthesis/hot-topics.md` |
| Vault health fixes (analyse → confirm → apply) | `wiki-lint` dry-run **scoped to the week's delta** → batched confirm → `--consolidate` on approved set (Step 9 B–D) |
| Monthly synthesis (additive) | `wiki-synthesize` (Step 9 Phase A, first retro of month) |
| Monthly dedup / tag fixes (analyse → confirm → apply) | `wiki-dedup` · `tag-taxonomy` (Step 9 B–D, first retro of month) |
| Monthly digest | `wiki-digest month` (Step 9 Phase A) |
| Monthly rétro mensuelle | Step 9 Phase A item 5a (last retro of month) → `retros/YYYY-MM-monthly.md` |
| Monthly brag compilation (inputs → Julia Evans doc) | Step 9 Phase A item 5b (last retro of month) → `brag/<YYYY>.md` |
| Tag consistency on any new page | `tag-taxonomy` (inside `wiki-ingest`) |

## Limits & notes

- **Interactive by design** — never run unattended/cron. The `{{profile.tools.retro_day}}` `morning-brief` only *nudges*; it does not run the retro. The Step 9 maintenance tail runs *after* the retro body: its additive work (ingests, cross-links, synthesis) is silent, but destructive fixes go through **one batched confirmation** (Phase C) while {{profile.owner.name}} is still present — analysis and apply happen in subagents, only the gate is interactive. It never applies a destructive change {{profile.owner.name}} didn't approve, and never defers a fix he *did* approve.
- Standard depth ≈ 20 min. If {{profile.owner.name}} asks for "express", do Steps 1–2 + sections 1,2,3,8,10 only, **and run Step 9 Phase A only** (additive ingests + cross-linker) — skip the analyse/confirm/apply phases (B–D); their fixes wait for a full retro or a manual skill run. If "profond", add relances and deep-dive recurring patterns (fin de trimestre).
- Ground everything in evidence from Step 1 — if a claim has no brief/task/permalink behind it, mark it as {{profile.owner.name}}'s recollection, not fact.
- Keep accomplishments **impact-framed** — the annual review needs outcomes, not activity logs.
- Never delete goals or checked actions; closed ≠ deleted (annual-review evidence).
- No Claude footer in the written retro.
- `date` weekday: 1=Mon … 5=Fri … 7=Sun. The retro normally runs on `{{profile.tools.retro_day}}` (its ISO weekday number). Run Mon–Wed with last week un-retro'd → catch-up flow (Step 0.5) targets the previous week; run Thu–Fri in that situation → single two-week retro. Run mid-week with last week already covered → current ISO week to-date, and say so.
- Corrupted state file → reset to `{}`/fallback, never crash.
