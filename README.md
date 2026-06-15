# engramme-assist

A profile-driven **overlay** for [`obsidian-wiki`](https://pypi.org/project/obsidian-wiki/)
(by Ar9av). It keeps the upstream skill framework and adds a config **profile** so the
personal skills (`morning-brief`, `weekly-retro`, `jot`, `daily-update`) read your identity,
sources and scoring from a private YAML instead of hardcoding them. The skill code stays
generic and shareable; your real values live in a gitignored profile.

```
obsidian-wiki (Ar9av)          engramme-assist (this overlay)
──────────────────────         ──────────────────────────────
vault structure, ingest,   +   profile.yml  ·  6 skills  ·  gardener/insights scripts
query, lint, export …          (identity & sources injected via {{profile.*}})
```

---

## What it adds

- **Profile** — `~/.obsidian-wiki/profile.yml` (global identity) merged with
  `$VAULT/_meta/profile.yml` (vault-local sources, tool prefs, brief scoring grid). Skills
  resolve `{{profile.*}}` placeholders from the merged result.
- **6 skills** (see below) — `wiki-init`, `wiki-profile`, `jot`, `morning-brief`,
  `weekly-retro`, `daily-update`.
- **`gardener.py` / `insights.py`** — programmatic-first maintenance scripts dropped into
  `$VAULT/_meta/scripts/`.
- **`AGENTS.generic.md`** — framework conventions + profile-loading protocol, no personal values.

---

## The skills

Each skill is invoked from your agent by a slash command or a natural phrase (EN + FR triggers).

### Setup skills (run once)

| Skill | What it does | Trigger |
|---|---|---|
| **`wiki-init`** | Single entry point for initializing a vault. Enforces the order **structure first** (Ar9av's `wiki-setup`: creates `concepts/`, `entities/`, `index.md`, `hot.md`, `.manifest.json`, writes `~/.obsidian-wiki/config`) **then profile** (`wiki-profile`). | *"set up my wiki"*, *"initialise mon wiki"* |
| **`wiki-profile`** | Fills or updates the profile (identity, active sources, tool prefs, brief scoring axes) and bootstraps the minimal skill-managed config (`state/channels.yml` + excluded patterns). Interactive and **non-destructive** — an existing profile is completed, never overwritten. | *"update my profile"*, *"change my channels"*, *"ajoute un canal Slack"* |

### Daily-use skills

| Skill | What it does | Trigger |
|---|---|---|
| **`jot`** | Frictionless personal capture — the **push** channel of the wiki. One free-text line in, routed to the right home: a goal (`goals.md`), a task (`state/open-actions.md`), a direct page update, or a raw note (`_raw/notes/`). At most one clarifying question, ever. | *"/jot &lt;texte&gt;"*, *"note rapide"*, *"retiens que…"* |
| **`morning-brief`** | Daily briefing: aggregates what you missed since the last brief across Slack (two-stage triage→synth pipeline), Confluence, calendar and agent sessions; scores each item 1–10 (archi / métier / urgence / signal); builds **pre-meeting briefs** for non-routine meetings; injects active goals; and feeds topical wiki pages when signal is strong. Surfaces a coverage warning if a source couldn't be scanned. | *"/morning-brief"*, *"brief du matin"*, *"what did I miss"* — or **`--night`** to run it the evening before |
| **`weekly-retro`** | Structured weekly retrospective primed by the week's auto-compiled data (daily briefs, closed tasks, sessions, calendar) — **never starts from a blank page**. Captures impact-framed accomplishments + brag inputs, reviews prior actions/goals, detects recurring patterns, then runs a non-interactive **weekly maintenance tail** (history ingests, cross-linker, hot-topics, lint). Monthly/annual modes compile a self-assessment draft. | *"/weekly-retro"*, *"rétro"*, *"bilan de la semaine"* |
| **`daily-update`** | Lightweight maintenance cycle: checks source freshness, refreshes `index.md`, regenerates `hot.md`, and writes the state file the terminal notification reads. Runs `gardener.py` under the hood. Also sets up / verifies the cron + terminal-notification infrastructure on first use. | *"/daily-update"*, *"morning sync"*, *"refresh the wiki index"* — or the 9 AM cron |

### Maintenance scripts (called by the skills, runnable by hand)

| Script | What it does |
|---|---|
| **`gardener.py`** | Vault life-cycle mechanics: TTL on `_raw/`, archiving dead pages, promoting drafts, rebuilding the index. `--apply` writes, no flag = dry-run JSON report, `--check` validates, `--skip-if-fresh` no-ops if nothing changed. |
| **`insights.py`** | Graph analysis over the vault — hubs, bridges, dead ends — written to `_insights.md`. |

---

## Install

```bash
pip install engramme-assist          # pulls obsidian-wiki (pinned) as a dependency
engramme-assist install --vault /path/to/your/vault
```

<details>
<summary>From a source checkout instead</summary>

```bash
pip install -e .
python -m engramme_assist install --vault /path/to/your/vault
```
</details>

The overlay's skills and scripts ship **inside the package** (`engramme_assist/_data/`), so a
plain `pip install` is self-contained — no clone required.

`install` does three things:

1. delegates the base install to `obsidian-wiki setup` (all upstream skills, global config, bootstrap files);
2. lays this overlay's six skills on top of it;
3. drops `AGENTS.generic.md`, `profile.example.yml` and the gardener scripts into the vault — **non-destructively** (an existing file is never clobbered).

Then, in your agent, say **"set up my wiki"** → `wiki-init` runs the structure setup and fills your profile interactively.

> **Add `--copy`** to copy skill files instead of symlinking (forced automatically on Windows — see Platform notes).

---

## Routines

Once the vault is set up, the rhythm is: **a brief in the morning, a retro once a week, capture anytime.**

### Every working day

```bash
# in your agent, working directory = your vault
/morning-brief            # what you missed + what to prepare today
#   …or the evening before:  /morning-brief --night
/jot <a thought>          # capture goals / tasks / notes in <5s, any time of day
```

The **maintenance pass** (`daily-update` → `gardener.py`) keeps the index, `hot.md` and `_raw/`
lifecycle current. Run it explicitly with `/daily-update`, or let the 9 AM cron do it (set up
once via `daily-update`, *"set up the daily cron"*). To run the mechanics directly:

```bash
export OBSIDIAN_VAULT_PATH=/path/to/your/vault
python3 $OBSIDIAN_VAULT_PATH/_meta/scripts/gardener.py            # dry-run report
python3 $OBSIDIAN_VAULT_PATH/_meta/scripts/gardener.py --apply    # apply lifecycle changes
```

### Once a week (your retro day)

```bash
/weekly-retro             # interactive retro, primed by the week's data
```

It then runs the weekly maintenance tail automatically (cross-linker, hot-topics regeneration,
lint report, history ingests). On the last retro of the month it also triggers the monthly
review + brag compilation. The retro-day `morning-brief` adds a nudge to run it.

```bash
/weekly-retro annual [year]   # compile the year's retros into a self-assessment draft
```

### Occasionally

```bash
python3 $OBSIDIAN_VAULT_PATH/_meta/scripts/insights.py   # refresh graph insights → _insights.md
```

---

## Platform notes

- **macOS / Linux:** skills are symlinked to the installed package; a `pip upgrade` is picked
  up automatically. After upgrading obsidian-wiki, re-run `engramme-assist install` to re-seat
  the overlay copies.
- **Windows:** symlinks need Developer Mode/admin, so `install` defaults to **copy** mode
  (`--copy` forces it everywhere). After any `pip upgrade`, **re-run `engramme-assist install`**
  to resync. Maintenance scripts use the `python` launcher on Windows (`python3` on macOS/Linux).
  The 9 AM cron + terminal notification (`daily-update`) is macOS-only (launchd) for now.

## Privacy

Your real `profile.yml` and `state/channels.yml` (Slack IDs, colleague names, private channels)
are **gitignored** and never published. Only generic code + `*.example.yml` are tracked.

## Credit

Built on [`obsidian-wiki`](https://pypi.org/project/obsidian-wiki/) by Ar9av. MIT licensed.
</content>
</invoke>
