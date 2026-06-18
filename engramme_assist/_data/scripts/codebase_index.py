#!/usr/bin/env python3
"""Build a JSON index of codebases (entities/ tagged `codebase`) for session-flow matching.

Read-only. Consumed by claude-history-ingest and wiki-update to resolve a decoded
Claude-session repo path -> the codebase entity it belongs to (and, via initiative_index
reverse-lookup on `codebases:`, its initiatives). Stdlib only — matches
initiative_index.py / portfolio.py house style. build_index() is import-safe; env
resolution lives in main() so tests can call it with a tmp vault.

Reuses initiative_index's frontmatter/field parsers via a same-dir sys.path import
(the portfolio.py pattern) — no duplicated parsing logic.
"""
import json
import os
import re
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)
import initiative_index as ii  # noqa: E402  (frontmatter + field parsers; import-safe)

# A decoded Claude project dir inside a source path: .../projects/<dir>/<uuid>.jsonl
SOURCE_DIR_RE = re.compile(r"/projects/([^/]+)/[^/]+\.jsonl")
# Best-effort git path in the body.
REPO_BODY_RE = re.compile(r"\*\*Repo:\*\*\s*`([^`]+)`")
GITLAB_RE = re.compile(r"(gitlab[^\s`]+)")


def _source_dirs(fm_text):
    """Decoded ~/.claude/projects/<dir> names parsed from the sources: field (deduped)."""
    dirs = []
    for src in ii._list_field(fm_text, "sources"):
        m = SOURCE_DIR_RE.search(src)
        if m and m.group(1) not in dirs:
            dirs.append(m.group(1))
    return dirs


def _git_path(body):
    m = REPO_BODY_RE.search(body)
    if m:
        return m.group(1).strip()
    m = GITLAB_RE.search(body)
    return m.group(1).strip() if m else ""


def build_index(vault):
    entities_dir = os.path.join(vault, "entities")
    out = []
    if not os.path.isdir(entities_dir):
        return out
    for fname in sorted(os.listdir(entities_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(entities_dir, fname)
        try:
            text = open(fpath, encoding="utf-8").read()
        except OSError:
            continue
        fm_text, body = ii._frontmatter(text)
        if fm_text is None or "codebase" not in ii._list_field(fm_text, "tags"):
            continue
        out.append({
            "name": ii._scalar(fm_text, "title"),
            "path": os.path.relpath(fpath, vault),
            "aliases": ii._list_field(fm_text, "aliases"),
            "tags": ii._list_field(fm_text, "tags"),
            "source_dirs": _source_dirs(fm_text),
            "git_path": _git_path(body),
        })
    return out


def main():
    vault = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault:
        sys.exit("error: OBSIDIAN_VAULT_PATH is not set (resolve it via .env or ~/.obsidian-wiki/config).")
    print(json.dumps(build_index(vault), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
