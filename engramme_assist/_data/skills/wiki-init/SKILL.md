---
name: wiki-init
description: >
  Single entry point for initializing an engramme-assist vault. Guarantees the order:
  structure (Ar9av's wiki-setup skill) → INTERACTIVE & verified profile (wiki-profile) →
  completeness check. By the end, everything the skills need is set up or explicitly deferred.
  Triggers: "set up my wiki", "initialize", « initialise mon wiki », « configure le vault ».
---

# wiki-init — complete, verified initialization

By the end of `wiki-init`, the profile must have **no missing core field** and **no `null`
channel `id`** for a connected Slack. Every MCP required by an enabled source is verified
(wire it up now or defer), never silently ignored.

## Procedure (sequential, do not reorder)

1. **Vault structure** — invoke `wiki-setup` (Ar9av): tree (`concepts/`, `entities/`…),
   special files (`index.md`, `hot.md`, `.manifest.json`), `~/.obsidian-wiki/config`. Wait.
   If the structure already exists (`index.md` present), skip this step and say so.
2. **Interactive & verified profile** — invoke `wiki-profile`. This invocation **must be
   interactive**: it converses family by family, verifies the MCP per source (Slack / Confluence /
   Calendar — see its "Required-MCP map") and resolves the IDs. **Never** turn this call into a
   pass-through: if `wiki-profile` hasn't asked its questions, init is not done.
3. **Completeness gate + report** — only declare "done" if:
   - `owner.name` and `owner.role` are filled (other identity fields: filled or explicitly declined);
   - `tools.model_tiers`, `tools.link_format`, `tools.retro_day` are filled;
   - `brief.scoring_axes` is filled and **each axis carries a `weight` (integer ≥ 1)** in addition to
     `name`/`description`; `brief.thresholds` carries `must_read` and `watch` with `must_read > watch`
     (exact schema: see "`brief` (scoring) schema" in wiki-profile);
   - each **enabled** source is either ✅ **resolved** (MCP available, IDs written) or
     ⏳ **`pending`** (MCP deferred, noted).
   Then show the **final report**: per source → ✅ ready / ⏳ pending (with the steps to wire up the
   MCP **and the re-run command**: re-run `wiki-profile`), the list of files written (`profile.yml`
   global + vault, `state/channels.yml`), and the vault path.

## Rules
- Never run step 2 before step 1.
- If the profile already exists, step 2 **completes** it without overwriting, and tries to resolve
  the still-`null` IDs.
