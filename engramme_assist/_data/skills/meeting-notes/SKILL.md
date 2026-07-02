---
name: meeting-notes
description: Prépare une page de prise de notes pour une réunion où le propriétaire du wiki assiste (il écoute et capte, sans rôle de présentateur) en remplissant le template meeting-notes. Récupère la réunion depuis Outlook, pré-remplit automatiquement l'en-tête (informations, participants résolus depuis entities/, objectif annoncé, agenda) à partir de l'invite et des pièces jointes, ET récolte le contexte du wiki via wiki-query pour un bloc de relecture rapide, puis laisse les zones de notes vides et prêtes. Écrit la page dans meetings/. Déclenche sur "/meeting-notes", "note de réunion", "prépare ma prise de notes", "je vais assister à une réunion", "compte rendu de réunion", "prépare le CR". À utiliser dès que Thomas va assister à une réunion et veut une page de capture prête — pas pour préparer une réunion qu'il anime (c'est meeting-prep), pas pour le balayage du brief quotidien (c'est morning-brief).
---

# meeting-notes — page de prise de notes pour une réunion où tu assistes

Remplit le template `_templates/meeting-notes.md` pour une réunion où `{{profile.owner.name}}`
**assiste** : il suit et capte, sans rôle de présentateur. La skill fait tout le pré-remplissage
mécanique (en-tête, participants, agenda, contexte wiki) pour qu'il entre informé et n'ait plus
qu'à noter au fil de l'eau.

## Quand l'utiliser

- `/meeting-notes [indice]` — le chemin normal (l'indice filtre la réunion).
- Phrases : « note de réunion », « prépare ma prise de notes », « je vais assister à… »,
  « compte rendu de réunion », « prépare le CR ».
- **PAS** pour préparer une réunion que tu animes / où tu présentes → `meeting-prep`.
- **PAS** pour le balayage des réunions du jour dans le brief → `morning-brief`.

## Procédure

### 1. Socle commun — récupérer la réunion + tout le contexte

Lis et exécute le socle `meeting-context.md`, **étapes 1 à 5** : préambule wiki, choix de la
réunion dans Outlook, résolution des participants, lecture des pièces jointes, cross-référence
wiki obligatoire via `wiki-query`. Le socle vit dans le skill `meeting-prep` — résous son chemin
dans cet ordre : (1) relatif au skill courant, `../meeting-prep/references/meeting-context.md` ;
(2) si ça ne résout pas, `$OBSIDIAN_VAULT_PATH/.claude/skills/meeting-prep/references/meeting-context.md`.

À l'inverse de `meeting-prep`, il n'y a **pas d'interview** : une page de notes est une page de
capture, pas un document de décision. Tout ce qui peut être pré-rempli l'est automatiquement.

### 2. Pré-remplir l'en-tête (automatique)

1. Lis `$VAULT/_templates/meeting-notes.md`.
2. Remplis la table **Informations** : Date, Heure, Organisateur, Sujet, Type (déduis du titre /
   de l'invite : Information / Cadrage / Décision / Suivi), Lien visio / salle.
3. **Participants** : une ligne par personne résolue (étape socle 3) — `Prénom Nom — <role>,
   <team> — périmètre [[Prénom Nom]]`, 🆕 si la fiche vient d'être créée.
4. **Objectif annoncé** : depuis le corps de l'invite ou les pièces jointes (verbatim si possible).
5. **Agenda prévu** : depuis l'invite / les pièces jointes ; sinon laisse vide.
6. **Bloc « Contexte wiki » en tête** : juste sous le titre, ajoute une courte section avec les
   pages remontées par `wiki-query` (`[[wikilinks]]`) — ce que `{{profile.owner.name}}` doit avoir
   en tête en entrant. C'est le point que les deux skills partagent : la page est branchée sur la
   connaissance accumulée.

### 3. Laisser les zones de capture vides et prêtes

Ne remplis pas, ne devine pas : Notes principales, Points clés / questions (Cornell), Décisions
prises, Actions, Points ouverts, Risques / alertes, Désaccords, Résumé final. Ces zones se
remplissent pendant et juste après la réunion. Garde la structure du template intacte.

### 4. Écrire la page, bookkeeping & restitution

1. Frontmatter fusionné selon `references/meeting-context.md` §7, variante notes : `type:
   meeting-notes`, `status: in-progress`, `tags: [meeting, notes, <domaine>]`, `attendees`,
   `related`, `sources`, **pas de `review_due`**.
2. Écris dans `$VAULT/meetings/<date>-<slug>-notes.md`. Termine la page par une ligne de relais :
   `> Après la réunion : lance `/meeting-debrief` pour absorber décisions & actions (open-actions, initiatives, ADR).`
3. Ligne `log.md` : `- [<now>] MEETING notes → meetings/<fichier>`.
4. Si des fiches personnes ont été staggées, signale-le.
5. Rends le chemin + le lien `obsidian://` d'ouverture, et 2–3 lignes : qui sera dans la pièce
   et les pages wiki à survoler avant — pour entrer informé. Rappelle qu'**après la réunion**,
   `/meeting-debrief` absorbe les notes (décisions → initiatives, actions → open-actions).
