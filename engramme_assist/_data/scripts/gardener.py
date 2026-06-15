#!/usr/bin/env python3
"""Gardener — mécanique du cycle de vie du vault (cf. AGENTS.md § Data Lifecycle).

Usage:
    python3 gardener.py                  # dry-run : rapport JSON, aucune écriture
    python3 gardener.py --apply          # applique : TTL _raw/, archivage, promotions, rebuild index
    python3 gardener.py --check          # validations post-run (remplace impl-validator)
    python3 gardener.py --skip-if-fresh  # exit 0 + {"skipped": true} si rien n'a bougé depuis .last_update

Sortie : JSON sur stdout. Le skill daily-update lance ce script puis interprète le rapport.
"""
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta

VAULT = os.environ.get("OBSIDIAN_VAULT_PATH")
if not VAULT:
    sys.exit("error: OBSIDIAN_VAULT_PATH is not set (resolve it via .env or ~/.obsidian-wiki/config).")
TODAY = date.today()
CATEGORY_DIRS = ["concepts", "entities", "skills", "references", "synthesis", "projects"]
ALL_CONTENT_DIRS = CATEGORY_DIRS + ["journal", "retros", "brag", "decisions"]
INDEX_SECTIONS = [  # ordre des sections de index.md (catégorie frontmatter → titre de section)
    ("entities", "Entities"), ("projects", "Projects"), ("concepts", "Concepts"),
    ("skills", "Skills"), ("references", "References"), ("_notes", "Notes"),
    ("retros", "Retros"), ("brag", "Brag"), ("journal", "Journal"), ("synthesis", "Synthesis"),
]
EXCLUDED = {"_archives", "_raw", "_meta", ".claude", ".obsidian", ".skills",
            "node_modules", "wiki-export", "state"}
RAW_PROMOTED_TTL_DAYS = 7
RAW_UNPROMOTED_FLAG_DAYS = 14
ARCHIVE_GRACE_DAYS = 60


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None, ""
    fm_text, body = m.group(1), text[m.end():]
    fm = {}
    for key in ("title", "category", "summary", "lifecycle", "review_due",
                "last_verified", "updated", "base_confidence", "type"):
        km = re.search(rf"^{key}:\s*['\"]?(.+?)['\"]?\s*$", fm_text, re.M)
        if km:
            fm[key] = km.group(1).strip()
    # tags : forme inline ou bloc
    tags = []
    tm = re.search(r"^tags:\s*\[(.*?)\]", fm_text, re.M)
    if tm:
        tags = [t.strip() for t in tm.group(1).split(",")]
    elif re.search(r"^tags:\s*$", fm_text, re.M):
        in_tags = False
        for line in fm_text.split("\n"):
            if re.match(r"^tags:\s*$", line):
                in_tags = True
            elif in_tags:
                t = re.match(r"^\s+-\s*(.+)$", line)
                if t:
                    tags.append(t.group(1).strip())
                else:
                    in_tags = False
    fm["tags"] = tags
    # aliases (pour la résolution de liens)
    aliases = []
    am = re.search(r"^aliases:\s*\[(.*?)\]", fm_text, re.M)
    if am:
        aliases = [a.strip().strip("'\"") for a in am.group(1).split(",")]
    elif re.search(r"^aliases:\s*$", fm_text, re.M):
        in_al = False
        for line in fm_text.split("\n"):
            if re.match(r"^aliases:\s*$", line):
                in_al = True
            elif in_al:
                a = re.match(r"^\s+-\s*(.+)$", line)
                if a:
                    aliases.append(a.group(1).strip().strip("'\""))
                else:
                    in_al = False
    fm["aliases"] = aliases
    # sources : compter les entrées
    n_sources = 0
    sm = re.search(r"^sources:\s*\[(.*?)\]", fm_text, re.M)
    if sm:
        n_sources = len([s for s in sm.group(1).split(",") if s.strip()])
    elif re.search(r"^sources:\s*$", fm_text, re.M):
        in_src = False
        for line in fm_text.split("\n"):
            if re.match(r"^sources:\s*$", line):
                in_src = True
            elif in_src:
                if re.match(r"^\s+-\s+", line):
                    n_sources += 1
                else:
                    in_src = False
    fm["n_sources"] = n_sources
    fm["_fm_text"] = fm_text
    return fm, body


