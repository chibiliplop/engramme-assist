import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "engramme_assist" / "_data" / "scripts" / "initiative_index.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("initiative_index", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hub(vault: Path, slug: str, frontmatter: str, body: str = "") -> None:
    pdir = vault / "projects" / slug
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"{slug}.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def _by_slug(index, slug):
    return next(e for e in index if e["slug"] == slug)


def test_basic_inline_and_block_fields(tmp_path):
    _hub(
        tmp_path, "blocage-offres-doublons",
        "title: Blocage des offres doublons\n"
        "category: projects\n"
        "aliases:\n  - Blocage des offres doublons\n  - Offres doublons\n"
        'team: "[[JobFactory Publication]]"\n'
        "status: active\n"
        'codebases: ["[[Hw.Emploi.Microservices]]"]',
    )
    idx = _load().build_index(str(tmp_path))
    e = _by_slug(idx, "blocage-offres-doublons")
    assert e["title"] == "Blocage des offres doublons"
    assert "Offres doublons" in e["aliases"]
    assert e["team"] == ["JobFactory Publication"]
    assert e["codebases"] == ["Hw.Emploi.Microservices"]
    assert e["status"] == "active"
    assert e["path"] == "projects/blocage-offres-doublons/blocage-offres-doublons.md"


def test_team_block_list_normalized(tmp_path):
    _hub(
        tmp_path, "offer-promote-reboost",
        "title: Offre Promote\ncategory: projects\n"
        'team:\n  - "[[Acquisition & notoriété]]"\n  - "[[Data-ingé]]"\n'
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "offer-promote-reboost")
    assert e["team"] == ["Acquisition & notoriété", "Data-ingé"]


def test_jira_from_provenance_when_no_field(tmp_path):
    _hub(
        tmp_path, "x",
        "title: X\ncategory: projects\nstatus: active\n"
        "provenance: analysis from Jira JFP-400 + Confluence",
    )
    assert _by_slug(_load().build_index(str(tmp_path)), "x")["jira_keys"] == ["JFP-400"]


def test_jira_field_takes_priority(tmp_path):
    _hub(
        tmp_path, "y",
        "title: Y\ncategory: projects\nstatus: active\n"
        'jira: ["SE-18453"]\n'
        "provenance: noise SE-99999",
    )
    assert _by_slug(_load().build_index(str(tmp_path)), "y")["jira_keys"] == ["SE-18453"]


def test_status_defaults_active(tmp_path):
    _hub(tmp_path, "z", "title: Z\ncategory: projects")
    assert _by_slug(_load().build_index(str(tmp_path)), "z")["status"] == "active"


def test_alias_collision_keeps_both(tmp_path):
    _hub(tmp_path, "a", "title: A\ncategory: projects\naliases:\n  - Shared")
    _hub(tmp_path, "b", "title: B\ncategory: projects\naliases:\n  - Shared")
    idx = _load().build_index(str(tmp_path))
    owners = [e["slug"] for e in idx if "Shared" in e["aliases"]]
    assert sorted(owners) == ["a", "b"]


def test_dir_without_hub_is_skipped(tmp_path):
    (tmp_path / "projects" / "no-hub").mkdir(parents=True)
    (tmp_path / "projects" / "no-hub" / "note.md").write_text(
        "---\ncategory: concepts\n---\nbody", encoding="utf-8"
    )
    _hub(tmp_path, "real", "title: Real\ncategory: projects")
    idx = _load().build_index(str(tmp_path))
    assert [e["slug"] for e in idx] == ["real"]


def test_missing_projects_dir_returns_empty(tmp_path):
    assert _load().build_index(str(tmp_path)) == []


def test_inline_list_field_with_trailing_yaml_comment(tmp_path):
    """inline-list: trailing ' # comment' must not corrupt parse."""
    _hub(
        tmp_path, "messagerie-candidat-recruteur",
        "title: Messagerie\n"
        "category: projects\n"
        'codebases: ["[[Hw.Emploi.Platform]]"]  # + app mobile iOS/Android (codebase non trackée)\n'
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "messagerie-candidat-recruteur")
    assert e["codebases"] == ["Hw.Emploi.Platform"]


def test_scalar_field_with_trailing_yaml_comment(tmp_path):
    """scalar: trailing ' # comment' must be stripped from the value."""
    _hub(
        tmp_path, "scalar-comment",
        "title: My Project  # this is a note\n"
        "category: projects\n"
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "scalar-comment")
    assert e["title"] == "My Project"


def test_scalar_hash_mid_value_preserved(tmp_path):
    """A '#' not preceded by whitespace must NOT be stripped (e.g. colour #fff)."""
    _hub(
        tmp_path, "hash-mid",
        "title: Tag#123\n"
        "category: projects\n"
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "hash-mid")
    assert e["title"] == "Tag#123"


def test_folded_scalar_title_is_unwrapped(tmp_path):
    """Folded YAML scalars are used by wiki-update and must not become literal '>-'."""
    _hub(
        tmp_path, "folded-title",
        "title: >-\n"
        "  Folded Initiative Title\n"
        "category: projects\n"
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "folded-title")
    assert e["title"] == "Folded Initiative Title"


def test_quoted_category_and_comment_still_identifies_hub(tmp_path):
    _hub(
        tmp_path, "quoted-category",
        'title: Quoted Category\ncategory: "projects"  # valid yaml comment\nstatus: active',
    )
    assert _by_slug(_load().build_index(str(tmp_path)), "quoted-category")["title"] == "Quoted Category"


def test_inline_list_keeps_commas_and_hashes_inside_quotes(tmp_path):
    _hub(
        tmp_path, "rich-list",
        'title: Rich List\ncategory: projects\n'
        'aliases: ["Foo, Bar", "Hash # kept", "Simple"]  # outer comment\n'
        'jira: ["SE-18453", "JFP-400"]\n'
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "rich-list")
    assert e["aliases"] == ["Foo, Bar", "Hash # kept", "Simple"]
    assert e["jira_keys"] == ["SE-18453", "JFP-400"]


def test_block_list_strips_item_comments_but_keeps_quoted_hash(tmp_path):
    _hub(
        tmp_path, "block-comments",
        "title: Block Comments\ncategory: projects\n"
        "aliases:\n"
        '  - "Hash # kept"\n'
        "  - Plain value  # dropped\n"
        "status: active",
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "block-comments")
    assert e["aliases"] == ["Hash # kept", "Plain value"]


def test_wikilink_alias_and_section_are_stripped(tmp_path):
    _hub(
        tmp_path, "wikilink-alias",
        "title: Wikilink Alias\ncategory: projects\n"
        'team: "[[Team Page#Section|Visible team]]"\n'
        'codebases: ["[[Repo Page|Visible repo]]"]\n',
    )
    e = _by_slug(_load().build_index(str(tmp_path)), "wikilink-alias")
    assert e["team"] == ["Team Page"]
    assert e["codebases"] == ["Repo Page"]
