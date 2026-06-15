---
name: wiki-init
description: >
  Point d'entrée unique de l'initialisation d'un vault engramme-assist. Garantit l'ordre :
  structure (skill wiki-setup d'Ar9av) → profil INTERACTIF & vérifié (wiki-profile) → contrôle
  de complétude. À la fin, tout ce dont les skills ont besoin est setup ou explicitement différé.
  Triggers : « set up my wiki », « initialize », « initialise mon wiki », « configure le vault ».
---

# wiki-init — initialisation complète et vérifiée

À la fin de `wiki-init`, le profil ne doit avoir **aucun champ cœur manquant** et **aucun `id`
de canal `null`** pour un Slack connecté. Tout MCP requis par une source activée est vérifié
(brancher maintenant ou différer), jamais ignoré en silence.

## Procédure (séquentielle, ne pas réordonner)

1. **Structure du vault** — invoquer `wiki-setup` (Ar9av) : arborescence (`concepts/`, `entities/`…),
   fichiers spéciaux (`index.md`, `hot.md`, `.manifest.json`), `~/.obsidian-wiki/config`. Attendre.
   Si la structure existe déjà (`index.md` présent), passer cette étape et le signaler.
2. **Profil interactif & vérifié** — invoquer `wiki-profile`. Cette invocation **doit être
   interactive** : `wiki-profile` dialogue famille par famille, vérifie les MCP par source
   (Slack / Confluence / Calendar — voir sa « Carte des MCP requis ») et résout les IDs.
   **Ne jamais** transformer cet appel en passe-plat : si `wiki-profile` n'a pas posé ses
   questions, l'init n'est pas terminée.
3. **Gate de complétude + rapport** — ne déclarer « terminé » que si :
   - `owner.name` et `owner.role` sont remplis (les autres champs identité : remplis ou
     explicitement déclinés) ;
   - `tools.model_tiers`, `tools.link_format`, `tools.retro_day` sont remplis ;
   - `brief.scoring_axes` + `brief.thresholds` sont remplis ;
   - chaque source **activée** est soit ✅ **résolue** (MCP dispo, IDs écrits) soit ⏳ **`pending`**
     (MCP différé, noté).
   Puis afficher le **rapport final** : par source → ✅ prêt / ⏳ pending (avec la marche à suivre
   pour brancher le MCP **et la commande de relance** `engramme-assist`/`wiki-profile`), liste
   des fichiers écrits (`profile.yml` global + vault, `state/channels.yml`), et le chemin du vault.

## Règles
- Ne jamais exécuter l'étape 2 avant l'étape 1.
- Si le profil existe déjà, l'étape 2 le **complète** sans écraser, et tente de résoudre les IDs
  encore `null`.
- L'étape 3 ne « valide » jamais une init où une source activée est restée sans MCP **et** sans
  être marquée `pending`.
