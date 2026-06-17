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
