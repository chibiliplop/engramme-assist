---
name: jot
description: Frictionless personal capture for the wiki owner — one line in, correctly routed out. Takes a free-text thought and routes it to the right home — personal objective (goals.md, exact conventions), task (state/open-actions.md, Obsidian Tasks syntax), fact about a known page (direct UPDATE per AGENTS.md discipline), or personal note (_raw/notes/, promoted by the normal ingest pipeline). Triggers on "/jot <texte>", "note rapide", "ajoute un objectif", "nouvelle note", "retiens que", "capture ça pour moi". Zero ceremony — at most ONE clarifying question, ever.
---

# jot — capture personnelle sans friction

One line in → routed to the right home → one-line confirmation out. This is the *push* channel of the wiki: everything else (Slack, Confluence, sessions) is pulled by pipelines; `jot` is how {{profile.owner.name}}'s own thoughts, objectives and notes get in, in under five seconds.

## When to use

- `/jot <texte libre>` — the normal path.
- `/jot` with no text → ask "Qu'est-ce que je note ?" and wait.
- Natural phrases: "note rapide :", "ajoute un objectif :", "retiens que…", "capture ça".
- NOT for capturing the current conversation (that's `wiki-capture`) and NOT for ingesting documents (that's `wiki-ingest`).

## Routing

Resolve config (Config Resolution Protocol) → `$OBSIDIAN_VAULT_PATH`. Read `$VAULT/AGENTS.md` conventions. Then classify the text into exactly one route:

**Explicit prefixes always win** (case-insensitive, strip the prefix from the content):
- `objectif:` / `goal:` → **Objectif**
- `task:` / `tâche:` / `todo:` → **Tâche**
- `note:` / `idée:` → **Note**
- `fait:` / `fact:` → **Fait**

**No prefix → heuristics** (in this order):
1. **Objectif** — expresses a desired *outcome* for {{profile.owner.name}} with an implicit horizon ("je veux…", "d'ici fin Q3…", "devenir/livrer/atteindre…"). An objective is a destination, not a single action.
2. **Tâche** — a single concrete action with {{profile.owner.name}} as owner ("appeler X", "relire la MR", "préparer le point lundi"). A task is doable in one sitting.
3. **Fait** — a factual statement about something the wiki already knows (a person, project, tool — check `index.md` titles/aliases cheaply). E.g. "X est passé EM de la squad Y".
4. **Note** (default) — everything else: idea, observation, raw thought, link to explore.

If genuinely torn between two routes, ask ONE `AskUserQuestion` with the two candidates — never more, and never for a prefixed input.

## Routes

### Objectif → `goals.md`

Follow the conventions in the file's header exactly. Determine the horizon from the text (deadline this week/quinzaine → `court`; trimestre → `moyen`; année+ → `long`); if no temporal signal at all, ask the ONE question (court/moyen/long). Append under the right section:

```
- 🎯 **<Titre court>** — <description une phrase> · statut:en-cours · horizon:<h> · ➕<today> [· 🎯<échéance si donnée>]
  - progrès: créé via /jot, pas encore démarré.
```

Add `Cf [[page]]` links when the objective clearly relates to existing wiki pages (check index titles). Never touch existing goals; never add `revu:` (the retro owns it).

### Tâche → `state/open-actions.md`

Append under `## Actions` (never inside the `tasks` query code-blocks), Obsidian Tasks syntax per the file's existing convention:

```
- [ ] #task @{{profile.owner.name}} — <description> #perso ➕<today> [📅 <due si donnée>] [priorité si évidente]
```

Deduplicate against existing unchecked lines. The task then shows up in the next morning-brief's « Actions en cours » automatically.

### Fait → UPDATE direct de la page

Per AGENTS.md ingest discipline (UPDATE par défaut) : find the page (index titles/aliases, QMD if needed), absorb the fact into the body/frontmatter, bump `updated`, recompute `review_due` (category offsets in AGENTS.md). The fact comes from {{profile.owner.name}} himself → no `^[inferred]` marker, and `last_verified: <today>`. If NO page covers the subject → fall back to **Note** (don't create a page from one line; the ingest pipeline decides page-worthiness).

### Note → `_raw/notes/YYYY-MM-DD-<slug>.md`

```markdown
---
title: <titre court dérivé du contenu>
created: <today>
source: jot
---

<texte verbatim de {{profile.owner.name}} — ne pas réécrire, ne pas embellir>
```

`_raw/notes/` rides the existing pipeline: the next `morning-brief`/`wiki-ingest` pass promotes it if it's page-worthy (counter/threshold rules apply), and the gardener TTLs it after promotion. A note is never lost: unpromoted notes are flagged at 14 days, archived after, both visibly.

## Confirmation & bookkeeping

- Echo ONE line: `→ objectif ajouté (moyen terme)` / `→ tâche ajoutée à open-actions` / `→ [[Page]] mise à jour` / `→ note déposée dans _raw/notes/`.
- Append to `log.md`: `- [<now>] JOT route=<objectif|tache|fait|note> target=<fichier>` — nothing else (no index, no hot.md for a one-liner).
- QMD: skip (the daily run reindexes).
- Batch input (several lines / bullets in one `/jot`) → route each line independently, one confirmation line each.

## Inbox (capture asynchrone depuis Obsidian)

`_raw/inbox.md` is the same channel for moments without Claude (mobile, réunion) : {{profile.owner.name}} appends free lines there from Obsidian. `morning-brief` (Step 1b) routes every line through the rules above at the start of each run, then resets the file to its header. `/jot` peut aussi être invoqué avec `--inbox` pour traiter ce fichier à la demande : route chaque ligne, confirme par ligne, réinitialise le fichier.
