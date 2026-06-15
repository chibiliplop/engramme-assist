#!/usr/bin/env python3
"""Insights — statistiques du graphe de liens du vault, écrites dans _insights.md.

Usage:
    python3 insights.py            # dry-run : JSON des stats sur stdout
    python3 insights.py --apply    # réécrit _insights.md (sections stats), en
                                   # préservant les sections rédigées par le LLM
                                   # (## Observations, ## Questions Worth Asking)

La partie mécanique (hubs, orphans, dead-ends, liens cassés, distribution) est
calculée ici ; l'interprétation (Observations, Questions) reste au LLM — le skill
qui invoque ce script complète ces deux sections après coup si elles sont vides.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gardener import VAULT, vault_pages, page_title  # noqa: E402

TODAY = date.today()
LLM_SECTIONS = ["## Observations", "## Questions Worth Asking"]
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def build_graph():
    pages = vault_pages()
    name_to_title = {}
    for rel, fm, _ in pages:
        t = page_title(rel, fm)
        name_to_title[t.lower()] = t
        name_to_title[os.path.splitext(os.path.basename(rel))[0].lower()] = t
        for a in fm.get("aliases", []):
            name_to_title[a.lower()] = t
    titles = {page_title(rel, fm) for rel, fm, _ in pages}
    out_links = defaultdict(set)
    in_links = defaultdict(set)
    broken = defaultdict(set)  # cible inexistante → pages qui la pointent
    cat_of = {page_title(rel, fm): rel.split("/")[0] for rel, fm, _ in pages}
    for rel, fm, body in pages:
        src = page_title(rel, fm)
        for raw in set(LINK_RE.findall(body)):
            target = raw.strip().split("/")[-1]
            resolved = name_to_title.get(target.lower())
            if resolved is None:
                broken[raw.strip()].add(src)
            elif resolved != src:
                out_links[src].add(resolved)
                in_links[resolved].add(src)
    return pages, titles, out_links, in_links, broken, cat_of


def main():
    apply = "--apply" in sys.argv
    pages, titles, out_links, in_links, broken, cat_of = build_graph()
    total_links = sum(len(v) for v in out_links.values())

    degree = {t: len(in_links.get(t, ())) + len(out_links.get(t, ())) for t in titles}
    hubs = sorted(titles, key=lambda t: -degree[t])[:10]
    orphans = sorted(t for t in titles if degree[t] == 0)
    dead_ends = sorted(t for t in titles
                       if in_links.get(t) and not out_links.get(t))
    # bridges : pages dont les voisins couvrent le plus de catégories distinctes
    def cat_spread(t):
        cats = {cat_of.get(n, "?") for n in (in_links.get(t, set()) | out_links.get(t, set()))}
        return len(cats)
    bridges = sorted((t for t in titles if degree[t] >= 4),
                     key=lambda t: (-cat_spread(t), -degree[t]))[:5]
    by_cat = defaultdict(int)
    for rel, fm, _ in pages:
        by_cat[rel.split("/")[0]] += 1

    stats = {
        "date": str(TODAY), "pages": len(pages), "links": total_links,
        "orphans": len(orphans), "dead_ends": len(dead_ends),
        "broken_targets": len(broken),
        "hubs": [{"title": t, "in": len(in_links.get(t, ())), "out": len(out_links.get(t, ()))}
                 for t in hubs],
    }
    if not apply:
        print(json.dumps(stats, indent=1, ensure_ascii=False))
        return

    # Préserver les sections LLM existantes
    insights_path = os.path.join(VAULT, "_insights.md")
    preserved = ""
    if os.path.exists(insights_path):
        old = open(insights_path, encoding="utf-8").read()
        for sec in LLM_SECTIONS:
            m = re.search(rf"^{re.escape(sec)}\n(.*?)(?=^## |\Z)", old, re.M | re.DOTALL)
            if m and m.group(1).strip():
                preserved += f"{sec}\n{m.group(1).rstrip()}\n\n"

    out = [f"# Wiki Insights — {TODAY}", "",
           "*Stats générées par `_meta/scripts/insights.py` — sections Observations/Questions rédigées par le skill.*", "",
           "## Vault Overview", "",
           f"- **{len(pages)} pages**, **{total_links} liens** internes",
           "- Distribution : " + " · ".join(f"{d}: {n}" for d, n in sorted(by_cat.items(), key=lambda x: -x[1])),
           f"- {len(orphans)} orphelins · {len(dead_ends)} dead-ends · {len(broken)} cibles de liens cassés", "",
           "## Anchor Pages (top 10 hubs)", "",
           "| Page | Entrants | Sortants |", "|---|---|---|"]
    out += [f"| [[{t}]] | {len(in_links.get(t, ()))} | {len(out_links.get(t, ()))} |" for t in hubs]
    out += ["", "## Bridge Pages (top 5 — connecteurs inter-catégories)", ""]
    out += [f"- [[{t}]] — {cat_spread(t)} catégories reliées, degré {degree[t]}" for t in bridges]
    out += ["", "## Orphan Pages (no links in or out)", ""]
    out += [f"- [[{t}]]" for t in orphans] or ["- (aucun)"]
    out += ["", "## Dead-End Pages (incoming but no outgoing links)", ""]
    out += [f"- [[{t}]]" for t in dead_ends] or ["- (aucun)"]
    out += ["", "## Broken Links (targets that don't exist)", ""]
    out += [f"- `[[{tgt}]]` ← {', '.join(sorted(srcs)[:3])}{' …' if len(srcs) > 3 else ''}"
            for tgt, srcs in sorted(broken.items())] or ["- (aucun)"]
    out += ["", preserved.rstrip() or "## Observations\n\n*(à compléter par le skill)*\n\n## Questions Worth Asking\n\n*(à compléter par le skill)*"]
    open(insights_path, "w", encoding="utf-8").write("\n".join(out).rstrip() + "\n")
    print(json.dumps(stats, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
