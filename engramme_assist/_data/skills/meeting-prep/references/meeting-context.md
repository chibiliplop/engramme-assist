# Socle commun — contexte de réunion

Procédure partagée par `meeting-prep` et `meeting-notes`. Les deux skills exécutent
les étapes 1→5 ci-dessous (récupérer la réunion + tout le contexte mobilisable), puis
divergent : `meeting-prep` enchaîne sur un interview pour remplir les champs de jugement,
`meeting-notes` pré-remplit l'en-tête d'une page de capture. Les étapes 6→7 (slug, chemin,
frontmatter, bookkeeping) valent pour les deux.

Le but du socle : une réunion ne doit jamais être abordée à froid. On rassemble *qui est dans
la pièce*, *ce qui sera discuté*, et *ce que le wiki sait déjà sur le sujet* — pour que la page
produite soit branchée sur la connaissance accumulée, pas une coquille vide.

## 1. Préambule wiki

1. Résous la config (Config Resolution Protocol du `CLAUDE.md`) → `$OBSIDIAN_VAULT_PATH`.
2. Charge le profil mergé (`~/.obsidian-wiki/profile.yml` ← `$VAULT/_meta/profile.yml`) et lis
   `$VAULT/AGENTS.md`. Garde-les en contexte (langue, conventions personnes, discipline d'ingest).
   La langue de travail et des pages produites est `{{profile.owner.lang}}`.

## 2. Choisir la réunion (Outlook)

Source primaire = le calendrier Outlook via le MCP Microsoft 365.

1. `outlook_calendar_search` pour `{{profile.owner.full_name}}` sur une fenêtre allant
   d'aujourd'hui aux prochains jours ouvrés (≈ J→J+3 ; `{{profile.owner.name}}` ne travaille
   pas le week-end). Si l'utilisateur a donné un indice (titre, heure, « la réunion archi »,
   « le point de 14h »), filtre dessus en priorité.
2. Présente les candidats sous forme de liste numérotée — heure (début–fin), titre,
   organisateur — et laisse `{{profile.owner.name}}` choisir le numéro. Un seul candidat
   évident (indice qui matche exactement un créneau) → propose-le directement à confirmer.
3. Si le MCP Outlook est indisponible ou ne renvoie rien qui matche, ne pas échouer : demande
   en une question l'essentiel (titre, date, heure, organisateur) et continue en mode dégradé.

Récupère pour la réunion choisie : titre/sujet, date, heure (début–fin), organisateur,
liste des participants (emails), lien visio / salle, et les pièces jointes éventuelles.

## 3. Résoudre les participants (annuaire `entities/`)

Source de vérité = les fiches personnes du wiki (`entities/`, taguées `person`). Même annuaire
et même format de fiche que `morning-brief`.

Pour chaque participant nommé qui n'est pas `{{profile.owner.name}}` (ignore l'owner, ignore
les listes de diffusion / salles — seulement des humains nommés) :

- **Match** sur `entities/*.md` (pages taguées `person`) par `title`, une entrée `aliases:`,
  l'`email:` (clé la plus fiable — Outlook le donne ; matche aussi la partie locale), ou `slack_id:`.
- **Trouvé** → une ligne : `Prénom Nom — <role>, <team> — périmètre : <perimeter> [[Prénom Nom]]`.
  Lie toujours par le `title` de la page (= nom de fichier), jamais par un slug kebab.