def vault_pages():
    """Toutes les pages de contenu : [(path_relatif, fm, body)]."""
    pages = []
    for d in ALL_CONTENT_DIRS:
        root_dir = os.path.join(VAULT, d)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [x for x in dirs if x not in EXCLUDED]
            for name in sorted(files):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                fm, body = parse_frontmatter(text)
                # Normalise en "/" : os.path.relpath renvoie "\" sous Windows,
                # ce qui casserait tous les rel.split("/") / startswith("entities/").
                rel = os.path.relpath(path, VAULT).replace(os.sep, "/")
                pages.append((rel, fm or {}, body))
    return pages


def parse_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def page_title(rel, fm):
    return fm.get("title") or os.path.splitext(os.path.basename(rel))[0]


def inbound_link_counts(pages):
    """title/alias (lowercase) → nb de liens entrants depuis d'autres pages."""
    name_to_title = {}
    for rel, fm, _ in pages:
        t = page_title(rel, fm)
        name_to_title[t.lower()] = t
        name_to_title[os.path.splitext(os.path.basename(rel))[0].lower()] = t
        for a in fm.get("aliases", []):
            name_to_title[a.lower()] = t
    counts = {page_title(rel, fm): 0 for rel, fm, _ in pages}
    link_re = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    for rel, fm, body in pages:
        src_title = page_title(rel, fm)
        for target in set(link_re.findall(body)):
            target = target.strip().split("/")[-1]
            resolved = name_to_title.get(target.lower())
            if resolved and resolved != src_title:
                counts[resolved] = counts.get(resolved, 0) + 1
    return counts


def raw_ttl(apply, manifest_text, entities_aliases):
    deleted, flagged, archived = [], [], []
    flag_path = os.path.join(VAULT, "state", ".raw_flagged.json")
    prev_flagged = set()
    if os.path.exists(flag_path):
        try:
            prev_flagged = set(json.load(open(flag_path)))
        except (json.JSONDecodeError, OSError):
            prev_flagged = set()
    raw_dir = os.path.join(VAULT, "_raw")
    if not os.path.isdir(raw_dir):
        return {"deleted": [], "flagged": [], "archived": []}
    now_flagged = set()
    for root, _, files in os.walk(raw_dir):
        for name in sorted(files):
            if not name.endswith(".md") or name == "inbox.md":
                continue  # inbox.md est permanent (canal de capture /jot)
            path = os.path.join(root, name)
            rel = os.path.relpath(path, VAULT).replace(os.sep, "/")
            stem = os.path.splitext(name)[0]
            age = (TODAY - date.fromtimestamp(os.path.getmtime(path))).days
            promoted = stem in manifest_text or stem.lower() in entities_aliases
            if promoted and age > RAW_PROMOTED_TTL_DAYS:
                deleted.append(rel)
                if apply:
                    os.remove(path)
            elif not promoted and age > RAW_UNPROMOTED_FLAG_DAYS:
                if rel in prev_flagged:
                    dest_dir = os.path.join(VAULT, "_archives", "raw", TODAY.strftime("%Y-%m"))
                    archived.append(rel)
                    if apply:
                        os.makedirs(dest_dir, exist_ok=True)
                        shutil.move(path, os.path.join(dest_dir, name))
                else:
                    flagged.append(rel)
                    now_flagged.add(rel)
    if apply:
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        json.dump(sorted(now_flagged), open(flag_path, "w"), indent=1)
    return {"deleted": deleted, "flagged": flagged, "archived": archived}


