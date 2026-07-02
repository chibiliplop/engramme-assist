---
name: meeting-debrief
description: Ferme la boucle d'une réunion passée en absorbant ses notes dans le wiki. Localise la page de réunion (meetings/*-notes.md ou *-prep.md), lit les décisions et actions consignées (ou les récolte en 2 questions si les blocs sont vides), puis route : les actions vers state/open-actions.md en syntaxe Tasks, les décisions vers la ou les initiatives liées (UPDATE), et propose un ADR quand une décision est un arbitrage d'architecture. Annote la page de réunion d'une ligne « Absorbé → ». Déclenche sur "/meeting-debrief", "débriefe la réunion", "la réunion est terminée", "absorbe mes notes de réunion", "qu'est-ce qu'on a décidé". À utiliser après une réunion préparée par meeting-prep ou notée par meeting-notes — c'est le pendant qui valide et absorbe (« l'un prépare, l'autre valide »). Pas pour noter pendant (c'est meeting-notes), pas pour préparer (c'est meeting-prep).
---

# meeting-debrief — absorber une réunion terminée dans le wiki

`meeting-prep` et `meeting-notes` sont **write-only** : ils produisent une page dans `meetings/`,
mais rien n'absorbe ensuite ce qui s'y est décidé. Cette skill est le pendant : après la réunion,
elle lit les **décisions** et **actions** consignées et les fait vivre dans le wiki — actions vers
`state/open-actions.md`, décisions vers les initiatives liées, arbitrage d'archi → ADR proposé.
Le principe : **l'un prépare, l'autre valide.**

## Quand l'utiliser

- `/meeting-debrief [indice]` — après une réunion (l'indice filtre la page : « archi », « MCP »…).
- Phrases : « débriefe la réunion », « la réunion est terminée », « absorbe mes notes de réunion »,
  « qu'est-ce qu'on a décidé ».
- **PAS** pour noter pendant la réunion → `meeting-notes`. **PAS** pour préparer → `meeting-prep`.

## Procédure

### 1. Préambule & localiser la page de réunion

1. Résous la config (`CLAUDE.md`) → `$OBSIDIAN_VAULT_PATH` ; charge le profil mergé et lis
   `$VAULT/AGENTS.md` (langue, discipline d'ingest, conventions personnes). Langue de travail =
   `{{profile.owner.lang}}`.
2. Liste `$VAULT/meetings/*-notes.md` et `*-prep.md`, la plus récente d'abord (date du nom de
   fichier, puis mtime). Si un indice est donné, filtre dessus. Propose la meilleure candidate à
   confirmer — **une seule question au maximum** ; si un indice matche exactement une page, pars
   dessus directement.
3. Lis la page : son frontmatter (surtout `related:` → les initiatives liées ; `attendees`,
   `date`, `title`) et son corps.

### 2. Lire les décisions et actions consignées

- **Page `-notes.md`** : lis les tables **« Décisions prises »** et **« Actions »**, plus
  **« Ce qui a été décidé »** et **« Prochaine étape »** du résumé final.
- **Page `-prep.md`** : pas de blocs de capture ; regarde si l'owner a annoté « Décision attendue »
  / « Résultat attendu » avec l'issue réelle.
- **Si décisions ET actions sont vides** → capture interactive minimale, **2 questions au
  maximum** : (a) « Qu'est-ce qui a été décidé ? » (b) « Quelles actions, qui, pour quand ? ».
  Ne devine rien ; s'il n'y a ni décision ni action, dis-le et arrête-toi là.

### 3. Router les actions → `state/open-actions.md`

Pour chaque action, ajoute une ligne en **syntaxe Tasks** (le format exact du fichier), sous
`## Actions`, **jamais** dans un bloc ```` ```tasks ````, regroupées sous un marqueur
`<!-- meeting-debrief YYYY-MM-DD <slug> -->` :

```
- [ ] #task @personne — description #tag ➕ <today> [📅 échéance] [prio] (source: réunion <titre> (<date>))
```

- Toujours `#task` et `➕ <today>` (date du débrief). `@personne` = le responsable résolu (Thomas → `@Thomas`).
- `📅 YYYY-MM-DD` seulement pour une vraie échéance (« semaine prochaine » → le lundi suivant).
- Priorité : `⏫`/`🔺` urgent ou piloté par une échéance · `🔼` défaut · `🔽` optionnel.
- Tag d'intention : `#relance` · `#decision` · `#attente` · `#urgent`.
- **Dédup** : si une action non cochée existe déjà pour le même `@personne` + même action, ne la
  duplique pas (NOOP). Ne coche ni ne supprime jamais une ligne existante.

### 4. Router les décisions → initiative(s) liée(s)

Pour chaque décision, absorbe le fait dans **la page d'initiative** correspondante (depuis
`related:` de la réunion ; sinon `wiki-query` pour la retrouver). Discipline `AGENTS.md` :

- **UPDATE par défaut** : la décision rejoint la bonne section du corps (état, arbitrage, `next`).
  Reformule en fait déclaratif — pas de trace du « qui/comment », pas de « non X ».
- Bump `updated: <today>` et recompute `review_due = <today> + 14 j` (initiatives).
- Si la décision fait bouger `next:` ou `status:`, mets-les à jour.
- Aucune page trouvée pour une décision structurante → signale-le (ne crée pas de dossier ici).

### 5. Arbitrage d'archi → proposer un ADR (ne pas forcer)

Si une décision est un **arbitrage d'architecture** (choix de conception transverse, dette assumée,
contrainte structurante), **propose** — sans l'imposer — de la consigner en ADR dans `decisions/`.
Si l'owner accepte : crée `decisions/ADR-NNN-titre-court.md` (numéro suivant) au format MADR et au
frontmatter des ADR existants (voir `decisions/index.md`) — Statut `accepted` si la réunion a
tranché, sinon `proposed` ; sections Contexte / Décision / Conséquences — puis ajoute la ligne dans
la table de `decisions/index.md`. Sinon, la décision reste sur l'initiative seulement.

### 6. Annoter, log, restitution

1. Sur la page de réunion, ajoute en fin une ligne minimale et bump son `updated` :
   `> **Absorbé le <today>** → [[Open Actions]] · [[Initiative liée]]` (+ `[[ADR-NNN]]` si créé).
   Passe son `status:` à `done` (la boucle est fermée).
2. Une ligne `log.md` :
   `- [<now>] MEETING_DEBRIEF page=meetings/<fichier> actions_added=X decisions_absorbed=Y adr_created=0|1`
3. Restitue en 3–4 lignes : ce qui a été décidé, les actions poussées (qui / échéance), les
   initiatives mises à jour, et l'ADR proposé/créé le cas échéant.
