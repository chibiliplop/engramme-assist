---
name: meeting-prep
description: Prépare une réunion où le propriétaire du wiki a un rôle actif (il présente, cadre, ou doit faire trancher une décision) en remplissant le template meeting-preparation. Récupère la réunion depuis Outlook, résout les participants depuis l'annuaire entities/, lit les pièces jointes, ET récolte le contexte du wiki via wiki-query, puis mène un interview ciblé pour remplir les champs de jugement (objectif, décision attendue, problème, options, critères, questions). Écrit la page dans meetings/. Déclenche sur "/meeting-prep", "prépare ma réunion", "prépare-moi le point/la réunion de…", "je participe à une réunion", "je présente en réunion", "prépare ma prise de parole", "j'anime une réunion". À utiliser dès que Thomas a un rôle actif dans une réunion à venir et veut arriver préparé — pas pour prendre des notes pendant (c'est meeting-notes), pas pour le balayage léger du brief quotidien (c'est morning-brief).
---

# meeting-prep — préparer une réunion où tu as un rôle actif

Remplit le template `_templates/meeting-preparation.md` pour une réunion à venir où
`{{profile.owner.name}}` **participe activement** : il présente, cadre le sujet, ou doit
obtenir une décision. Le but est d'arriver préparé — objectif clair, options déjà pesées,
questions prêtes — pas de partir d'une page blanche.

## Quand l'utiliser

- `/meeting-prep [indice]` — le chemin normal (l'indice filtre la réunion : « archi », « 14h »…).
- Phrases : « prépare ma réunion », « prépare-moi le point de demain », « je participe à… »,
  « je présente en réunion », « j'anime le comité ».
- **PAS** pour prendre des notes pendant une réunion où tu assistes → `meeting-notes`.
- **PAS** pour le balayage léger des réunions du jour dans le brief → `morning-brief` le fait déjà.

## Procédure

### 1. Socle commun — récupérer la réunion + tout le contexte

Lis et exécute `references/meeting-context.md`, **étapes 1 à 5** : préambule wiki, choix de la
réunion dans Outlook, résolution des participants, lecture des pièces jointes, et la
cross-référence wiki obligatoire via `wiki-query`. Tu arrives à cette étape avec : la réunion
choisie, les participants résolus (qui ils sont + leur périmètre), les pièces jointes lues, et
les pages wiki pertinentes.

### 2. Interview ciblé — seulement les champs de jugement

Le template `meeting-preparation` a beaucoup de sections, mais une grande partie se déduit du
contexte que tu viens de rassembler. Le principe : **pré-remplis tout ce que le contexte
permet, et n'interroge `{{profile.owner.name}}` que sur ce que lui seul détient** — son intention
et ses arbitrages. Une page pré-remplie qu'il corrige vaut mille fois mieux qu'un interrogatoire.

Déduis du contexte (propose, il édite) :
- **Contexte** — depuis les pièces jointes + pages wiki.
- **Problème à résoudre** — formule une hypothèse depuis le sujet et le contexte wiki.
- **Options à discuter** — si le sujet en suggère (depuis le wiki, les pièces jointes, les
  initiatives liées), propose 1–2 options pré-rédigées avec avantages/risques pressentis.
- **Questions à poser** — propose des questions tirées du contexte et de qui sera dans la pièce
  (ex. « X possède l'indexation → prépare la question latence pour lui »).

Demande à `{{profile.owner.name}}` (groupe les questions, ne les égrène pas une par une) :
- **Objectif** de la réunion + **décision attendue** à la fin (le cœur — une réunion sans
  décision attendue n'a souvent pas lieu d'être ; challenge gentiment si flou).
- **Type de réunion** — une `AskUserQuestion` multi-select sur les cases du template
  (Information / Cadrage / Décision / Résolution de problème / Suivi / Rétrospective).
- **Périmètre** in/out s'il n'est pas évident.
- **Critères de décision** — `AskUserQuestion` multi-select sur la liste du template
  (Simplicité, Délai, Coût de maintenance, Réversibilité, Robustesse, Sécurité, Scalabilité,
  Autonomie des équipes, Observabilité, Cohérence architecture).
- Validation / correction des options et questions pré-rédigées.

Si la **décision attendue** est une position que `{{profile.owner.name}}` doit défendre ou faire
accepter, propose-lui (optionnel) d'en éprouver le fond avant la réunion avec la skill `sparring`
— anticiper les objections vaut mieux que les découvrir dans la pièce.

Garde ça proportionné : un point de synchro léger ne mérite pas le même interrogatoire qu'un
comité d'archi qui doit trancher. Si une section du template n'a pas de matière, laisse-la
avec ses puces vides plutôt que d'inventer.

### 3. Remplir le template et écrire la page

1. Lis `$VAULT/_templates/meeting-preparation.md`.
2. Substitue `{{title}}` / `{{date}}` / `{{time}}` par les vraies valeurs, et remplis chaque
   section avec les déductions (étape 2) + les réponses de l'interview. Coche les cases retenues
   (`- [x]`). Renseigne la table Participants avec les personnes résolues (rôle attendu + pourquoi
   nécessaire). Adapte l'agenda proposé au temps réel de la réunion si tu le connais.
3. Compose le frontmatter fusionné selon `references/meeting-context.md` §7 (`type:
   meeting-preparation`, `status: draft`, `tags: [meeting, preparation, <domaine>]`, `attendees`,
   `related`, `sources`, **pas de `review_due`**).
4. Écris dans `$VAULT/meetings/<date>-<slug>-prep.md`. Termine la page par une ligne de relais :
   `> Après la réunion : lance `/meeting-debrief` pour absorber décisions & actions (open-actions, initiatives, ADR).`

### 4. Bookkeeping & restitution

- Ajoute la ligne `log.md` (§7) : `- [<now>] MEETING prep → meetings/<fichier>`.
- Si de nouvelles fiches personnes ont été staggées (socle §3), signale-le.
- Rends le chemin du fichier + le lien `obsidian://` d'ouverture.
- Restitue en 3–4 lignes : objectif, décision attendue, qui sera dans la pièce (1 ligne),
  et les pages wiki à relire avant — pour que `{{profile.owner.name}}` ait l'essentiel sans
  rouvrir le fichier. Rappelle qu'**après la réunion**, `/meeting-debrief` ferme la boucle.
