---
name: cross-linker
description: >
  Scan the Obsidian wiki and automatically discover missing cross-references between pages.
  Use this skill when the user says "link my pages", "find missing links", "cross-reference",
  "connect my wiki", "add wikilinks", "what pages should be linked", or after any large ingestion
  to ensure new pages are woven into the existing knowledge graph. Also trigger when the user
  mentions "orphan pages" in the context of wanting to connect them, or says things like
  "my wiki feels disconnected" or "pages aren't linked well". This is a write-heavy skill —
  it actually modifies pages to add links, unlike wiki-lint which just reports issues.
---

<!-- adopted from obsidian-wiki==2026.6.5 — engramme overlay owns this copy; diff against upstream releases before bumping the pin -->

# Cross-Linker — Automated Wiki Cross-Referencing

You are weaving the wiki's knowledge graph tighter by finding and inserting missing `[[wikilinks]]` between pages that should reference each other but currently don't.

**Discovery is script-first (`insights.py --json`), reads are scoped.** The candidate set — orphans and unlinked co-occurring pairs — comes from the graph script, and you read *only* the pages it points at. All link-count math (in/out, hub/peripheral) is read from the script's output, never recounted by reading pages. Blind full-vault reads are exactly what this framework exists to avoid; Step 1 still greps frontmatter only.

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `llm-wiki/SKILL.md` (walk up CWD for `.env` → `~/.obsidian-wiki/config` → prompt setup). This gives `OBSIDIAN_VAULT_PATH` and `OBSIDIAN_LINK_FORMAT` (default: `wikilink`).
2. Read `index.md` to get the full inventory of pages and their one-line descriptions
3. Skim `log.md` to see what was recently ingested (focus linking effort on new pages)

When inserting links in Step 4, apply the link format from `llm-wiki/SKILL.md` (Link Format section) using the `OBSIDIAN_LINK_FORMAT` value. When `OBSIDIAN_LINK_FORMAT=markdown`, compute the relative `.md` path from the **file being edited** to the target page.

## Step 1: Build the Page Registry

Glob all `.md` files in the vault (excluding `_archives/`, `.obsidian/`). For each page, extract:

- **Filename** (without `.md`) — this is the wikilink target
- **Title** from frontmatter
- **Aliases** from frontmatter (if any)
- **Tags** from frontmatter
- **Category** from frontmatter or directory inference
- **One-line summary** — first sentence or `title` field

Build a lookup table:

```
page_name → { path, title, aliases, tags, summary }
```

This is your "vocabulary" — every entry in this table is a valid wikilink target.

## Step 2: Find Link Candidates (script-first)

Do **not** read every page. The candidate set comes from the graph script; you read only the pages it points at.

Run the link-graph analysis:

```bash
python3 "$OBSIDIAN_VAULT_PATH/_meta/scripts/insights.py" --json
```

It returns `{orphans, backlinks, broken_links, link_counts, cooccurrence_candidates}`:

- **`orphans`** — pages with no incoming links. These are the priority targets for new links.
- **`cooccurrence_candidates`** — `[{a, b, weight}]`: page pairs that co-occur across the vault (shared tags, shared mentions) but are **not** yet linked. Each pair is a candidate link; higher `weight` = stronger signal.
- **`link_counts`** — per page `{in, out}` totals. **Use these numbers directly** for the hub/peripheral and in/out signals in Step 3 — never recount links by reading pages.
- **`backlinks` / `broken_links`** — supporting context (who links to whom; dangling links).

**Build the candidate page set:**

- **Full run (default):** every `orphan`, plus both endpoints of the highest-`weight` `cooccurrence_candidates`. Cap the pair set so the pass stays bounded — the point is to weave in the loose and the strongly-co-occurring, not to re-scan the whole vault.
- **Scoped run (e.g. morning-brief step 5b):** the caller scopes the run to a specific set of just-ingested/staged pages. Restrict the candidate set to those pages plus their `cooccurrence_candidates` and any that are `orphans`. When no explicit scope is passed but the run follows an ingest, `log.md` (skimmed in *Before You Start*) tells you which pages to prioritise.

Either way the discovery is script-driven — no full-vault body reads.

**Now, and only now, read the candidate pages** (full `Read`, justified because the set is small). For each candidate page:

1. **Extract existing wikilinks** — the `[[...]]` already present, so you don't double-link.
2. **Detect unlinked mentions** — check whether the body contains, unwrapped, any registry entry: page filenames, titles, aliases, or entity/project/concept names (see Matching Rules).
3. **Confirm co-occurrence pairs** — for each `cooccurrence_candidate` touching this page, decide whether the body supports a real link and where to place it.

