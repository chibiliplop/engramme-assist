---
name: wiki-profile
description: >
  Remplit ou met à jour le profil engramme-assist (identité, sources, prefs outils,
  grille de scoring du brief), vérifie les MCP requis par les skills et résout les IDs
  (canaux Slack, espaces Confluence). Interactif et exhaustif, non-destructif. Triggers :
  appelé par wiki-init au setup ; ou « update my profile », « change my channels »,
  « mets à jour mon profil », « ajoute un canal Slack ».
---

# wiki-profile

> Dans ce document, `$VAULT` est un raccourci pour `$OBSIDIAN_VAULT_PATH`.

Construit le profil lu par toutes les skills, **vérifie les MCP** dont elles dépendent et
**résout les IDs concrets**. **Non-destructif** : un profil existant est complété, jamais écrasé.

## Invariant — interactif, jamais passe-plat

Cette skill **dialogue** avec l'utilisateur, une famille à la fois, et **attend sa réponse**
avant de continuer. Proposer les valeurs existantes comme défaut est permis, mais :
- ne **jamais** auto-accepter un défaut en silence ni « rubber-stamp » l'ensemble ;
- ne **jamais** fabriquer une réponse à la place de l'utilisateur ;
- ne **jamais** se réduire à un passe-plat (écrire le profil sans avoir posé les questions).
Si appelée par `wiki-init`, le mode interactif reste obligatoire.

## Emplacements (couches)
- Global, identité stable → `~/.obsidian-wiki/profile.yml` (`owner:`)
- Vault, contexte propre → `$VAULT/_meta/profile.yml` (`sources`, `tools`, `brief`). Le vault écrase le global au merge.
- Valeurs sensibles (canaux, user_id) → toujours dans le profil **vault** (privé).

## Carte des MCP requis (source de vérité)

Chaque source du profil dépend d'un serveur MCP. Avant de collecter une source activée, **vérifier**
sa dispo par un appel léger ; voir « préflight » plus bas.

| Source profil        | Serveur MCP   | Skills consommatrices       | Vérif (appel léger)        |
|----------------------|---------------|-----------------------------|----------------------------|
| `sources.slack`      | Slack         | morning-brief, weekly-retro | `slack_search_users`       |
| `sources.confluence` | Atlassian     | morning-brief, weekly-retro | `getConfluenceSpaces`      |
| `sources.calendar`   | Microsoft 365 | morning-brief               | `outlook_calendar_search`  |

## Procédure

1. **Résoudre le vault** via le Config Resolution Protocol (`.env` → `~/.obsidian-wiki/config`).
2. **Charger l'existant** : lire `~/.obsidian-wiki/profile.yml` et `$VAULT/_meta/profile.yml`
   s'ils existent. S'en servir comme **défauts proposés** — mais toujours confirmer (cf. invariant).
3. **Q&A par famille** (une à la fois, attendre la réponse) :
   - **Identité** → `owner.name` (**requis**), `owner.full_name`, `owner.role` (**requis**),
     `owner.team`, `owner.lang`. `full_name`/`team`/`lang` peuvent être **explicitement déclinés**
     (« je passe ») — jamais sautés en silence.
   - **Outils** → `tools.model_tiers` (proposer le défaut `{triage: haiku, synth: sonnet, deep: opus}`),
     `tools.link_format`, `tools.retro_day`.
   - **Brief (scoring)** → proposer la grille dérivée de `owner.role` (cf. `brief.role_fallback`
     dans profile.example.yml) ; l'utilisateur confirme ou édite `scoring_axes` / `thresholds`.
   - **Sources** — pour CHAQUE source (Slack, Confluence, Calendar), demander d'abord
     **« Tu utilises X ? »** (opt-in). Si **non** → ne pas écrire la source, passer à la suivante.
     Si **oui** :
     1. **Préflight MCP** (hybride) : vérifier le serveur via l'appel de la carte ci-dessus.
        - **Dispo** → continuer.
        - **Absent** → proposer à l'utilisateur : *(a)* le brancher maintenant (donner la marche
          à suivre, attendre, re-tester) **ou** *(b)* **différer** cette source — la noter
          `pending` (config collectée mais IDs laissés `null`).
     2. **Collecte** :
        - **Slack** → `sources.slack.user_id` ; la **liste des canaux à suivre** ;
          `excluded_patterns` — présenter **comme des patterns de noms de canaux Slack**
          (ex. `*-bots`, `random`, `*-alerts`), **jamais** des globs de fichiers.
        - **Confluence** → la **liste des espaces** (`sources.confluence.spaces`).
        - **Calendar** → accès seulement (`sources.calendar: true`).
     3. **Résolution immédiate** (si MCP dispo) :
        - Slack : pour chaque canal saisi, `slack_search_channels` → écrire l'`id` réel.
          Si introuvable, laisser `null` et le signaler.
        - Confluence : `getConfluenceSpaces` → valider que chaque clé d'espace existe ;
          signaler les inconnues.
        - Calendar : `outlook_calendar_search` (fenêtre courte) → confirmer que la lecture marche.
4. **Écrire les fichiers** :
   - `owner:` → `~/.obsidian-wiki/profile.yml`
   - `sources` / `tools` / `brief` → `$VAULT/_meta/profile.yml`
   - Format : YAML, une ligne descriptive par axe de scoring (ni label nu, ni pavé).
5. **Bootstrap `state/channels.yml`** (vault-relative) : s'il **n'existe pas**, l'écrire avec les
   `team_channels` (avec les `id` résolus, sinon `null`) + `excluded_patterns` (schéma :
   voir channels.example.yml). S'il **existe**, NE PAS l'écraser — proposer d'ajouter les
   nouveaux canaux uniquement.
6. **Confirmer** : récap des fichiers écrits, des champs renseignés, et par source : ✅ résolue /
   ⏳ `pending` (MCP différé).

## Règles
- Interactif obligatoire (cf. invariant) ; au plus une famille à la fois.
- Ne jamais **inventer** un `user_id` ou un `id` de canal. En revanche, **résoudre** activement
  via `slack_search_channels` / `getConfluenceSpaces` quand le MCP est dispo.
- Idempotent : relancer complète un profil partiel sans rien perdre, et tente de résoudre les
  IDs encore `null`.
