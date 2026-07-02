---
name: wiki-dedup
description: >
  Scan the Obsidian wiki for page-level identity collisions — different pages covering the same
  concept under different names (e.g. "RSC" vs "React Server Components") — and merge them.
  Use this skill when the user says "dedup my wiki", "find duplicate pages", "merge duplicates",
  "identity resolution", "consolidate my wiki", "I have duplicate pages", or "my wiki has two pages
  for the same thing". Distinct from wiki-lint (which checks structure) and cross-linker (which adds
  links) — this skill makes destructive page-level merges and requires careful confirmation.
---

<!-- adopted from obsidian-wiki==2026.6.5 — engramme overlay owns this copy; diff against upstream releases before bumping the pin -->

# Wiki Dedup — Identity Resolution and Page-Level Deduplication

You are finding and merging wiki pages that cover the same concept under different names. This is a write-heavy, potentially destructive skill — page merges cannot be automatically undone. Work carefully and confirm before acting in merge mode.

**Detection is scripted; judgement is yours.** Near-duplicate *detection* is a mechanical vault-wide comparison handled by `page_lookup.py --pairs` — not an O(n²) LLM sweep. You open full page bodies **only** for the pairs the script flags, deliver the semantic verdict (merge / keep-separate / needs-review), and perform the merges. Identity resolution and merging are this skill's exclusive ownership (see `AGENTS.md` → *Skill ownership*).

## Before You Start

1. **Resolve config** — follow the Config Resolution Protocol in `llm-wiki/SKILL.md` (walk up CWD for `.env` → `~/.obsidian-wiki/config` → prompt setup). This gives `OBSIDIAN_VAULT_PATH` and `OBSIDIAN_LINK_FORMAT`.
2. Read `index.md` to get the full page inventory with one-line descriptions and tags.
3. Read `log.md` briefly — if a dedup run just happened, note what was already merged.

## Modes

| Mode | Flag | Behavior |
|---|---|---|
| **Audit** | *(default)* | Report candidates only — no writes |
| **Merge** | `--merge` | Show each confirmed pair, ask for confirmation before merging |
| **Auto-merge** | `--auto` | Merge all high-confidence pairs (`score ≥ 0.90`) non-interactively |

If the user doesn't specify, run in **Audit** mode and present findings before asking whether to proceed.

## Step 1: Build the Page Registry

You need frontmatter only for the pages that surface as candidate pairs in Step 2 — **defer this grep until after the script runs and scope it to the flagged pages** (a full-vault frontmatter registry is unnecessary work now that detection is scripted).

For each page that appears in a Step 2 pair, extract from frontmatter:
- `node_id` — relative path from vault root, without `.md`
- `title` — frontmatter `title` field
- `aliases` — frontmatter `aliases` list (may be absent)
- `tags` — frontmatter `tags` list
- `category` — directory prefix

Build a lookup table: `node_id → {title, aliases, tags, category, summary}` — this feeds the audit report and the merge tiebreakers.

**Title extraction note:** Some pages use YAML block scalars (`title: >-` or `title: |`). When the `title:` value is `>-`, `>`, `|`, or `|-`, the actual title is on the next indented line — read it from there. Never treat the literal `>-` as a title.

## Step 2: Detect Candidate Pairs (scripted)

Near-duplicate detection is a mechanical, vault-wide comparison — a script does it, not an O(n²) LLM sweep. Run:

```bash
python3 "$OBSIDIAN_VAULT_PATH/_meta/scripts/page_lookup.py" --pairs --threshold 0.75
```

It returns a JSON array `[{path_a, path_b, score}]` of near-duplicate page pairs across the whole vault (it already excludes `_archives/`, `_raw/`, redirect stubs, and the special files). The script's default `--threshold` is `0.82` (near-certain only); pass `0.75` as above to also surface the MEDIUM band.

Bucket each returned pair by `score`:

| Score | Label |
|---|---|
| ≥ 0.90 | HIGH — almost certainly the same concept |
| 0.75–0.89 | MEDIUM — likely the same, verify |

Carry all returned pairs into Step 3.

