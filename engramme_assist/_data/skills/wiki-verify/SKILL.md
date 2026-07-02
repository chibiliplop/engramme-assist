---
name: wiki-verify
description: Human-in-the-loop validation of inferred / uncertain wiki knowledge. Surfaces claims marked ^[inferred] or ^[ambiguous], pages with lifecycle draft/stub or low base_confidence, gathers evidence from their sources, then asks Thomas to decide — vrai / faux / à éditer / laisser ouvert. ONLY the human's answer promotes lifecycle (draft→reviewed→verified) or marks disputed; the skill never auto-validates. Triggers on "/wiki-verify", "valide l'inféré", "vérifie ce qui est incertain", "passe en revue les pages non sûres", "promote verified pages", "what needs validating".
---

# wiki-verify

Maintain and validate the *uncertain* knowledge in the vault. Ingest skills write everything as `draft` and mark synthesized claims `^[inferred]` — but nothing ever revisits them. Over time the vault accumulates plausible-but-unchecked claims. This skill closes that loop.

**Core principle: the AI gathers, the human decides.** The skill finds risky claims, re-reads their sources, and presents evidence + a recommendation — but the *validation itself is a human answer*. This matches the `llm-wiki` lifecycle state machine, where `reviewed` / `verified` / `disputed` are **human-only** transitions. The skill never promotes a page to `verified` on its own.

## When to use