def review_audit(pages):
    overdue = []
    for rel, fm, _ in pages:
        due = parse_date(fm.get("review_due"))
        if due and due < TODAY:
            overdue.append({"page": rel, "title": page_title(rel, fm),
                            "overdue_days": (TODAY - due).days,
                            "lifecycle": fm.get("lifecycle", "")})
    overdue.sort(key=lambda x: -x["overdue_days"])
    return overdue


def archive_dead_pages(pages, overdue, inbound, apply):
    archived = []
    overdue_by_page = {o["page"]: o for o in overdue}
    for rel, fm, _ in pages:
        o = overdue_by_page.get(rel)
        if not o or o["overdue_days"] < ARCHIVE_GRACE_DAYS:
            continue
        top = rel.split("/")[0]
        if top not in CATEGORY_DIRS or fm.get("lifecycle") == "verified":
            continue
        if inbound.get(page_title(rel, fm), 0) > 0:
            continue
        dest_dir = os.path.join(VAULT, "_archives", TODAY.strftime("%Y-%m"))
        archived.append(rel)
        if apply:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(os.path.join(VAULT, rel), os.path.join(dest_dir, os.path.basename(rel)))
    return archived


def auto_promote(pages, apply):
    promoted = []
    for rel, fm, body in pages:
        if rel.split("/")[0] not in CATEGORY_DIRS or fm.get("lifecycle") != "draft":
            continue
        try:
            conf = float(fm.get("base_confidence", 0))
        except ValueError:
            continue
        if conf < 0.8 or fm.get("n_sources", 0) < 2:
            continue
        if "^[inferred]" in body or "^[ambiguous]" in body:
            continue
        promoted.append(rel)
        if apply:
            path = os.path.join(VAULT, rel)
            text = open(path, encoding="utf-8").read()
            text = re.sub(r"^lifecycle:\s*draft\s*$", "lifecycle: reviewed", text, count=1, flags=re.M)
            open(path, "w", encoding="utf-8").write(text)
    return promoted


def truncate(s, n=110):
    s = (s or "").strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def rebuild_index(pages, apply):
    by_section = {key: [] for key, _ in INDEX_SECTIONS}
    for rel, fm, _ in pages:
        top = rel.split("/")[0]
        cat = fm.get("category", "")
        if top in ("retros", "brag", "journal"):
            key = top
        elif cat in by_section:
            key = cat
        elif top in by_section:
            key = top
        else:
            key = "_notes"
        line = f"- [[{page_title(rel, fm)}]]"
        if fm.get("summary"):
            line += f" — {truncate(fm['summary'])}"
        by_section[key].append((page_title(rel, fm).lower(), line))
    out = ["---", "title: Wiki Index", "aliases:", "  - Wiki Index", "---", "",
           "# Wiki Index", "",
           f"*This index is automatically maintained. Last updated: {TODAY} (gardener rebuild)*", ""]
    total = 0
    for key, heading in INDEX_SECTIONS:
        entries = by_section[key]
        if not entries:
            continue
        out.append(f"## {heading}")
        out.append("")
        if key == "journal":  # antichronologique pour le journal
            entries.sort(key=lambda x: x[0], reverse=True)
        else:
            entries.sort(key=lambda x: x[0])
        out.extend(line for _, line in entries)
        out.append("")
        total += len(entries)
    content = "\n".join(out).rstrip() + "\n"
    if apply:
        open(os.path.join(VAULT, "index.md"), "w", encoding="utf-8").write(content)
    return total


