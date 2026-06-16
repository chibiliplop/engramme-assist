# Agent E — daily-update final maintenance (prompt)

Spawn this after Step 5 wiki writes and Step 6 state persistence. The orchestrator
substitutes `<synth_model>` and passes only the fenced block as the subagent prompt.

```
Subagent type: general-purpose
Model: <synth_model>

Task — invoke skill `daily-update` in Run Mode (default), as morning-brief's
Agent E (so SKIP its Step-0 idempotence guard — pages were just written).
Run the full maintenance cycle on the vault as it now stands:
source-freshness check, gardener script pass (`_meta/scripts/gardener.py
--apply`: index rebuild, _raw TTL, review queue, archiving, promotions),
hot.md regen, write the vault-scoped state file, validate via
`gardener.py --check`, append the DAILY-UPDATE line to log.md, QMD refresh.
You own the SINGLE QMD reindex for this whole run — the Step-5 agents
skipped QMD on purpose, so reindex now covers every page they wrote.
Do NOT read Slack / calendar / Claude sessions — pure vault maintenance.

Return a one-line summary: fresh/stale/missing counts, index pages added,
hot.md refreshed yes/no, QMD status. Include verify_backlog_claims,
verify_backlog_pages and review_overdue_count when available so the orchestrator
can decide whether to add the `/wiki-verify` nudge.
```