- Manual `/wiki-verify` — optionally scoped: `/wiki-verify [page title | #tag | project-name | --all]`.
- After a big ingest, when many fresh `draft` pages with `^[inferred]` claims have landed.
- When `wiki-lint` Check 7 flags speculation-heavy or unsourced-synthesis pages.
- Periodically (e.g. monthly, via `weekly-retro`'s maintenance tail) to keep the verified set fresh.

This is the *write* counterpart to `wiki-lint`'s provenance/confidence *diagnostics*: lint reports, wiki-verify resolves — with the human in the loop.

## Step 1 — Resolve config

Follow the Config Resolution Protocol in `llm-wiki/SKILL.md` to get `OBSIDIAN_VAULT_PATH`. Read `$OBSIDIAN_VAULT_PATH/AGENTS.md` if present. Read `index.md` and `hot.md` for context. Honour `OBSIDIAN_LINK_FORMAT`.

## Step 2 — Build the validation worklist

**Default scope = the active portfolio.** The inferred-claims backlog drains slower than it grows (roughly ten claims/week against a vault-wide pile in the hundreds), so validating the whole vault is a losing race. By default, restrict the worklist to what matters now:

- **Active-portfolio initiatives** — `projects/` pages with `engagement:` set **and** `status: active`. Read `projects/_portfolio.md` (the derived portfolio view) for the current list rather than re-deriving it; include the claims on those initiative hubs and on pages under their `projects/<slug>/` folders.
- **Plus any page Thomas explicitly names** in the invocation (`/wiki-verify [page title | #tag | project-name]`). A named scope *overrides* the portfolio default — validate exactly what was named.

Everything else — concepts, entities, references, and paused/done initiatives — is **out of scope unless `--all` is passed**. `--all` drops the portfolio filter and walks the whole vault's ranked list. State the scope you used at the top of the session, e.g. *"scope: active portfolio (13 initiatives) + [[named-page]] — pass `--all` for the rest of the vault."*

Within that scope, use the Retrieval Primitives (frontmatter-scoped greps, not full-page reads). Collect candidate claims and rank them. A *claim* is one `^[inferred]` / `^[ambiguous]` line; a *page* enters the list if it has any candidate claim **or** matches a page-level risk signal.

Candidate signals (grep, don't read bodies yet):
- Bodies containing `^[inferred]` or `^[ambiguous]` markers (one entry per marked line).
- Frontmatter `lifecycle: draft` or `lifecycle: stub` (never validated).
- Frontmatter `base_confidence` < 0.5.
- `provenance:` block with `inferred` ≥ 0.40 or `ambiguous` ≥ 0.15.

Priority score (validate highest first — errors on these have the widest blast radius):
1. **Hub pages** — top-10 by incoming wikilink count. An inferred claim on a hub propagates to everything that links it.
2. High inferred fraction (`inferred` field or counted markers).
3. Lowest `base_confidence`.
4. `lifecycle: draft`/`stub` over already-`reviewed`.

Default session size: the **top 10–15 claims**, like a retro — keep it finishable in one sitting. If scoped to a single page/tag/project, take all its claims. `--all` drops the portfolio scope and walks the whole vault's ranked list in batches, confirming before each new batch. **If you cap the list, say so explicitly** ("showing 12 of 41 in scope — re-run, or `--all` for the rest of the vault"); never imply full coverage.

## Step 3 — Gather evidence (per claim, before asking)

For each claim, assemble what's needed for a human to judge it in seconds — do NOT decide yourself:
- Read the claim in context (the surrounding section, not the whole page).
- Re-open the page's `sources:` — read the cited file / transcript / URL / Slack permalink / Confluence page (via the matching MCP) and check whether it supports the claim.
- If no usable `sources:`, widen: `wiki-query` (index-only first), QMD semantic search (`$QMD_CLI` on `$QMD_WIKI_COLLECTION`), related pages by shared tags, or web/MCP only when the claim is externally checkable.
- **Mandatory — read the concrete source before forming any recommendation.** You must actually open the cited source and capture *what it literally says* about this claim: a direct quote or a specific paraphrase of the passage, with its pointer — never a restatement of the claim itself. If the source can't be opened, or doesn't mention the claim, say exactly that ("`sources:` X does not address this"; "URL unreachable") rather than implying support. Thomas rejects bare inference verdicts ("this looks inferred, confirm?") with no source read behind them — and reading the source frequently reverses the recommendation.
- Form a **recommendation** (confirm / refute / still-uncertain) with a one-line rationale and the concrete evidence pointer. The recommendation is a *hint for the human*, not a decision.

For high-stakes claims (hub pages, or anything that would flip a decision), optionally spawn 1–3 skeptic sub-agents prompted to *refute* the claim, and summarise whether they could. Still hand the verdict to the human.

## Step 4 — Ask the human (the validation itself)

Present claims one page at a time. For each claim show: the claim text, its current marker + the page's `base_confidence`/`lifecycle`, the **concrete source evidence** (the quote or specific paraphrase of what the cited source actually says about the claim, with its pointer — from Step 3; never a restatement of the claim, never "the source supports it" with nothing shown), and your recommendation. Then ask — use `AskUserQuestion` so the answer is structured. Options, in French:

- **✅ Vrai** — confirmed against the evidence.
- **❌ Faux** — refuted; the claim is wrong.
- **✏️ À éditer** — partly right; the human supplies (or dictates) the corrected wording.
- **❓ Laisser ouvert** — genuinely uncertain; keep it flagged, move to Open Questions.
- **⏭️ Passer** — skip for now, no change.

The human may answer per-claim or wave a batch through ("tout vrai sur cette page"). Never pick for them; if they don't answer a claim, treat it as **Passer**. Capture any free-text correction verbatim for the edit case.

## Step 5 — Apply the human's decision

Only now write. Per outcome:

| Answer | Marker change | Confidence / lifecycle | Other |
|---|---|---|---|
| **Vrai** | drop the `^[inferred]`/`^[ambiguous]` suffix (becomes extracted) | recompute `base_confidence` (formula below); if the human says it's solid, propose `lifecycle: reviewed` or `verified` — **only with their explicit say-so** | bump `last_verified: <today>` |
| **Faux** | remove or correct the claim | if it conflicts with another page, offer a `relationships: contradicts` entry and `lifecycle: disputed` (human confirms) | — |
| **À éditer** | apply the human's wording; keep `^[inferred]` only if still synthesized | recompute `base_confidence` if sources changed | — |
| **Laisser ouvert** | keep the marker | no lifecycle change | ensure the claim appears under a `## Open Questions` section (create it if missing), with its source pointer |
| **Passer** | no change | no change | — |

Rules:
- **Never set `reviewed`/`verified`/`disputed` without an explicit human answer for that page.** These are human-only transitions per `llm-wiki`. The skill at most *proposes* them.
- **No who/how meta.** A promotion is only the `lifecycle` change plus a `last_verified: <today>` bump — never write a `lifecycle_reason` or any "human-verified via wiki-verify" prose. Per the vault conventions (AGENTS.md) the editor is always the owner and the tool/date of the edit is not knowledge. A refutation deletes the claim; it leaves no "réfuté" trace.
- Recompute `base_confidence` with the `llm-wiki` formula: `min(distinct_sources/3,1)×0.5 + avg_source_quality×0.5`. Update `lifecycle_changed` on any state change.
- Always bump `updated:` on a touched page and refresh its `provenance:` fractions if markers changed.

## Step 6 — Lifecycle vocabulary reconciliation

This vault currently uses non-schema lifecycle values (`active`, `stub`) alongside `draft`. The schema enum is `draft | reviewed | verified | disputed | archived`. When you touch such a page, **ask the human** how to map it (suggested: `stub → draft`, `active → reviewed`) rather than rewriting silently. Apply only what they confirm. Surface the count of non-enum pages once at the start so they can decide whether to normalise in this session.

## Step 7 — Bookkeeping

After writes:
- Append to `log.md`:
  `- [TIMESTAMP] WIKI_VERIFY claims_reviewed=N confirmed=C refuted=F edited=E left_open=O lifecycle_promotions=P disputed=D pages_touched=T`
- Update `hot.md` (≤500-word snapshot) noting what was validated this session.
- Refresh QMD per the standard block: `${QMD_CLI:-qmd} update` (+ `embed` if vectors are stale), only if `$QMD_WIKI_COLLECTION` is set and vault markdown changed. Report the QMD status line; never roll back vault changes on QMD failure.
- Do NOT touch `.manifest.json` (no new sources ingested).

## Output

A short session report:

```markdown
## Validation — <date>

Reviewed N claims across M pages (showing N of TOTAL — re-run for the rest).

### ✅ Confirmed (C)
- `concepts/foo.md` — "<claim>" → extracted, base_confidence 0.5→0.67, proposed lifecycle reviewed
### ❌ Refuted (F)
- `entities/bar.md` — "<claim>" → corrected; flagged disputed vs [[other-page]]
### ✏️ Edited (E)
- ...
### ❓ Still open (O)
- `synthesis/baz.md` — moved to Open Questions (source inconclusive)

Lifecycle: P promotions (human-approved), D disputed. QMD: <status>.
Next: K higher-priority claims remain unvalidated.
```

## Safety

- The human is the validator. The skill gathers evidence and proposes; it never marks anything `verified` on its own.
- One page's claims at a time; cap the session and say what was left.
- Quote evidence honestly — if the sources don't actually support a claim, recommend refute even if it "sounds right".
- Edits are surgical: change only the claim line + its frontmatter, never reflow the page.
