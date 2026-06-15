---
name: wiki-profile
description: >
  Remplit ou met à jour le profil engramme-assist (identité, sources, prefs outils,
  grille de scoring du brief) et bootstrappe le minimum des configs skill-managed
  (state/channels.yml + excluded_patterns). Interactif, non-destructif. Triggers : appelé par
  wiki-init au setup ; ou directement « update my profile », « change my channels »,
  « mets à jour mon profil », « ajoute un canal Slack ».
---

# wiki-profile

> Dans ce document, `$VAULT` est un raccourci pour `$OBSIDIAN_VAULT_PATH`.

Construit le profil lu par toutes les skills. **Non-destructif** : un profil existant est
complété, jamais écrasé.

## Emplacements (couches)
- Global, identité stable → `~/.obsidian-wiki/profile.yml` (`owner:`)
- Vault, contexte propre → `$OBSIDIAN_VAULT_PATH/_meta/profile.yml` (`sources`, `tools`, `brief`). Le vault écrase le global au merge.
- Valeurs sensibles (canaux, user_id) → toujours dans le profil **vault** (privé).

## Procédure

1. **Résoudre le vault** via le Config Resolution Protocol (`.env` → `~/.obsidian-wiki/config`).
2. **Charger l'existant** : lire `~/.obsidian-wiki/profile.yml` et `$VAULT/_meta/profile.yml`
   s'ils existent. Garder les valeurs présentes ; ne questionner que les champs absents.
3. **Questionner par famille** (une famille à la fois, proposer les valeurs existantes comme défaut) :
   - **Identité** → `owner.name`, `owner.role`, `owner.team`, `owner.lang`.
   - **Sources** → `sources.slack.user_id` ; **canaux Slack importants** (noms ; `id` laissé `null`
     si inconnu) ; **`excluded_patterns`** ; `sources.confluence.spaces` ; `sources.calendar` (oui/non).
   - **Outils** → `tools.model_tiers`, `tools.link_format`, `tools.retro_day`.
   - **Brief (scoring)** → proposer la grille par défaut dérivée de `owner.role` (cf.
     `brief.role_fallback` dans profile.example.yml) ; l'utilisateur peut éditer `scoring_axes`/`thresholds`.
4. **Écrire les fichiers** :
   - `owner:` → `~/.obsidian-wiki/profile.yml`
   - le reste → `$VAULT/_meta/profile.yml`
   - Format : YAML, une ligne descriptive par axe de scoring (ni label nu, ni pavé).
5. **Bootstrap `state/channels.yml`** (vault-relative) : s'il **n'existe pas**, écrire un fichier minimal avec les
   `team_channels` (id: null) + `excluded_patterns` collectés (schéma : voir channels.example.yml).
   S'il **existe déjà**, NE PAS l'écraser — proposer d'ajouter les nouveaux canaux uniquement.
6. **Confirmer** : afficher un récap des fichiers écrits et des champs renseignés.

## Règles
- Au plus une question par famille à la fois ; accepter « passe » pour laisser un champ vide.
- Ne jamais inventer un `user_id` ou un `id` de canal : laisser `null`, la skill consommatrice
  résout via search par nom.
- Idempotent : relancer la skill complète un profil partiel sans rien perdre.