**Do not re-derive similarity by reading pages** — the score is the script's, and it already accounts for title token-overlap, edit distance, substring containment, alias cross-match, shared category, and tag overlap. Your value-add is the semantic verdict in Step 3, which is what the script cannot do.

### Batch and exit rules

- If the script returns **no pairs**, report "no duplicate candidates found" and stop.
- If it returns **more than 50 pairs**, process them in batches of 50 — pause and report progress between batches.

## Step 3: Semantic Verdict

For each candidate pair (sorted by score descending):

1. Read both pages in full (full page read — justified because candidate pool is small).
2. Ask: are these pages covering the **same concept**, or are they distinct?

Assign one of three verdicts:

| Verdict | Meaning |
|---|---|
| `merge` | Same concept — different name, abbreviation, alias, or accidental duplicate. Safe to merge. |
| `keep-separate` | Related but distinct — e.g. "Server Actions" vs "Server Components" are related React features, not duplicates. |
| `needs-review` | Ambiguous — substantial overlap but also meaningful differences. Flag for the user to decide. |

Attach a short reason to each verdict (one sentence). This appears in the report and the log.

## Step 4: Audit Report

Always produce this report, even in merge/auto-merge mode (so the user sees what will happen):

```markdown
## Wiki Dedup Report

### High-Confidence Candidates (score ≥ 0.90): N pairs

| Score | Page A | Page B | Verdict | Reason |
|---|---|---|---|---|
| 0.95 | `concepts/rsc.md` | `concepts/react-server-components.md` | merge | "RSC" is the abbreviation; both pages cover identical material |
| 0.91 | `entities/vaswani-2017.md` | `references/attention-is-all-you-need.md` | keep-separate | One is a person stub, one is a paper reference |

### Medium-Confidence Candidates (score 0.75–0.89): N pairs

| Score | Page A | Page B | Verdict | Reason |
|---|---|---|---|---|
| 0.82 | `concepts/fine-tuning.md` | `concepts/finetuning.md` | merge | Same concept, hyphenation variant |

### Needs Human Review: N pairs

| Score | Page A | Page B | Reason |
|---|---|---|---|
| 0.78 | `concepts/agents.md` | `concepts/autonomous-agents.md` | Substantial overlap but "agents" may intentionally be broader |

### Summary
- Pages scanned: N
- Candidate pairs found: M
- Recommended merges: X
- Keep separate: Y
- Needs review: Z
```

In **Audit mode**, stop here and ask: "Run `--merge` to interactively merge the recommended pairs, or `--auto` to merge all high-confidence ones automatically?"

## Step 5: Merge

For each `merge` verdict pair (in merge or auto-merge mode):

In **merge mode**: show the pair and verdict, then ask: "Merge `[Page A]` into `[Page B]`? (yes/skip/review)". Skip on anything other than yes.

In **auto-merge mode**: only process HIGH-confidence (`score ≥ 0.90`) merges without prompting.

### 5a: Pick the canonical page

Apply these tiebreakers in order until one wins:

1. **More incoming wikilinks** — grep the vault for `[[node_id]]` references; higher count wins
2. **Richer content** — longer page body (more lines) wins
3. **More sources** — larger `sources:` list wins
4. **Title length** — longer, more descriptive title wins (e.g. "React Server Components" beats "RSC")
5. **Alphabetical** — earlier title wins

The canonical page is the **survivor**. The other page becomes the **secondary** (to be merged in, then replaced with a redirect stub).

### 5b: Merge content into the canonical page

Read both pages. Update the canonical page:

- **`aliases:`** — add secondary page's title and all its aliases (no duplicates)
- **`tags:`** — merge both tag lists (deduplicate, cap at 5 domain tags + system tags)
- **`sources:`** — merge both source lists (deduplicate)
- **`relationships:`** — merge both relationship lists (deduplicate by target, prefer typed entries over untyped)
- **`base_confidence`** — recompute using the union of sources and the formula from `llm-wiki/SKILL.md`
- **`updated`** — set to now
- **`summary:`** — rewrite to cover the merged scope if the secondary page added new ground
- **Body content** — merge unique sections and bullets from the secondary page. Do not blindly append — integrate the content. Avoid duplicating claims already present in the canonical page. Use `^[inferred]` markers where synthesis is needed.
- **`provenance:`** — recompute after merging

