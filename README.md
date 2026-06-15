# engramme-assist

A profile-driven **overlay** for [`obsidian-wiki`](https://pypi.org/project/obsidian-wiki/)
(by Ar9av) — keeps the upstream skill framework, adds a config **profile** so personal
skills (`morning-brief`, `weekly-retro`, `jot`, `daily-update`) read your identity, sources
and scoring from a private YAML instead of hardcoding them. The skill code stays generic and
shareable; your real values live in a gitignored profile.

## What it adds

- **Profile** (`~/.obsidian-wiki/profile.yml` global + `$VAULT/_meta/profile.yml`, merged) —
  identity, role, active sources, model tiers, brief scoring grid.
- **`wiki-init`** (orchestrator: runs `wiki-setup` then `wiki-profile`) and **`wiki-profile`**.
- **`jot`, `morning-brief`, `weekly-retro`, `daily-update`** — parametrized via `{{profile.*}}`.
- **`gardener.py` / `insights.py`** — the programmatic-first daily-maintenance scripts.
- **`AGENTS.generic.md`** — framework conventions + profile-loading, no personal values.

## Install

```bash
pip install engramme-assist   # pulls obsidian-wiki (pinned in UPSTREAM) as a dependency
# or, from a checkout: pip install -e .
engramme-assist install --vault /path/to/your/vault
# or: python -m engramme_assist install --vault /path/to/your/vault
```

The overlay's skills and scripts ship inside the package (`engramme_assist/_data/`), so a
plain `pip install` is self-contained — no clone required.

`install` delegates the base install to `obsidian-wiki setup`, then lays this overlay's six
skills on top, and drops `AGENTS.generic.md` / `profile.example.yml` / the gardener scripts
into the vault (non-destructively — never clobbers an existing file).

Then, in your agent: say **"set up my wiki"** → `wiki-init` (runs setup, then fills your profile).

## Platform notes

- **macOS / Linux:** skills are symlinked to the installed package; `pip upgrade` is picked up
  automatically. After upgrading obsidian-wiki, re-run `engramme-assist install` to re-seat the
  overlay copies.
- **Windows:** symlinks need Developer Mode/admin, so `install` defaults to **copy** mode
  (`--copy` forces it everywhere). After any `pip upgrade`, **re-run `engramme-assist install`**
  to resync. The maintenance scripts use the `python` launcher on Windows (`python3` on
  macOS/Linux).

## Privacy

Your real `profile.yml` and `state/channels.yml` (Slack IDs, colleague names, private channels)
are **gitignored** and never published. Only generic code + `*.example.yml` are tracked.

## Credit

Built on [`obsidian-wiki`](https://pypi.org/project/obsidian-wiki/) by Ar9av. MIT licensed.
