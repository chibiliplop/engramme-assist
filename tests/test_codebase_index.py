import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "engramme_assist" / "_data" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import codebase_index  # noqa: E402  (initiative_index imported internally from same dir)


def _entity(vault: Path, fname: str, frontmatter: str, body: str = "") -> None:
    edir = vault / "entities"
    edir.mkdir(parents=True, exist_ok=True)
    (edir / fname).write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def _by_name(index, name):
    return next(e for e in index if e["name"] == name)


def test_source_dirs_parsed_from_block_sources(tmp_path):
    _entity(
        tmp_path, "engramme-assist.md",
        "title: Engramme Assist\n"
        "category: entities\n"
        "tags: [codebase, wiki]\n"
        "aliases:\n  - engramme-assist\n  - engramme\n"
        "sources:\n"
        "  - ~/.claude/projects/-Users-tnabet-Dev-tools-engramme-assist/a1.jsonl\n"
        "  - ~/.claude/projects/-Users-tnabet-Documents-wiki/b2.jsonl",
        body="# Engramme Assist\n\n**Repo:** `/Users/tnabet/Dev/tools/engramme-assist`.",
    )
    e = _by_name(codebase_index.build_index(str(tmp_path)), "Engramme Assist")
    assert e["source_dirs"] == [
        "-Users-tnabet-Dev-tools-engramme-assist", "-Users-tnabet-Documents-wiki",
    ]
    assert e["aliases"] == ["engramme-assist", "engramme"]
    assert "codebase" in e["tags"]
    assert e["git_path"] == "/Users/tnabet/Dev/tools/engramme-assist"
    assert e["path"] == "entities/engramme-assist.md"


def test_source_dirs_inline_and_dedup(tmp_path):
    _entity(
        tmp_path, "x.md",
        "title: X\ncategory: entities\ntags: [codebase]\n"
        "sources: ['~/.claude/projects/-repo-a/u1.jsonl', "
        "'~/.claude/projects/-repo-a/u2.jsonl']",
    )
    assert _by_name(codebase_index.build_index(str(tmp_path)), "X")["source_dirs"] == ["-repo-a"]


def test_non_jsonl_sources_ignored(tmp_path):
    _entity(
        tmp_path, "y.md",
        "title: Y\ncategory: entities\ntags: [codebase]\n"
        "sources:\n  - projects/some-initiative\n  - ~/notes/file.md",
    )
    assert _by_name(codebase_index.build_index(str(tmp_path)), "Y")["source_dirs"] == []


def test_gitlab_path_from_body_when_no_repo_line(tmp_path):
    _entity(
        tmp_path, "plat.md",
        "title: Plat\ncategory: entities\ntags: [codebase]",
        body="hosted at `gitlab.hellowork-group.com/XJob/Hw.Emploi.Platform`, branch develop.",
    )
    assert _by_name(codebase_index.build_index(str(tmp_path)), "Plat")["git_path"] == \
        "gitlab.hellowork-group.com/XJob/Hw.Emploi.Platform"


def test_non_codebase_entity_excluded(tmp_path):
    _entity(tmp_path, "person.md", "title: Thomas Nabet\ncategory: entities\ntags: [person]")
    _entity(tmp_path, "repo.md", "title: Repo\ncategory: entities\ntags: [codebase]")
    assert [e["name"] for e in codebase_index.build_index(str(tmp_path))] == ["Repo"]


def test_git_path_absent_is_empty(tmp_path):
    _entity(
        tmp_path, "z.md",
        "title: Z\ncategory: entities\ntags: [codebase]",
        body="No repo line here.",
    )
    assert _by_name(codebase_index.build_index(str(tmp_path)), "Z")["git_path"] == ""


def test_missing_entities_dir_returns_empty(tmp_path):
    assert codebase_index.build_index(str(tmp_path)) == []


def test_malformed_entity_skipped(tmp_path):
    edir = tmp_path / "entities"
    edir.mkdir(parents=True)
    (edir / "bad.md").write_text("no frontmatter here", encoding="utf-8")
    _entity(tmp_path, "good.md", "title: Good\ncategory: entities\ntags: [codebase]")
    assert [e["name"] for e in codebase_index.build_index(str(tmp_path))] == ["Good"]