### Matching Rules

- **Case-insensitive matching** for names (e.g., "my-project" matches page `MyProject`)
- **Diacritic-insensitive matching** — normalize both the page name and the body text with Unicode NFKD (decompose accented characters to base + combining marks, strip combining marks) before comparing. This ensures body text "Muller" matches page `[[entities/müller]]` and vice versa.
- **Skip self-references** — a page shouldn't link to itself
- **Skip common words** — don't link "the", "and", generic terms. Only match on distinctive names
- **Prefer the shortest unambiguous wikilink path** — use `[[page-name]]` not `[[full/path/to/page-name]]` when the name is unique across the vault
- **Don't link inside code blocks** or frontmatter
- **Don't double-link** — if `[[foo]]` already appears on the page, don't add another

## Step 3: Score and Rank Suggestions

Not every possible link is worth adding. Score each candidate using a composite signal, then tag it with a confidence label.

### Scoring

| Signal | Points | Example |
|---|---|---|
| **Exact name match in text** | +4 | "MyProject" appears in body text → link to my-project.md |
| **Shared tags (2+)** | +2 | Both tagged `#ai #agent` but no link between them |
| **Same project, no link** | +2 | Both under `projects/my-project/` but don't reference each other |
| **Mentioned entity/concept** | +2 | Page mentions "knowledge graphs" → link to `[[concepts/knowledge-graphs]]` |
| **Cross-category connection** | +2 | Source is in `concepts/`, target is in `entities/` (or `skills/` ↔ `synthesis/`) — different knowledge layers make this link more architecturally valuable |
| **Peripheral→hub reach** | +2 | Source page has ≤ 2 total links (peripheral) but target has ≥ 8 (hub) — connecting a loose page to a load-bearing concept |
| **Partial name match** | +1 | "graph" appears but page is `knowledge-graphs` — plausible but ambiguous |

**Link counts are read, not recounted.** The peripheral/hub thresholds (≤ 2, ≥ 8) and any in/out figure come from `link_counts` in the Step 2 script output — do not re-derive them by reading or grepping pages.

### Confidence labels

Tag each candidate with a confidence label based on its score:

| Score | Label | Action |
|---|---|---|
| ≥ 6 | **EXTRACTED** | Link is effectively certain — exact mention or very strong match. Apply inline. |
| 3–5 | **INFERRED** | Link is a reasonable inference — shared context, cross-category, peripheral→hub. Apply inline or as Related section. |
| 1–2 | **AMBIGUOUS** | Weak or partial match. Skip unless user specifically asks to connect loose pages. |

Only act on **EXTRACTED** and **INFERRED** candidates. Include the confidence label in the Cross-Link Report so the user can review INFERRED links before trusting them.

## Step 4: Apply Links

For each page with missing links:

### 4a: Inline linking (preferred)

Find the first natural mention of the term in the body text and wrap it in wikilinks:

**Before:**
```markdown
This project uses knowledge graphs to connect entities.
```

**After:**
```markdown
This project uses [[concepts/knowledge-graphs|knowledge graphs]] to connect entities.
```

Use the `[[path|display text]]` format when the wikilink path differs from the display text.

### 4b: Related section (fallback)

If the term isn't mentioned naturally in the body but the pages are semantically related (shared tags, same project), add a `## Related` section at the bottom of the page:

```markdown
## Related

- [[projects/my-project/my-project]] — Also uses AI agents for research automation
- [[concepts/knowledge-graphs]] — Core technique used in this project
```

If a `## Related` section already exists, append to it. Don't duplicate existing entries.

### 4c: Infer and write relationship type

For every EXTRACTED or INFERRED link added (inline or related section), infer a semantic relationship type from the surrounding sentence context and write it to the page's `relationships:` frontmatter block. Skip AMBIGUOUS links.

**Type inference rules** — scan the sentence containing the mention (or, for related-section links, the page title and shared-tag context):

| Sentence pattern | Inferred type |
|---|---|
| "X extends / builds on / generalises Y" | `extends` |
| "X implements / is an implementation of Y" | `implements` |
| "X contradicts / opposes / refutes / is at odds with Y" | `contradicts` |
| "X is derived from / based on / adapted from Y" | `derived_from` |
| "X uses / relies on / depends on / requires Y" | `uses` |
| "X replaces / supersedes / deprecates Y" | `replaces` |
| Shared tags or cross-category inference with no directional cue | `related_to` |

If the surrounding context is ambiguous or the link came from shared-tag matching (no in-body mention), default to `related_to`.

