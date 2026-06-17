#!/usr/bin/env python3
"""Build a JSON index of initiatives (projects/) for ambient-topic matching.

Read-only. Consumed by wiki-ingest (placement) and morning-brief (gate signal).
Stdlib only — matches gardener.py / insights.py house style. build_index() is
import-safe; env resolution lives in main() so tests can call it with a tmp vault.
"""
import json
import os
import re
import sys

JIRA_RE = re.compile(r"\b([A-Z]{2,}-\d+)\b")


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return (m.group(1), text[m.end():]) if m else (None, text)


def _scalar(fm_text, key):
    m = re.search(rf"^{key}:\s*['\"]?(.+?)['\"]?\s*$", fm_text, re.M)
    return m.group(1).strip() if m else ""


def _list_field(fm_text, key):
    """Values of a frontmatter field in inline [..], block (- x), or scalar form."""
    m = re.search(rf"^{key}:\s*\[(.+)\]\s*$", fm_text, re.M)
    if m:
        return [v.strip().strip("'\"") for v in m.group(1).split(",") if v.strip()]
    if re.search(rf"^{key}:\s*$", fm_text, re.M):
        vals, in_block = [], False
        for line in fm_text.split("\n"):
            if re.match(rf"^{key}:\s*$", line):
                in_block = True
            elif in_block:
                mm = re.match(r"^\s+-\s*(.+)$", line)
                if mm:
                    vals.append(mm.group(1).strip().strip("'\""))
                else:
                    in_block = False
        return vals
    s = _scalar(fm_text, key)
    return [s] if s else []


def _strip_wikilink(s):
    s = s.strip().strip("'\"")
    m = re.match(r"^\[\[(.+?)\]\]$", s)
    return m.group(1) if m else s


def _find_hub(pdir):
    """Top-level .md in pdir whose frontmatter category is `projects`."""
    for fname in sorted(os.listdir(pdir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(pdir, fname)
        try:
            text = open(fpath, encoding="utf-8").read()
        except OSError:
            continue
        fm_text, body = _frontmatter(text)
        if fm_text and re.search(r"^category:\s*projects\s*$", fm_text, re.M):
            return fpath, fm_text, body
    return None, None, None


def build_index(vault):
    projects_dir = os.path.join(vault, "projects")
    out = []
    if not os.path.isdir(projects_dir):
        return out
    for slug in sorted(os.listdir(projects_dir)):
        pdir = os.path.join(projects_dir, slug)
        if not os.path.isdir(pdir):
            continue
        hub_path, hub_fm, hub_body = _find_hub(pdir)
        if hub_fm is None:
            print(f"skip: no hub (category: projects) in projects/{slug}", file=sys.stderr)
            continue
        jira = _list_field(hub_fm, "jira")
        if not jira:  # current primary source: provenance grep in frontmatter
            jira = sorted(set(JIRA_RE.findall(hub_fm)))
        out.append({
            "slug": slug,
            "path": os.path.relpath(hub_path, vault),
            "title": _scalar(hub_fm, "title"),
            "aliases": _list_field(hub_fm, "aliases"),
            "team": [_strip_wikilink(t) for t in _list_field(hub_fm, "team")],
            "codebases": [_strip_wikilink(c) for c in _list_field(hub_fm, "codebases")],
            "jira_keys": jira,
            "status": _scalar(hub_fm, "status") or "active",
        })
    return out


def main():
    vault = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault:
        sys.exit("error: OBSIDIAN_VAULT_PATH is not set (resolve it via .env or ~/.obsidian-wiki/config).")
    print(json.dumps(build_index(vault), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
