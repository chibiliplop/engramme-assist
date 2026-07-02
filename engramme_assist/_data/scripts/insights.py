#!/usr/bin/env python3
"""Insights — statistiques du graphe de liens du vault, écrites dans _insights.md.

Usage:
    python3 insights.py            # dry-run : JSON des stats sur stdout
    python3 insights.py --apply    # réécrit _insights.md (sections stats), en
                                   # préservant les sections rédigées par le LLM
                                   # (## Observations, ## Questions Worth Asking)
    python3 insights.py --json     # machine-readable : un seul objet JSON
                                   # (orphans, backlinks, broken_links, link_counts,
                                   # cooccurrence_candidates) pour wiki-lint /
                                   # cross-linker / wiki-synthesize

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
from itertools import combinations

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


def build_path_graph(pages):
    """Graphe de liens indexé par chemin relatif (pour la sortie --json).

    Renvoie (out_links, in_links, broken, tags_by_path) où out_links/in_links sont
    des dict path → set(path) et broken une liste de {source, target}."""
    name_to_path = {}
    for rel, fm, _ in pages:
        t = page_title(rel, fm)
        name_to_path[t.lower()] = rel
        name_to_path[os.path.splitext(os.path.basename(rel))[0].lower()] = rel
        for a in fm.get("aliases", []):
            name_to_path[a.lower()] = rel
    out_links = defaultdict(set)
    in_links = defaultdict(set)
    broken = []
    tags_by_path = {}
    for rel, fm, body in pages:
        tags_by_path[rel] = {t for t in fm.get("tags", []) if not t.startswith("visibility/")}
        for raw in set(LINK_RE.findall(body)):
            target = raw.strip().split("/")[-1]
            resolved = name_to_path.get(target.lower())
            if resolved is None:
                broken.append({"source": rel, "target": raw.strip()})
            elif resolved != rel:
                out_links[rel].add(resolved)
                in_links[resolved].add(rel)
    return out_links, in_links, broken, tags_by_path


def cooccurrence_candidates(out_links, tags_by_path, limit=30):
    """Paires de pages souvent co-citées / partageant des tags mais non reliées.

    Signal = 2 × (co-citations : pages tierces qui lient les deux) + (tags partagés).
    Exclut les paires déjà reliées dans un sens ou l'autre. Top `limit` par poids."""
    comention = defaultdict(int)
    for targets in out_links.values():
        for a, b in combinations(sorted(targets), 2):
            comention[(a, b)] += 1
    tag_index = defaultdict(list)
    for rel, tags in tags_by_path.items():
        for tag in tags:
            tag_index[tag].append(rel)
    tag_overlap = defaultdict(int)
    for paths in tag_index.values():
        if not (2 <= len(paths) <= 25):  # ignore singletons et tags trop génériques
            continue
        for a, b in combinations(sorted(paths), 2):
            tag_overlap[(a, b)] += 1

    def linked(a, b):
        return b in out_links.get(a, ()) or a in out_links.get(b, ())

    scored = {}
    for pair in set(comention) | set(tag_overlap):
        a, b = pair
        if linked(a, b):
            continue
        weight = 2 * comention.get(pair, 0) + tag_overlap.get(pair, 0)
        if weight > 0:
            scored[pair] = weight
    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"a": a, "b": b, "weight": w} for (a, b), w in ranked]


def json_report():
    pages = vault_pages()
    out_links, in_links, broken, tags_by_path = build_path_graph(pages)
    all_paths = [rel for rel, _, _ in pages]
    link_counts = {rel: {"in": len(in_links.get(rel, ())), "out": len(out_links.get(rel, ()))}
                   for rel in all_paths}
    return {
        "orphans": sorted(rel for rel in all_paths if link_counts[rel]["in"] == 0),
        "backlinks": {rel: link_counts[rel]["in"] for rel in all_paths},
        "broken_links": broken,
        "link_counts": link_counts,
        "cooccurrence_candidates": cooccurrence_candidates(out_links, tags_by_path),
    }


def main():
    if "--json" in sys.argv:
        print(json.dumps(json_report(), indent=1, ensure_ascii=False))
        return
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
