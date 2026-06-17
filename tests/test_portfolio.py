# tests/test_portfolio.py
import sys
from datetime import date
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "engramme_assist" / "_data" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import portfolio  # noqa: E402  (initiative_index importé en interne depuis le même dossier)


def test_norm_engagement():
    assert portfolio.norm_engagement("Porteur") == "porteur"
    assert portfolio.norm_engagement("sponsor") is None
    assert portfolio.norm_engagement(None) is None


def test_source_jsonl_paths_block_and_inline():
    block = "sources:\n  - ~/.claude/projects/a/x.jsonl\n  - notes.md\n"
    assert portfolio.source_jsonl_paths(block) == [str(Path.home() / ".claude/projects/a/x.jsonl")]
    assert portfolio.source_jsonl_paths("sources: [~/a.jsonl, b.md]\n") == [str(Path.home() / "a.jsonl")]


def test_parse_date():
    assert portfolio.parse_date("2026-06-17") == date(2026, 6, 17)
    assert portfolio.parse_date("analysis 2026-06-17 from X") == date(2026, 6, 17)
    assert portfolio.parse_date(None) is None and portfolio.parse_date("nope") is None


def test_topic_last_seen_matches_names():
    counter = {"assay-harbor-docker": {"last_seen": "2026-06-11"},
               "assay": {"last_seen": "2026-06-15"},
               "stet-eval": {"last_seen": "2026-06-20"}}
    assert portfolio.topic_last_seen({"assay"}, counter) == date(2026, 6, 15)
    assert portfolio.topic_last_seen({"nomatch"}, counter) is None


def test_compute_last_movement_takes_max_ignoring_none():
    assert portfolio.compute_last_movement(date(2026, 6, 1), None, date(2026, 6, 10)) == date(2026, 6, 10)
    assert portfolio.compute_last_movement(None, None) is None


def test_is_stale_per_tier():
    th = {"porteur": 10, "contributeur": 21, "observateur": 45}
    assert portfolio.is_stale("porteur", 12, th) is True
    assert portfolio.is_stale("porteur", 9, th) is False
    assert portfolio.is_stale("observateur", 12, th) is False
    assert portfolio.is_stale("porteur", None, th) is False


def test_load_thresholds_defaults_and_override():
    assert portfolio.load_thresholds("") == portfolio.DEFAULT_STALE
    prof = "portfolio:\n  enabled: true\n  stale_days:\n    porteur: 7\n    contributeur: 21\n    observateur: 45\n"
    assert portfolio.load_thresholds(prof)["porteur"] == 7


def test_portfolio_enabled():
    assert portfolio.portfolio_enabled("") is True
    assert portfolio.portfolio_enabled("portfolio:\n  enabled: false\n") is False
    assert portfolio.portfolio_enabled("portfolio:\n  enabled: true\n") is True


def test_build_snapshot_flags_stale_only_active():
    today, th = date(2026, 6, 17), portfolio.DEFAULT_STALE
    projects = [
        {"title": "A", "path": "projects/a/A.md", "engagement": "porteur",
         "status": "active", "last_movement": date(2026, 6, 1), "next": "go"},
        {"title": "B", "path": "projects/b/B.md", "engagement": "porteur",
         "status": "paused", "last_movement": date(2026, 5, 1), "next": None}]
    snap = portfolio.build_snapshot(projects, today, th)
    a = next(r for r in snap["projects"] if r["title"] == "A")
    b = next(r for r in snap["projects"] if r["title"] == "B")
    assert a["days_stale"] == 16 and a["is_stale"] is True
    assert b["is_stale"] is False  # paused jamais stale
    assert [r["title"] for r in snap["stale"]] == ["A"]


def test_collect_reads_index_and_filters_engagement(tmp_path):
    foo = tmp_path / "projects" / "foo"
    foo.mkdir(parents=True)
    (foo / "Foo.md").write_text(
        "---\ntitle: Foo\ncategory: projects\nstatus: active\n"
        "engagement: porteur\nupdated: 2026-06-01\nnext: ship it\n---\n# Foo\n", encoding="utf-8")
    bar = tmp_path / "projects" / "bar"
    bar.mkdir(parents=True)
    (bar / "Bar.md").write_text(  # pas d'engagement → exclu
        "---\ntitle: Bar\ncategory: projects\nstatus: active\nupdated: 2026-06-01\n---\n# Bar\n",
        encoding="utf-8")
    snap = portfolio.collect(str(tmp_path), date(2026, 6, 17), {}, portfolio.DEFAULT_STALE)
    assert [r["title"] for r in snap["projects"]] == ["Foo"]
    foo_rec = snap["projects"][0]
    assert foo_rec["engagement"] == "porteur" and foo_rec["status"] == "active"
    assert foo_rec["next"] == "ship it" and foo_rec["days_stale"] == 16 and foo_rec["is_stale"] is True


def test_render_md_is_derived_and_lists_projects():
    snap = {"generated": "2026-06-17", "projects": [
        {"title": "A", "path": "projects/a/A.md", "engagement": "porteur",
         "status": "active", "last_movement": "2026-06-01", "days_stale": 16,
         "is_stale": True, "next": "go"}], "stale": []}
    md = portfolio.render_md(snap)
    assert "Ne pas éditer à la main" in md
    assert "[[A]]" in md and "porteur" in md and "⚠️" in md