def check():
    """Validations post-run — remplace l'agent impl-validator."""
    results, ok = {}, True
    pages = vault_pages()
    index_text = open(os.path.join(VAULT, "index.md"), encoding="utf-8").read()
    index_links = len(re.findall(r"^- \[\[", index_text, re.M))
    results["index_count_matches_vault"] = (index_links >= len(pages),
                                            f"index={index_links} vault={len(pages)}")
    hot_fm, _ = parse_frontmatter(open(os.path.join(VAULT, "hot.md"), encoding="utf-8").read())
    hot_updated = parse_date((hot_fm or {}).get("updated", ""))
    results["hot_md_fresh"] = (hot_updated is not None and (TODAY - hot_updated).days <= 2,
                               f"hot.md updated={hot_updated}")
    missing_rd = [rel for rel, fm, _ in pages
                  if rel.split("/")[0] in CATEGORY_DIRS and not fm.get("review_due")]
    results["review_due_coverage"] = (len(missing_rd) == 0,
                                      f"{len(missing_rd)} pages sans review_due" +
                                      (f" (ex: {missing_rd[:3]})" if missing_rd else ""))
    no_fm = [rel for rel, fm, _ in pages if not fm]
    results["frontmatter_present"] = (len(no_fm) == 0, f"{len(no_fm)} pages sans frontmatter")
    ok = all(v[0] for v in results.values())
    return {"ok": ok, "checks": {k: {"pass": v[0], "detail": v[1]} for k, v in results.items()}}


def main():
    apply = "--apply" in sys.argv
    if "--check" in sys.argv:
        report = check()
        print(json.dumps(report, indent=1, ensure_ascii=False))
        sys.exit(0 if report["ok"] else 1)

    if "--skip-if-fresh" in sys.argv:
        import hashlib
        vault_id = hashlib.md5((VAULT + "\n").encode()).hexdigest()[:8]
        lu_path = os.path.expanduser(f"~/.obsidian-wiki/state/{vault_id}/.last_update")
        if os.path.exists(lu_path):
            last_update = float(open(lu_path).read().strip())
            newest = 0.0
            for d in ALL_CONTENT_DIRS + ["_raw"]:
                root_dir = os.path.join(VAULT, d)
                for root, dirs, files in os.walk(root_dir) if os.path.isdir(root_dir) else []:
                    for name in files:
                        if name.endswith(".md"):
                            newest = max(newest, os.path.getmtime(os.path.join(root, name)))
            if newest < last_update:
                print(json.dumps({"skipped": True,
                                  "reason": "aucune page modifiée depuis le dernier run"}))
                return

    manifest_path = os.path.join(VAULT, ".manifest.json")
    manifest_text = open(manifest_path, encoding="utf-8").read() if os.path.exists(manifest_path) else ""
    pages = vault_pages()
    entities_aliases = set()
    for rel, fm, _ in pages:
        if rel.startswith("entities/"):
            entities_aliases.update(a.lower() for a in fm.get("aliases", []))

    inbound = inbound_link_counts(pages)
    overdue = review_audit(pages)
    # Backlog de vérification humaine (wiki-verify) : claims inférés/ambigus restants
    verify_backlog = []
    for rel, fm, body in pages:
        if rel.split("/")[0] not in CATEGORY_DIRS:
            continue
        n = body.count("^[inferred]") + body.count("^[ambiguous]")
        if n:
            verify_backlog.append({"page": rel, "claims": n})
    verify_backlog.sort(key=lambda x: -x["claims"])
    raw = raw_ttl(apply, manifest_text, entities_aliases)
    archived = archive_dead_pages(pages, overdue, inbound, apply)
    promoted = auto_promote(pages, apply)
    if apply and (archived or promoted):
        pages = vault_pages()  # re-scan après mutations
    index_total = rebuild_index(pages, apply)

    print(json.dumps({
        "mode": "apply" if apply else "dry-run",
        "date": str(TODAY),
        "pages_total": len(pages),
        "index_rebuilt": index_total,
        "raw": raw,
        "review_overdue_count": len(overdue),
        "review_overdue_top10": overdue[:10],
        "verify_backlog_pages": len(verify_backlog),
        "verify_backlog_claims": sum(v["claims"] for v in verify_backlog),
        "verify_backlog_top5": verify_backlog[:5],
        "archived": archived,
        "promoted": promoted,
        "orphans": sorted(t for t, c in inbound.items() if c == 0)[:20],
    }, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
