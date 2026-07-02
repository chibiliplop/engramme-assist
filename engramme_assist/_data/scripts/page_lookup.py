#!/usr/bin/env python3
"""page_lookup — write-time duplicate gate + vault-wide near-duplicate finder.

Le portail de déduplication à l'écriture (cf. AGENTS.md § Ingest discipline,
UPDATE-vs-ADD) : avant de créer une page, un skill interroge ce script pour savoir
si une page couvrant déjà le même titre/alias existe. En mode --pairs il liste
toutes les quasi-duplications du vault (moteur pour wiki-dedup).

Ne lit que le frontmatter (title:, aliases:) — rapide. Similarité :
difflib.SequenceMatcher sur des chaînes normalisées (minuscules, accents retirés
via unicodedata, ponctuation/espaces compactés).

Usage:
    python3 page_lookup.py --title "X" [--aliases "a,b"] [--threshold 0.78]
        → JSON [{path, title, score}] des pages dont le titre/alias matche, tri desc.
    python3 page_lookup.py --pairs [--threshold 0.82]
        → JSON [{path_a, path_b, score}] des paires quasi-dupliquées du vault.

Racine du vault : $OBSIDIAN_VAULT_PATH ou --vault. Exclut _archives/ _raw/
journal/ retros/ meetings/ (et les dossiers non-contenu).
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from difflib import SequenceMatcher

EXCLUDE = {"_archives", "_raw", "journal", "retros", "meetings", "_meta",
           ".obsidian", ".git", "node_modules", "wiki-export", "state",
           ".claude", ".skills", "_templates"}
TITLE_DEFAULT_THRESHOLD = 0.78
PAIRS_DEFAULT_THRESHOLD = 0.82


def normalize(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_aliases(fm_text):
    am = re.search(r"^aliases:\s*\[(.*?)\]", fm_text, re.M)
    if am:
        return [a.strip().strip("'\"") for a in am.group(1).split(",") if a.strip()]
    aliases = []
    if re.search(r"^aliases:\s*$", fm_text, re.M):
        in_al = False
        for line in fm_text.split("\n"):
            if re.match(r"^aliases:\s*$", line):
                in_al = True
            elif in_al:
                m = re.match(r"^\s+-\s*(.+)$", line)
                if m:
                    aliases.append(m.group(1).strip().strip("'\""))
                else:
                    in_al = False
    return aliases


def read_names(path):
    """(title, [aliases]) depuis le frontmatter ; title = basename si absent."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None, []
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    fm_text = m.group(1) if m else ""
    tm = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", fm_text, re.M)
    title = tm.group(1).strip() if tm else os.path.splitext(os.path.basename(path))[0]
    return title, parse_aliases(fm_text)


def scan_pages(vault):
    """[(rel, title, [aliases])] pour toutes les pages de contenu."""
    pages = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in EXCLUDE and not d.startswith(".")]
        if os.path.abspath(root) == os.path.abspath(vault):
            continue  # ignore les artefacts racine (index.md, hot.md, log.md, …)
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            title, aliases = read_names(path)
            if title is None:
                continue
            rel = os.path.relpath(path, vault).replace(os.sep, "/")
            pages.append((rel, title, aliases))
    return pages


def norm_names(title, aliases):
    seen = [normalize(title)] + [normalize(a) for a in aliases]
    return [n for n in dict.fromkeys(seen) if n]  # dédup, sans les vides


def best_score(names_a, names_b):
    """Ratio SequenceMatcher max entre n'importe quel nom normalisé de A et de B."""
    best = 0.0
    for na in names_a:
        for nb in names_b:
            r = SequenceMatcher(None, na, nb).ratio()
            if r > best:
                best = r
    return best


def cmd_title(vault, title, aliases, threshold):
    query = norm_names(title, aliases)
    results = []
    for rel, ptitle, paliases in scan_pages(vault):
        score = best_score(query, norm_names(ptitle, paliases))
        if score >= threshold:
            results.append({"path": rel, "title": ptitle, "score": round(score, 4)})
    results.sort(key=lambda r: (-r["score"], r["path"]))
    return results


def cmd_pairs(vault, threshold):
    pages = [(rel, ptitle, norm_names(ptitle, paliases))
             for rel, ptitle, paliases in scan_pages(vault)]
    out = []
    for i in range(len(pages)):
        rel_a, _, names_a = pages[i]
        for j in range(i + 1, len(pages)):
            rel_b, _, names_b = pages[j]
            score = best_score(names_a, names_b)
            if score >= threshold:
                out.append({"path_a": rel_a, "path_b": rel_b, "score": round(score, 4)})
    out.sort(key=lambda r: (-r["score"], r["path_a"], r["path_b"]))
    return out


def main():
    ap = argparse.ArgumentParser(description="Vault page duplicate gate / near-dup finder.")
    ap.add_argument("--title")
    ap.add_argument("--aliases", default="")
    ap.add_argument("--pairs", action="store_true")
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--vault")
    args = ap.parse_args()

    vault = args.vault or os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault:
        sys.exit("error: set --vault or OBSIDIAN_VAULT_PATH")
    if not os.path.isdir(vault):
        sys.exit("error: vault not found: %s" % vault)

    if args.pairs:
        threshold = args.threshold if args.threshold is not None else PAIRS_DEFAULT_THRESHOLD
        print(json.dumps(cmd_pairs(vault, threshold), indent=1, ensure_ascii=False))
    elif args.title:
        threshold = args.threshold if args.threshold is not None else TITLE_DEFAULT_THRESHOLD
        aliases = [a.strip() for a in args.aliases.split(",") if a.strip()]
        print(json.dumps(cmd_title(vault, args.title, aliases, threshold),
                         indent=1, ensure_ascii=False))
    else:
        ap.error('provide --title "X" or --pairs')


if __name__ == "__main__":
    main()