**Writing the block:**

Read the page's YAML frontmatter. If a `relationships:` block already exists, append new entries without duplicating existing targets. If the block is absent, add it after `aliases:` (or after `tags:` when `aliases:` is missing).

```yaml
relationships:
  - target: "[[concepts/knowledge-graphs]]"
    type: uses
```

Always use wikilink format (`[[path/to/page]]`) for `target` values in the `relationships:` YAML block — regardless of `OBSIDIAN_LINK_FORMAT`. The `OBSIDIAN_LINK_FORMAT` setting controls body content; frontmatter properties always use wikilink syntax so that `wiki-export` can reliably parse them.

Only add entries for links added in this cross-linker run — do not touch typed entries that were already present.

## Step 5: Score Misc Page Affinity

After the main linking pass, update affinity scores for all pages in `misc/` (pages with `promotion_status: misc` in their frontmatter, or located under the `misc/` directory).

For each misc page:

1. **Collect outgoing links** — all `[[wikilinks]]` in the page body (you already read misc bodies for the linking pass)
2. **Collect incoming links** — read them from the `backlinks` map in the Step 2 `insights.py --json` output; do not grep the vault for `[[misc/<slug>]]` references
3. For each linked page (both directions), check if it belongs to a project:
   - Lives under `projects/<project-name>/`
   - Has a `project:` frontmatter field matching a project name
4. Group by project name and sum: `outgoing_links + incoming_links`
5. Update the `affinity` frontmatter block on the misc page:

```yaml
affinity:
  obsidian-wiki: 3
  another-project: 1
```

6. If any project's score ≥ 3: flag this page as a **promotion candidate** and record it for the report

**Efficiency note:** only read the full body of misc pages — other pages only need a frontmatter grep to determine their project membership.

## Step 6: Report

Present a summary:

```markdown
## Cross-Link Report

### Links Added: 23 across 12 pages

| Page | Links Added | Confidence | Placement | Relationship Types |
|---|---|---|---|---|
| `projects/my-project/my-project.md` | 3 | EXTRACTED | 2 inline, 1 related | uses ×2, related_to ×1 |
| `entities/jane-doe.md` | 5 | INFERRED | 3 inline, 2 related | extends ×1, uses ×3, related_to ×1 |
| ... | | | | |

### Orphan Pages Remaining: 2
- `references/foo.md` — no incoming or outgoing links found
- `concepts/bar.md` — could not find related pages

### Misc Promotion Candidates: N
Pages in misc/ that have ≥ 3 connections to a single project — ready to be promoted:

| Page | Top Project | Score |
|---|---|---|
| `misc/web-martinfowler-articles-microservices.md` | `obsidian-wiki` | 4 |

To promote: move the page to `projects/<project-name>/references/` and update all backlinks.

### Pages Skipped: 3
- `index.md`, `log.md` — special files
- `_archives/*` — archived content
```

## Step 7: Update Log and Hot Cache

Append to `log.md`:
```
- [TIMESTAMP] CROSS_LINK pages_scanned=N links_added=M typed_relations_written=T pages_modified=P orphans_remaining=Q misc_affinity_updated=R promotion_candidates=S
```

**`hot.md`** — Read `$OBSIDIAN_VAULT_PATH/hot.md` (create from the template in `wiki-ingest` if missing). Update **Recent Activity** with a one-line summary of what was linked — e.g. "Cross-linked 23 mentions across 12 pages; 2 orphans remain." Keep the last 3 operations. Update `updated` timestamp.

## Tips

- **Run after every ingest.** New pages are almost always poorly connected. This is the fix.
- **Be conservative with inline links.** Only link the first natural mention, not every occurrence.
- **Don't touch pages in `_archives/`.** Those are frozen snapshots.
- **Respect existing structure.** If a page carefully curates its links in a `## Key Concepts` section, add to that section rather than creating a separate `## Related`.
- **Entity pages are link magnets.** An entity like `jane-doe` should be linked from almost every project page. Prioritize these.

## QMD Refresh After Vault Writes

**GUARD: skip if `$QMD_WIKI_COLLECTION` is unset or the caller passed `QMD=skip`.** QMD is a search index, not the source of truth — never roll back vault writes if refresh fails.

After this skill has written markdown, run `${QMD_CLI:-qmd} update`, then `${QMD_CLI:-qmd} embed` if it reports missing vectors (use `$QMD_CLI` if set, else `qmd`). Report one of: `QMD refreshed`, `QMD skipped: unset`, `QMD skipped: CLI unavailable`, `QMD failed: <error>`.