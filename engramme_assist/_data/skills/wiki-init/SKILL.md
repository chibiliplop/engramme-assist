---
name: wiki-init
description: >
  Point d'entrée unique de l'initialisation d'un vault engramme-assist. Garantit l'ordre :
  d'abord la structure du vault (skill wiki-setup d'Ar9av), puis le profil (skill wiki-profile).
  Triggers : « set up my wiki », « initialize », « initialise mon wiki », « configure le vault ».
---

# wiki-init — orchestrateur d'initialisation

L'ordre structure → profil ne doit pas dépendre du routage inter-skill. Cette skill l'impose
en invoquant les deux étapes dans l'ordre, depuis un seul SKILL.md.

## Procédure (séquentielle, ne pas réordonner)

1. **Structure du vault** — invoquer la skill `wiki-setup` (Ar9av) : crée l'arborescence
   (`concepts/`, `entities/`, …), les fichiers spéciaux (`index.md`, `hot.md`, `.manifest.json`),
   et écrit `~/.obsidian-wiki/config`. Attendre sa fin.
2. **Profil** — invoquer la skill `wiki-profile` : remplit `~/.obsidian-wiki/profile.yml` +
   `$VAULT/_meta/profile.yml` et bootstrappe `state/channels.yml`. Attendre sa fin.
3. **Récap** — afficher : vault initialisé (chemin), profil écrit (champs clés), nombre de team_channels écrits dans state/channels.yml.

## Règles
- Si la structure existe déjà (vault non vide, `index.md` présent), passer l'étape 1 et le signaler.
- Si le profil existe déjà, l'étape 2 (wiki-profile) le complète sans écraser.
- Ne jamais exécuter l'étape 2 avant l'étape 1.