- **Inconnu** → enrichis légèrement (slack_search_users / slack_read_user_profile sur le nom
  ou l'email ; Atlassian si présent) et stage un stub minimal à
  `_raw/morning-brief/people/<slug>.md` (le pipeline d'ingest le promeut plus tard en
  `entities/Prénom Nom.md` — nommé d'après le `title`, pas le slug). Format du stub :

  ```yaml
  ---
  title: Prénom Nom
  category: entities
  aliases: [prenom-nom, prenom.nom]      # slug kebab + partie locale email (filet de résolution)
  email: prenom.nom@company.com          # si connu
  slack_id: U0XXXXXXX                    # si connu
  role: <titre si connu>
  team: <équipe si connue>
  perimeter: <périmètre inféré> (à confirmer)
  tags: [person, visibility/internal]
  summary: <une ligne — qui c'est>
  sources: ["réunion <titre> (<date>)"]
  created: <today>
  updated: <today>
  ---

  # Prénom Nom

  <1 phrase : rôle, équipe, périmètre. Lie [[équipe]] / [[initiative]] si évident.>
  ```

  Lie-le dans la sortie par `[[Prénom Nom]]`, marqué « 🆕 fiche créée ».
- **Externe / non résoluble** → liste le nom brut « (externe ?) », pas de stub.

Proportionne : petite réunion → tous les participants nommés ; grande réunion (>8) →
l'organisateur + les 3–4 plus pertinents, puis « + N autres ».

## 4. Lire les pièces jointes

Si la réunion porte des pièces jointes (agenda, doc, deck) → lis-les via le bon MCP
(Microsoft 365 `read_resource` pour OneDrive/SharePoint ; Confluence `fetch` pour un lien
Confluence HW ; URL directe sinon). Extrais : sujets clés, décisions attendues, questions
ouvertes. Ce qui est lu alimente le `sources:` de la page.

## 5. Cross-référence wiki — OBLIGATOIRE (`wiki-query`)

**Les deux skills doivent récolter du contexte dans le wiki.** Ce n'est pas optionnel : c'est
ce qui distingue une page de réunion branchée sur la connaissance accumulée d'une coquille vide.

1. Construis une requête à partir de : titre de la réunion + mots-clés du sujet + noms des
   participants clés + toute initiative que le sujet évoque manifestement.
2. Invoque la skill `wiki-query` en **mode index/rapide** (« quick answer », sans ouvrir les
   corps de page) avec cette requête.
3. Remonte les pages pertinentes en `[[wikilinks]]` : concepts, initiatives, références,
   fiches personnes des participants. Une réunion « Refonte SERP » doit faire surgir
   `[[SERP]]`, l'initiative liée, les références d'indexation, etc.
4. Note l'initiative principale si le sujet en mappe une (sert au `related:` et au backlink).

## 6. Slug, date, chemin

- `slug` = titre de la réunion en kebab-case, court, sans accents (ex. « Sprint Review B2C —
  itération 24 » → `sprint-review-b2c-iteration-24`).
- `date` = date de la réunion (pas la date du jour si la réunion est demain).
- Chemin : `$VAULT/meetings/<date>-<slug>-prep.md` (meeting-prep) ou `-notes.md` (meeting-notes).
  Crée le dossier `meetings/` s'il n'existe pas.

## 7. Frontmatter & bookkeeping

`meetings/` est une catégorie **time-bound** comme `journal/` / `retros/` : pages d'archive
opérationnelle, **pas de `review_due`** (le gardener ne les archive donc jamais
automatiquement). On fusionne le frontmatter du `_template` (`type`, `date`, `time`, `status`,
`tags`) avec les champs wiki requis (`title`, `category`, `tags`, `sources`, `created`, `updated`) :

```yaml
---
title: <titre réunion>
type: meeting-preparation        # ou meeting-notes — vient du _template
category: meetings
date: <date réunion>
time: "<HH:MM>"
status: draft                    # prep: draft · notes: in-progress
tags: [meeting, preparation, <domaine>]   # notes: [meeting, notes, <domaine>]
attendees: ["[[Prénom Nom]]", "[[…]]"]
related: ["[[Initiative liée]]"]          # depuis l'étape 5 (backlink)
sources: ["Outlook — <sujet> (<date>)", "<pièces jointes lues>"]
created: <today>
updated: <today>
---
```

Remplace les placeholders `{{title}}` / `{{date}}` / `{{time}}` du `_template` par les vraies
valeurs (génération programmatique — on n'utilise pas le moteur Templater d'Obsidian).

Bookkeeping (minimal) :
- Ajoute une ligne à `$VAULT/log.md` : `- [<now>] MEETING <prep|notes> → meetings/<fichier>`.
- Le `related:` assure le backlink Obsidian vers l'initiative.
- Rends à `{{profile.owner.name}}` le chemin du fichier + un lien d'ouverture
  `obsidian://open?vault=<nom-vault>&file=<chemin-relatif-url-encodé-sans-.md>` (best-effort).

**Contrat prep/notes ↔ debrief.** `meeting-prep` et `meeting-notes` restent **write-only** : ils
posent la page dans `meetings/` et n'écrivent rien ailleurs (ni initiative, ni action). L'absorption
post-réunion — actions → `state/open-actions.md`, décisions → initiatives, arbitrage d'archi → ADR
`decisions/` — est le travail de la skill `meeting-debrief`. C'est le pendant : l'un prépare, l'autre valide.
