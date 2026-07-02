---
name: sparring
description: Stress-test a position, decision, ADR or design-doc BEFORE committing to it — the adversarial "challenge" pass the framework otherwise lacks. Frames the position under test, gathers wiki context cheaply, runs the `grilling` interrogation on it, then writes four deliverables — the steelman against, a pre-mortem, the three questions peers will ask (challengers named when known), and the strengthened position. Offers to persist as an ADR in decisions/ or into a meeting-prep page. Triggers on "/sparring", "challenge cette décision", "attaque ma position", "red-team ce design", "pre-mortem", "prépare-moi à défendre", "stress-test avant d'engager". PRE-decision — meeting-prep prepares a meeting's logistics/context, sparring attacks the substance, weekly-retro challenges after the fact.
---

# sparring — attaquer une position avant de s'engager

Passe une position au banc d'essai adverse **avant** que `{{profile.owner.name}}` ne la défende
ou ne la tranche : décision d'archi, ADR en cours, design-doc, parti-pris technique. Le but n'est
pas de valider — c'est de trouver où ça casse pendant qu'il est encore temps de changer d'avis.
Bâti sur `grilling` comme moteur d'interrogatoire, avec un cadrage en amont et des livrables
écrits en sortie.

## Quand l'utiliser

- `/sparring [indice]` — le chemin normal (l'indice pointe la position : « l'ADR analytics »,
  « le choix du seam », un chemin de fichier, une URL).
- Phrases : « challenge cette décision », « attaque ma position », « red-team ce design »,
  « fais-moi le pre-mortem », « prépare-moi à défendre X », « stress-test avant d'engager ».
- **PRE-décision.** À utiliser tant que la position n'est pas figée :
  - `meeting-prep` prépare la logistique et le contexte d'une réunion → *avant, sur la forme*.
  - `sparring` attaque le fond de la position → *avant, sur la substance*.
  - `weekly-retro` challenge ce qui a déjà été fait → *après coup*.

## Procédure

### 1. Identifier la position sous test

Résous la config (Config Resolution Protocol) → `$OBSIDIAN_VAULT_PATH`, charge le profil mergé et
lis `$VAULT/AGENTS.md`. Puis établis *quelle position exactement* est attaquée, dans cet ordre :

1. **Argument explicite** — l'indice de `/sparring` décrit ou pointe la position.
2. **Conversation courante** — une décision vient d'être formulée dans le fil → prends-la.
3. **Chemin / URL** — un ADR de `decisions/`, un design-doc, une page Confluence → lis-le.
4. **`meetings/*-prep.md`** — récupère le champ « Décision attendue » de la prep la plus récente.

Reformule la position en **une phrase falsifiable** (« On fait X plutôt que Y parce que Z ») et
renvoie-la pour accord. Si la cible reste ambiguë après ce balayage, **une seule** question de
clarification, puis avance.

### 2. Récolter le contexte — au moindre coût

Via la skill `wiki-query` en mode index/rapide (ou une passe directe `index.md` / QMD) :

- l'**initiative** liée (`projects/`) et son statut ;
- les **personnes / entités** impliquées (`entities/`) — surtout celles qui possèdent un
  périmètre que la position touche (elles serviront à nommer les contradicteurs, étape 4) ;
- les **décisions passées** proches (`decisions/`) — pour ne pas rejouer un débat déjà tranché.

Reste léger : on cherche de quoi armer l'attaque, pas un dossier complet.

### 3. Interrogatoire — invoquer `grilling`

Invoque la skill `grilling` sur la position, cadrée sur ces quatre axes (une question à la fois,
avec ta réponse recommandée à chaque fois, comme le veut `grilling`) :

- **Hypothèses** — qu'est-ce qui est tenu pour acquis et qui pourrait être faux ?
- **Alternatives** — quelle option a été écartée trop vite, et à quel prix ?
- **Modes d'échec** — par où ça casse en prod, à l'échelle, ou dans six mois ?
- **Dépendances** — qui / quoi doit tenir pour que ça marche (équipes, contrats, délais) ?

Explore le wiki ou le code plutôt que de demander quand la réponse s'y trouve.

### 4. Livrables — écrits, après l'interrogatoire

Une fois l'interview close, produis les quatre, concis et sans remplissage :

1. **Contre-arguments** — le *steelman* le plus fort **contre** la position : la meilleure
   version de l'argument adverse, pas un épouvantail.
2. **Pre-mortem** — « on est dans six mois, c'est un échec : qu'est-ce qui s'est passé ? » —
   2 à 4 scénarios de rupture plausibles, du plus probable au plus coûteux.
3. **Les 3 questions que les pairs poseront** — les objections que la position rencontrera en
   revue. Nomme le contradicteur probable quand il est connu (participants de la prep, ou
   propriétaire du périmètre dans `entities/`) : « [[X]] demandera… ».
4. **La position renforcée** — réécrite : mêmes conclusions si elles tiennent, amendées ou
   abandonnées sinon. C'est le vrai produit de l'exercice.

### 5. Persister — proposer, ne pas forcer

Propose (sans l'imposer) d'acter le résultat :

- **ADR dans `decisions/`** — si la position est une décision d'archi. Lis `decisions/index.md`
  pour le format (MADR simplifié : **Statut** `proposed`, **Date**, **Décideurs**, **Équipes
  impactées**, puis `## Contexte`, `## Décision`, `## Alternatives considérées`, `## Conséquences`)
  et le prochain numéro libre (`ADR-00N`). `review_due` = +180 j, comme les ADR existants. Ajoute
  la ligne dans la table d'index. La position renforcée devient la Décision ; contre-arguments et
  pre-mortem nourrissent Alternatives et Conséquences — rédigés positivement (état des lieux, pas
  trace de réfutation), conformément à `AGENTS.md`.
- **Mise à jour d'une prep** — si la position vient d'une `meetings/*-prep.md`, verse les
  contre-arguments et les 3 questions dans ses sections *Options à discuter* / *Questions à poser*.
- Sinon → ne rien écrire ; la position renforcée reste dans le fil.

Dans tous les cas, une ligne dans `log.md` : `- [<now>] SPARRING <position courte> → <ADR-00N | prep | fil>`.
