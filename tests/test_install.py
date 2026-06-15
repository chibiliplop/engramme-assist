import sys
from pathlib import Path

from engramme_assist import install


REPO_ROOT = Path(install.__file__).resolve().parent.parent
DATA_ROOT = Path(install.__file__).resolve().parent / "_data"


def test_overlay_skills_list_is_the_six_vendored():
    assert set(install.OVERLAY_SKILLS) == {
        "daily-update", "jot", "morning-brief", "weekly-retro", "wiki-init", "wiki-profile",
    }


def test_data_root_is_packaged_data_dir():
    # Overlay data is packaged under engramme_assist/_data/ so it ships in the wheel.
    root = install.data_root()
    assert root == DATA_ROOT
    assert (root / "skills").is_dir()


def test_every_overlay_skill_has_a_skill_md():
    root = install.data_root()
    for name in install.OVERLAY_SKILLS:
        assert (root / "skills" / name / "SKILL.md").is_file(), name


def test_profile_example_has_single_source_in_wiki_profile_skill():
    # The installer reuses the wiki-profile skill's copy; there must be no second divergent one.
    root = install.data_root()
    assert (root / "skills" / "wiki-profile" / "profile.example.yml").is_file()
    assert not (root / "profile.example.yml").exists()


def test_read_upstream_pin_matches_file():
    pin = install.read_upstream_pin()
    assert pin.startswith("obsidian-wiki==")
    assert pin == (DATA_ROOT / "UPSTREAM").read_text().strip()


