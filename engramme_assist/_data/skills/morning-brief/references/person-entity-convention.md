# Person-entity convention (the people directory)

The format for wiki person pages and the staged stubs that become them. The calendar stage
resolves meeting attendees against these pages and stages a stub here for anyone new; a
wiki-ingest step later turns each stub into its `entities/` page.

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

`perimeter` is the field that answers "what scope/domain do they own" — keep it a short,
scannable phrase, not a paragraph. When a meeting or Slack thread reveals a person's perimeter
shifted (new team, new ownership), update their page (delegate to `wiki-ingest`) rather
than creating a duplicate.
