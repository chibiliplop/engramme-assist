from pathlib import Path

from engramme_assist import install

SKILLS = Path(install.__file__).resolve().parent / "_data" / "skills"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_wiki_profile_states_interactive_invariant():
    t = _read("wiki-profile").lower()
    # must explicitly forbid the pass-through / rubber-stamp behaviour
    assert "interacti" in t
    assert "jamais" in t and ("passe-plat" in t or "auto-accept" in t or "rubber" in t)


def test_wiki_profile_has_mcp_preflight_map():
    t = _read("wiki-profile")
    for marker in ("slack_search_users", "getConfluenceSpaces", "outlook_calendar_search"):
        assert marker in t, marker


def test_wiki_profile_resolves_slack_ids_now():
    t = _read("wiki-profile")
    assert "slack_search_channels" in t          # resolve ids during setup
    assert "id: null" in t or "`id`" in t


def test_wiki_profile_frames_excluded_as_slack_channels():
    t = _read("wiki-profile").lower()
    assert "excluded_patterns" in t
    assert "canal" in t or "canaux" in t          # framed as Slack channels
    assert "*-bots" in _read("wiki-profile")      # channel-style example, not file glob


def test_wiki_profile_sources_are_opt_in():
    t = _read("wiki-profile").lower()
    assert "tu utilises" in t or "utilises-tu" in t or "opt-in" in t


def test_wiki_init_invokes_profile_interactively():
    t = _read("wiki-init").lower()
    assert "wiki-profile" in t
    assert "interacti" in t                       # guarantees interactive invocation


def test_wiki_init_has_completeness_gate_and_report():
    t = _read("wiki-init").lower()
    assert "complétude" in t or "complet" in t
    assert "rapport" in t                         # final setup report
    assert "pending" in t or "différ" in t        # deferred-source status