### 5c: Write a redirect stub at the secondary page path

```markdown
---
title: <secondary page title>
redirects_to: "[[<canonical node_id>]]"
aliases: [<secondary aliases>]
category: <secondary category>
tags: []
created: <secondary original created>
updated: <ISO timestamp now>
---

This page has been merged into [[<canonical page title>]].
```

The `redirects_to:` field tells any skill reading this page to follow the redirect rather than treat it as content.

### 5d: Rewrite wikilinks vault-wide

Grep the entire vault for any link pointing at the secondary slug:

- `[[secondary-slug]]` → `[[canonical-slug]]`
- `[[secondary-slug|display text]]` → `[[canonical-slug|display text]]`
- If `OBSIDIAN_LINK_FORMAT=markdown`: `[text](../path/to/secondary.md)` → `[text](../path/to/canonical.md)`

**Safety rules:**
- Never rewrite inside code blocks (``` fences or `inline code`)
- Never rewrite inside the redirect stub itself (that's the one place the old slug should remain legible)
- Never use `rm` or destructive shell ops — only Edit/Write tools
- Rewrite one file at a time, verifying each before moving on
- If a file has zero occurrences, skip it

### 5e: Update tracking files

**`index.md`** — Remove the secondary page's entry. Update the canonical page's entry with the merged summary.

**`.manifest.json`** — For the secondary page's source entries: add `"merged_into": "<canonical node_id>"` to each. For the canonical page: merge in the secondary's `pages_created` and `pages_updated` lists.

**`hot.md`** — Update Recent Activity: "Merged N duplicate pairs; canonical pages updated."

### 5f: Final check

After all merges, grep the vault for any remaining `[[secondary-slug]]` references (in non-stub files). If any survive, report them — the rewrite step may have missed a non-standard link format.

## Step 6: Log

Append to `log.md`:
```
- [TIMESTAMP] DEDUP mode=audit|merge|auto-merge pages_scanned=N pairs_found=M merged=X kept_separate=Y needs_review=Z wikilinks_rewritten=W
```

## Redirect Stub Handling

Other skills should handle redirect stubs as follows:

- **`wiki-export`** — skip pages with `redirects_to:` in frontmatter; they are not content nodes
- **`wiki-query`** — if a search hits a redirect stub, follow `redirects_to:` and read the canonical page instead
- **`wiki-lint`** — validate that every `redirects_to:` wikilink resolves to an existing, non-stub page (a redirect chain — stub pointing to stub — is an error)
- **`cross-linker`** — treat redirect stubs as non-targets; never add a new `[[wikilink]]` pointing at a stub page

## Tips

- **Audit first, always.** Even in auto-merge mode, the audit report is shown. Read it before trusting the results.
- **Check `needs-review` last.** These are the hard cases — don't batch them with obvious merges.
- **Abbreviations are the most common case.** "GPT" / "GPT-4" / "GPT4", "RSC" / "React Server Components", "LLM" / "Large Language Models" — these score high on substring containment and are almost always safe to merge.
- **Different versions are not duplicates.** "GPT-3" and "GPT-4" are related but distinct. "fine-tuning" and "fine-tuning-llms" may be distinct (technique vs. specific application).
- **Run `cross-linker` after dedup.** The redirect stubs leave the graph in a slightly inconsistent state. Cross-linker will tighten it up.

## QMD Refresh After Vault Writes

**GUARD: skip if `$QMD_WIKI_COLLECTION` is unset or the caller passed `QMD=skip`.** QMD is a search index, not the source of truth — never roll back a merge if refresh fails.

After merges are written, run `${QMD_CLI:-qmd} update`, then `${QMD_CLI:-qmd} embed` if it reports missing vectors (use `$QMD_CLI` if set, else `qmd`). Report one of: `QMD refreshed`, `QMD skipped: unset`, `QMD skipped: CLI unavailable`, `QMD failed: <error>`.