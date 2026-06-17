#!/usr/bin/env python3
"""Portfolio — couche engagement + momentum par-dessus l'index initiative.

Usage:
    python3 portfolio.py                 # dry-run : snapshot JSON sur stdout
    python3 portfolio.py --apply         # écrit _meta/portfolio.json + projects/_portfolio.md
    python3 portfolio.py --skip-if-fresh # no-op (avec --apply) si aucun mouvement depuis le dernier run

Réutilise initiative_index.build_index() (scan projects/<slug>/, status/team/aliases…)
et ses helpers ; n'ajoute que : engagement (sélecteur), momentum dérivé
(max de updated / mtime sessions Claude / last_seen topics), stagnation par tier, rendu.
Stdlib only. Cœur pur séparé de l'IO pour la testabilité.
"""
import json
import os
import re
import sys
from datetime import date

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
import initiative_index as ii  # noqa: E402  (helpers + build_index ; import-safe)

DEFAULT_STALE = {"porteur": 10, "contributeur": 21, "observateur": 45}
ENGAGEMENTS = ("porteur", "contributeur", "observateur")
TIER_ICON = {"porteur": "🔴", "contributeur": "🟡", "observateur": "⚪"}


def norm_engagement(value):
    v = (value or "").strip().lower()
    return v if v in ENGAGEMENTS else None


def source_jsonl_paths(fm_text):
    """Chemins .jsonl sous `sources:` (réutilise ii._list_field), ~ expansé."""
    return [os.path.expanduser(s) for s in ii._list_field(fm_text, "sources") if s.endswith(".jsonl")]


def parse_date(s):
    if not s:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def latest_session_mtime(paths):
    dates = []
    for p in paths:
        try:
            dates.append(date.fromtimestamp(os.path.getmtime(p)))
        except OSError:
            continue
    return max(dates) if dates else None


def topic_last_seen(names, counter):
    """names: set de slugs/alias lowercase. Match exact, préfixe `name-`, ou inclusion."""
    best = None
    names = {n for n in names if n}
    for key, meta in counter.items():
        if not isinstance(meta, dict):
            continue
        k = key.lower()
        if any(k == n or k.startswith(n + "-") or n in k for n in names):
            d = parse_date(meta.get("last_seen"))
            if d and (best is None or d > best):
                best = d
    return best


def compute_last_movement(*candidates):
    ds = [d for d in candidates if d is not None]
    return max(ds) if ds else None


def is_stale(engagement, days, thresholds):
    t = thresholds.get(engagement)
    return t is not None and days is not None and days >= t


def _portfolio_block(profile_text):
    m = re.search(r"^portfolio:\s*\n((?:[ \t]+.*\n?)*)", profile_text or "", re.M)
    return m.group(1) if m else ""


def portfolio_enabled(profile_text):
    m = re.search(r"enabled:\s*(\w+)", _portfolio_block(profile_text))
    return (m.group(1).lower() not in ("false", "no", "0")) if m else True


def load_thresholds(profile_text):
    th, block = dict(DEFAULT_STALE), _portfolio_block(profile_text)
    for tier in DEFAULT_STALE:
        m = re.search(rf"{tier}:\s*(\d+)", block)
        if m:
            th[tier] = int(m.group(1))
    return th


def build_snapshot(projects, today, thresholds):
    """projects: dicts {title,path,engagement,status,last_movement:date|None,next}."""
    out = []
    for p in projects:
        lm = p["last_movement"]
        days = (today - lm).days if lm else None
        out.append({
            "title": p["title"], "path": p["path"],
            "engagement": p["engagement"], "status": p["status"],
            "last_movement": lm.isoformat() if lm else None,
            "days_stale": days,
            "is_stale": p["status"] == "active" and is_stale(p["engagement"], days, thresholds),
            "next": p.get("next"),
        })
    out.sort(key=lambda r: (r["days_stale"] is None, -(r["days_stale"] or 0)))
    stale = sorted((r for r in out if r["is_stale"]), key=lambda r: -(r["days_stale"] or 0))
    return {"generated": today.isoformat(), "projects": out, "stale": stale}


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def collect(vault, today, counter, thresholds):
    projects = []
    for e in ii.build_index(vault):
        fm_text, _ = ii._frontmatter(_read(os.path.join(vault, e["path"])) or "")
        fm_text = fm_text or ""
        eng = norm_engagement(ii._scalar(fm_text, "engagement"))
        if not eng:
            continue
        names = {e["slug"].lower(), (e["title"] or "").lower()}
        names |= {a.lower() for a in e.get("aliases", [])}
        lm = compute_last_movement(
            parse_date(ii._scalar(fm_text, "updated")),
            latest_session_mtime(source_jsonl_paths(fm_text)),
            topic_last_seen(names, counter),
        )
        projects.append({
            "title": e["title"] or e["slug"], "path": e["path"],
            "engagement": eng, "status": e.get("status") or "active",
            "last_movement": lm, "next": ii._scalar(fm_text, "next") or None,
        })
    return build_snapshot(projects, today, thresholds)


def render_md(snapshot):
    lines = [
        "---", "title: Portefeuille", "category: projects",
        "tags: [state, portfolio]", f"updated: {snapshot['generated']}", "---", "",
        "# 📁 Portefeuille de projets", "",
        f"*Vue dérivée — régénérée par `_meta/scripts/portfolio.py`. "
        f"Ne pas éditer à la main. ({snapshot['generated']})*", "",
        "| Initiative | Engagement | Statut | Jours sans mouvement | Next |",
        "|---|---|---|---|---|",
    ]
    for r in snapshot["projects"]:
        flag = " ⚠️" if r["is_stale"] else ""
        days = "—" if r["days_stale"] is None else str(r["days_stale"])
        lines.append(
            f"| [[{r['title']}]] | {TIER_ICON.get(r['engagement'], '')} {r['engagement']} "
            f"| {r['status']}{flag} | {days} | {r['next'] or ''} |")
    return "\n".join(lines) + "\n"


def _sig(snap):
    return [[r["path"], r["last_movement"], r["status"], r["engagement"], r["next"]]
            for r in snap.get("projects", [])]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    apply = "--apply" in argv
    skip_if_fresh = "--skip-if-fresh" in argv

    vault = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault:
        sys.exit("error: OBSIDIAN_VAULT_PATH is not set.")

    profile_text = _read(os.path.join(vault, "_meta", "profile.yml"))
    if not portfolio_enabled(profile_text):
        print(json.dumps({"disabled": True}, ensure_ascii=False))
        return

    counter = {}
    cpath = os.path.join(vault, "state", "topics-counter.json")
    if os.path.exists(cpath):
        try:
            with open(cpath, encoding="utf-8") as fh:
                counter = json.load(fh)
        except (ValueError, OSError):
            counter = {}

    snapshot = collect(vault, date.today(), counter, load_thresholds(profile_text))

    if apply and skip_if_fresh:
        prev = _read(os.path.join(vault, "_meta", "portfolio.json"))
        if prev:
            try:
                if _sig(json.loads(prev)) == _sig(snapshot):
                    print(json.dumps({"skipped": True}, ensure_ascii=False))
                    return
            except ValueError:
                pass

    if apply:
        with open(os.path.join(vault, "_meta", "portfolio.json"), "w", encoding="utf-8") as fh:
            json.dump(snapshot, fh, ensure_ascii=False, indent=1)
        with open(os.path.join(vault, "projects", "_portfolio.md"), "w", encoding="utf-8") as fh:
            fh.write(render_md(snapshot))
    print(json.dumps(snapshot, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
