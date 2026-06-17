from pathlib import Path

from engramme_assist import install

SKILLS = Path(install.__file__).resolve().parent / "_data" / "skills"


def _read(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def _read_ref(skill: str, name: str) -> str:
    return (SKILLS / skill / "references" / name).read_text(encoding="utf-8")


def test_wiki_profile_states_interactive_invariant():
    t = _read("wiki-profile").lower()
    # must explicitly forbid the pass-through / rubber-stamp behaviour
    assert "interactive" in t
    assert "never" in t and ("pass-through" in t or "rubber" in t)


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
    assert "channel" in t                         # framed as Slack channels
    assert "*-bots" in _read("wiki-profile")      # channel-style example, not file glob


def test_wiki_profile_sources_are_opt_in():
    t = _read("wiki-profile").lower()
    assert "tu utilises" in t or "opt-in" in t    # French user-facing prompt kept; opt-in framing


def test_wiki_init_invokes_profile_interactively():
    t = _read("wiki-init").lower()
    assert "wiki-profile" in t
    assert "interacti" in t                       # guarantees interactive invocation


def test_wiki_init_has_completeness_gate_and_report():
    t = _read("wiki-init").lower()
    assert "complete" in t                        # completeness gate
    assert "report" in t                          # final setup report
    assert "pending" in t                         # deferred-source status


def test_wiki_profile_specifies_scoring_axis_weight():
    t = _read("wiki-profile")
    # scoring axes must explicitly require a weight + the exact key names
    assert "scoring_axes" in t and "weight" in t
    assert "must_read" in t and "watch" in t
    assert "integer ≥ 1" in t                     # weight is a required positive integer


def test_wiki_profile_offers_assisted_discovery_with_keep_ignore():
    t = _read("wiki-profile")
    low = t.lower()
    # offers to enumerate + help choose, opt-in
    assert "assisted discovery" in low
    assert "slack_search_channels" in t and "getConfluenceSpaces" in t
    # must present BOTH sides explicitly, never silently drop, user decides
    assert "keep" in low and "ignore" in low
    assert "last word" in low


def test_wiki_profile_ships_filled_example_alongside():
    # the skill promises a co-located, loadable template — it must actually ship
    example = SKILLS / "wiki-profile" / "profile.example.yml"
    assert example.is_file(), example
    text = example.read_text(encoding="utf-8")
    assert "scoring_axes" in text and "weight:" in text and "thresholds" in text


def test_morning_brief_references_are_shipped_and_linked():
    t = _read("morning-brief")
    expected = (
        "agent-a1-slack-triage.md",
        "agent-a2-slack-synth.md",
        "agent-b-claude-sessions.md",
        "agent-c-confluence.md",
        "agent-d-calendar.md",
        "agent-e-daily-update.md",
        "architecture-notes.md",
        "brief-template.md",
        "person-entity-convention.md",
        "sources-monitored.md",
    )
    for filename in expected:
        rel = f"references/{filename}"
        assert rel in t, rel
        assert (SKILLS / "morning-brief" / rel).is_file(), rel


def test_morning_brief_agent_prompts_remain_loadable():
    for filename in (
        "agent-a1-slack-triage.md",
        "agent-a2-slack-synth.md",
        "agent-b-claude-sessions.md",
        "agent-c-confluence.md",
        "agent-d-calendar.md",
        "agent-e-daily-update.md",
    ):
        text = _read_ref("morning-brief", filename)
        assert text.count("```") >= 2, filename
        assert "Subagent type:" in text, filename
        assert "Model:" in text, filename


def test_morning_brief_template_keeps_output_contract():
    template = _read_ref("morning-brief", "brief-template.md")
    for marker in (
        "digest-first / single-mention rule",
        "Rafraîchi le matin",
        "## 📌 Must read",
        "## 👀 À surveiller",
        "## 📋 Actions en cours",
        "## ⚡ Action required today",
        "## 🎯 Préparation réunions",
        "## 📅 Next working day — prepare today",
        "## 🗂 Faible signal — liens",
        "qmd query",
        "goals.md",
        "one_liner",
        "under 1,200 words",
    ):
        assert marker in template, marker


def test_wiki_ingest_is_adopted_with_origin_marker():
    t = _read("wiki-ingest")
    assert "adopted from obsidian-wiki==2026.6.5" in t
