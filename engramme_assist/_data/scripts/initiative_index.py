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
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return (m.group(1), text[m.end():]) if m else (None, text)


def _strip_yaml_comment(value):
    quote = None
    escape = False
    for i, ch in enumerate(value):
        if escape:
            escape = False
            continue
        if quote:
            if quote == '"' and ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i]
    return value


def _strip_yaml_value(value):
    value = _strip_yaml_comment(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return value.strip()


def _inline_list_items(value):
    value = _strip_yaml_comment(value).strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1]
    items, buf = [], []
    quote = None
    escape = False
    for ch in inner:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if quote:
            if quote == '"' and ch == "\\":
                escape = True
                buf.append(ch)
            elif ch == quote:
                quote = None
                buf.append(ch)
            else:
                buf.append(ch)
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == ",":
            item = _strip_yaml_value("".join(buf))
            if item:
                items.append(item)
            buf = []
        else:
            buf.append(ch)
    item = _strip_yaml_value("".join(buf))
    if item:
        items.append(item)
    return items


def _key_value_lines(fm_text, key):
    lines = fm_text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}:\s*(.*?)\s*$", line)
        if m:
            yield i, m.group(1), lines


def _scalar(fm_text, key):
    for i, raw_val, lines in _key_value_lines(fm_text, key):
        val = _strip_yaml_value(raw_val)
        if val in (">", ">-", ">+", "|", "|-", "|+"):
            block = []
            for sub in lines[i + 1:]:
                if sub.strip() and not sub.startswith((" ", "\t")):
                    break
                block.append(sub.strip() if sub.strip() else "")
            return ("\n" if val.startswith("|") else " ").join(x for x in block if x).strip()
        return val
    return ""


def _list_field(fm_text, key):
    """Values of a frontmatter field in inline [..], block (- x), or scalar form."""
    for i, raw_val, lines in _key_value_lines(fm_text, key):
        inline = _inline_list_items(raw_val)
        if inline is not None:
            return inline
        if _strip_yaml_value(raw_val):
            val = _scalar(fm_text, key)
            return [val] if val else []
        vals = []
        for line in lines[i + 1:]:
            if not line.strip():
                continue
            if not line.startswith((" ", "\t")):
                break
            mm = re.match(r"^\s+-\s*(.*)$", line)
            if mm:
                val = _strip_yaml_value(mm.group(1))
                if val:
                    vals.append(val)
        return vals
    s = _scalar(fm_text, key)
    return [s] if s else []


def _strip_wikilink(s):
    s = s.strip().strip("'\"")
    m = re.match(r"^\[\[(.+?)\]\]$", s)
    if not m:
        return s
    target = m.group(1).split("|", 1)[0].split("#", 1)[0].strip()
    return target


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
        if fm_text and _scalar(fm_text, "category") == "projects":
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