def test_default_mode_is_copy_on_windows(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Windows")
    assert install.default_mode() == "copy"


def test_default_mode_is_symlink_on_posix(monkeypatch):
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")
    assert install.default_mode() == "symlink"
    monkeypatch.setattr(install.platform, "system", lambda: "Linux")
    assert install.default_mode() == "symlink"


def test_install_overlay_skills_symlink(tmp_path):
    target = tmp_path / ".claude" / "skills"
    done = install.install_overlay_skills(target, "symlink")
    assert set(done) == set(install.OVERLAY_SKILLS)
    for name in install.OVERLAY_SKILLS:
        link = target / name
        assert link.is_symlink()
        assert (link / "SKILL.md").exists()


def test_install_overlay_skills_copy(tmp_path):
    target = tmp_path / "skills"
    done = install.install_overlay_skills(target, "copy")
    assert set(done) == set(install.OVERLAY_SKILLS)
    link = target / "jot"
    assert link.is_dir() and not link.is_symlink()
    assert (link / "SKILL.md").exists()


def test_install_overlay_replaces_existing_managed_symlink(tmp_path):
    target = tmp_path / "skills"
    install.install_overlay_skills(target, "symlink")  # first pass
    done = install.install_overlay_skills(target, "symlink")  # idempotent re-run
    assert set(done) == set(install.OVERLAY_SKILLS)
    assert (target / "daily-update").is_symlink()


def test_install_overlay_skips_unmanaged_user_dir(tmp_path):
    target = tmp_path / "skills"
    target.mkdir(parents=True)
    user_dir = target / "jot"  # a real dir WITHOUT SKILL.md = the user's own
    user_dir.mkdir()
    (user_dir / "notes.txt").write_text("mine")
    done = install.install_overlay_skills(target, "copy")
    assert "jot" not in done            # left untouched
    assert (user_dir / "notes.txt").exists()
    assert "wiki-init" in done          # the others still install


def test_link_or_copy_falls_back_to_copy_on_oserror(tmp_path, monkeypatch):
    src = install.data_root() / "skills" / "jot"
    dst = tmp_path / "jot"

    def boom(*a, **k):
        raise OSError("symlink not permitted")

    monkeypatch.setattr(install.Path, "symlink_to", boom, raising=False)
    install._link_or_copy(src, dst, "symlink")
    assert dst.is_dir() and not dst.is_symlink()  # fell back to a real copy
    assert (dst / "SKILL.md").exists()


def test_place_if_absent_writes_when_missing(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    dst = tmp_path / "sub" / "dst.txt"
    assert install.place_if_absent(src, dst) is True
    assert dst.read_text() == "hello"


def test_place_if_absent_is_noop_when_present(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("new")
    dst = tmp_path / "dst.txt"
    dst.write_text("existing — keep me")
    assert install.place_if_absent(src, dst) is False
    assert dst.read_text() == "existing — keep me"  # never clobbered


def test_run_upstream_setup_builds_correct_argv(monkeypatch):
    captured = {}

    class FakeCli:
        @staticmethod
        def main(argv):
            captured["argv"] = argv
            return 0

    import types
    fake_mod = types.ModuleType("obsidian_wiki.cli")
    fake_mod.main = FakeCli.main
    monkeypatch.setitem(sys.modules, "obsidian_wiki.cli", fake_mod)

    rc = install.run_upstream_setup("/tmp/vault", "symlink")
    assert rc == 0
    assert captured["argv"] == ["setup", "--vault", "/tmp/vault", "--project", "/tmp/vault"]


def test_run_upstream_setup_passes_copy_flag(monkeypatch):
    captured = {}
    import types
    fake_mod = types.ModuleType("obsidian_wiki.cli")
    fake_mod.main = lambda argv: captured.setdefault("argv", argv) or 0
    monkeypatch.setitem(sys.modules, "obsidian_wiki.cli", fake_mod)

    install.run_upstream_setup("/tmp/vault", "copy")
    assert "--copy" in captured["argv"]


def test_verify_upstream_raises_when_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "obsidian_wiki", None)  # force ImportError
    import pytest
    with pytest.raises(RuntimeError, match="not installed"):
        install.verify_upstream()


def test_cohérence_pin_pyproject_vs_upstream():
    # The pyproject dependency must match the UPSTREAM file (single source of truth).
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    pin = install.read_upstream_pin()  # 'obsidian-wiki==2026.6.5'
    assert f'"{pin}"' in pyproject, f"pyproject must depend on {pin}"


def _fake_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a tmp dir so global installs never touch real $HOME."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(install.Path, "home", staticmethod(lambda: home), raising=False)
    return home


def test_main_install_end_to_end(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    home = _fake_home(tmp_path, monkeypatch)

    monkeypatch.setattr(install, "run_upstream_setup", lambda v, m, local=False: 0)
    monkeypatch.setattr(install, "verify_upstream", lambda: "2026.6.5")
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")

    rc = install.main(["install", "--vault", str(vault)])
    assert rc == 0

    # Default scope = global + project: skills land under BOTH the vault and $HOME.
    for name in install.OVERLAY_SKILLS:
        assert (vault / ".claude" / "skills" / name / "SKILL.md").exists(), name
        assert (home / ".codex" / "skills" / name / "SKILL.md").exists(), name  # a global-only agent
    # Non-destructive vault files dropped:
    assert (vault / "AGENTS.md").exists()                       # from AGENTS.generic.md
    assert (vault / "_meta" / "profile.example.yml").exists()
    assert (vault / "_meta" / "scripts" / "gardener.py").exists()
    assert (vault / "_meta" / "scripts" / "insights.py").exists()


def test_main_install_local_scope_skips_global(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    home = _fake_home(tmp_path, monkeypatch)

    captured = {}

    def fake_setup(v, m, local=False):
        captured["local"] = local
        return 0

    monkeypatch.setattr(install, "run_upstream_setup", fake_setup)
    monkeypatch.setattr(install, "verify_upstream", lambda: "2026.6.5")
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")

    install.main(["install", "--vault", str(vault), "--local"])

    assert captured["local"] is True                             # --project-only forwarded upstream
    assert (vault / ".claude" / "skills" / "jot" / "SKILL.md").exists()   # project dir populated
    assert not (home / ".codex" / "skills").exists()             # no global install


def test_main_install_does_not_clobber_existing_agents_md(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    (vault).mkdir()
    _fake_home(tmp_path, monkeypatch)
    (vault / "AGENTS.md").write_text("# Thomas's real conventions — keep")

    monkeypatch.setattr(install, "run_upstream_setup", lambda v, m, local=False: 0)
    monkeypatch.setattr(install, "verify_upstream", lambda: "2026.6.5")
    monkeypatch.setattr(install.platform, "system", lambda: "Darwin")

    install.main(["install", "--vault", str(vault)])
    assert (vault / "AGENTS.md").read_text() == "# Thomas's real conventions — keep"
    assert (vault / "AGENTS.generic.md").exists()  # reference copy placed instead


def test_overlay_skill_targets_local_is_project_only(tmp_path):
    vault = tmp_path / "vault"
    home = tmp_path / "home"
    targets = install.overlay_skill_targets(vault, local=True, home=home)
    assert targets, "expected project-local targets"
    assert all(vault in t.parents for t in targets), targets     # every target under the vault
    assert all(home not in t.parents for t in targets)           # nothing under $HOME
    assert vault / ".claude" / "skills" in targets


def test_overlay_skill_targets_global_plus_project(tmp_path):
    vault = tmp_path / "vault"
    home = tmp_path / "home"
    targets = install.overlay_skill_targets(vault, local=False, home=home)
    assert vault / ".claude" / "skills" in targets              # project (vault)
    assert home / ".codex" / "skills" in targets                # global-only agent
    assert home / ".gemini" / "skills" in targets
    assert len(targets) == len(set(targets))                    # de-duplicated


def test_run_upstream_setup_local_adds_project_only(monkeypatch):
    # Patch the real cli.main directly (robust to import order, unlike sys.modules).
    import obsidian_wiki.cli as upstream_cli
    captured = {}
    monkeypatch.setattr(upstream_cli, "main", lambda argv: captured.update(argv=argv) or 0)

    install.run_upstream_setup("/tmp/vault", "symlink", local=True)
    assert "--project-only" in captured["argv"]
    # default (local=False) must NOT add it
    captured.clear()
    install.run_upstream_setup("/tmp/vault", "symlink")
    assert "--project-only" not in captured["argv"]
