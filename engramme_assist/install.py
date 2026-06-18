"""engramme-assist installer — overlay on top of obsidian-wiki.

Delegates the base install to ``obsidian-wiki setup`` (all upstream skills +
global config + bootstrap), then lays this overlay's skills on top, and drops
``AGENTS.generic.md`` / ``profile.example.yml`` / the gardener scripts into the
vault non-destructively. Cross-platform: symlink on macOS/Linux (copy fallback
on ``OSError``), copy on Windows; ``--copy`` forces copy everywhere.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path

from engramme_assist import __version__


# The 9 skills this overlay vendors. `daily-update`, `wiki-ingest`,
# `claude-history-ingest` and `wiki-update` override the upstream skills of the same
# name (adopted copies — see each SKILL.md's origin marker); the rest are new additions.
OVERLAY_SKILLS = (
    "daily-update",
    "jot",
    "morning-brief",
    "weekly-retro",
    "wiki-init",
    "wiki-profile",
    "wiki-ingest",
    "claude-history-ingest",
    "wiki-update",
)

# Agent skill directories. The overlay installs its skills into the SAME set
# obsidian-wiki uses, so every agent it supports also gets the overlay skills —
# not just Claude. The live list is read straight from the pinned upstream (see
# _agent_skill_dirs) so it stays in sync automatically; the tuples below are a
# vendored fallback used only if those upstream internals ever move.
#
# Global dirs live under $HOME (discoverable from any directory); project dirs
# live under the vault. Upstream's project scope is the narrower set — the
# global-only agents (gemini, codex, hermes, copilot, …) are NOT covered by a
# project-local (`--local`) install, on either side.
_GLOBAL_AGENT_SKILL_DIRS = (
    ".claude/skills",
    ".gemini/skills",
    ".gemini/antigravity/skills",
    ".codex/skills",
    ".hermes/skills",
    ".openclaw/skills",
    ".copilot/skills",
    ".trae/skills",
    ".trae-cn/skills",
    ".kiro/skills",
    ".pi/agent/skills",
    ".agents/skills",
)
_PROJECT_AGENT_SKILL_DIRS = (
    ".claude/skills",
    ".cursor/skills",
    ".windsurf/skills",
    ".agents/skills",
    ".pi/skills",
    ".kiro/skills",
)


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def _agent_skill_dirs() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(_global_, _project_) agent skill dirs, read from the pinned obsidian-wiki.

    We already pin obsidian-wiki exactly and import its CLI, so reading its agent
    lists keeps the overlay in lockstep with whatever agents upstream supports —
    no manual resync. Falls back to the vendored tuples if those internals move.
    """
    try:
        from obsidian_wiki.cli import GLOBAL_AGENT_DIRS, PROJECT_AGENT_DIRS

        global_dirs = tuple(entry[0] for entry in GLOBAL_AGENT_DIRS)
        project_dirs = tuple(entry[0] for entry in PROJECT_AGENT_DIRS)
        if global_dirs and project_dirs:
            return global_dirs, project_dirs
    except Exception:  # upstream renamed/removed the constants → use the fallback
        pass
    return _GLOBAL_AGENT_SKILL_DIRS, _PROJECT_AGENT_SKILL_DIRS


def _hermes_profile_skill_dirs(home: Path) -> list[Path]:
    """Mirror upstream: the active HERMES_HOME profile + every ~/.hermes/profiles/*."""
    dirs: list[Path] = []
    handled: set[Path] = set()
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        hp = Path(hermes_home).expanduser()
        if hp != home / ".hermes":
            dirs.append(hp / "skills")
            handled.add(hp)
    profiles = home / ".hermes" / "profiles"
    if profiles.is_dir():
        for prof in sorted(p for p in profiles.iterdir() if p.is_dir()):
            if prof not in handled:
                dirs.append(prof / "skills")
    return dirs


def overlay_skill_targets(vault_path: Path, local: bool, home: Path | None = None) -> list[Path]:
    """Every skill dir the overlay should populate.

    ``local=True``  → project-local only (under the vault), matching upstream's
    ``--project-only``. ``local=False`` → global (under ``$HOME``) + project-local.
    """
    home = home or Path.home()
    global_dirs, project_dirs = _agent_skill_dirs()
    targets: list[Path] = [vault_path / rel for rel in project_dirs]
    if not local:
        targets += [home / rel for rel in global_dirs]
        targets += _hermes_profile_skill_dirs(home)
    seen: set[Path] = set()
    deduped: list[Path] = []
    for t in targets:  # preserve order, drop duplicates
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def data_root() -> Path:
    """Root holding overlay data (skills/, scripts/, AGENTS.generic.md, examples).

    Data is packaged under ``engramme_assist/_data`` so it ships inside the wheel
    and resolves identically from a source checkout or an installed package.
    """
    root = _pkg_dir() / "_data"
    if (root / "skills").is_dir():
        return root
    raise FileNotFoundError(
        "Could not locate overlay data (engramme_assist/_data/skills). "
        "Reinstall engramme-assist."
    )


def read_upstream_pin() -> str:
    """Return the pinned upstream spec from UPSTREAM, e.g. 'obsidian-wiki==2026.6.5'."""
    f = data_root() / "UPSTREAM"
    return f.read_text().strip() if f.is_file() else ""


def default_mode() -> str:
    """Windows lacks symlink privilege by default → copy; elsewhere → symlink."""
    return "copy" if platform.system() == "Windows" else "symlink"


def _replace_target(link_path: Path) -> bool:
    """Clear an existing managed entry at *link_path*.

    Returns False (skip) if it's a real directory that isn't a managed skill
    (no SKILL.md) — that's the user's own content, leave it alone.
    """
    if link_path.is_symlink() or link_path.is_file():
        link_path.unlink()
        return True
    if link_path.is_dir():
        if (link_path / "SKILL.md").exists():
            shutil.rmtree(link_path)
            return True
        return False
    return True


def _link_or_copy(src: Path, dst: Path, mode: str) -> None:
    if mode == "symlink":
        try:
            dst.symlink_to(src, target_is_directory=True)
            return
        except OSError:
            pass  # symlink-hostile FS (e.g. Windows w/o privilege) → copy
    shutil.copytree(src, dst)


def install_overlay_skills(target_dir: Path, mode: str) -> list[str]:
    """Install the overlay skills into *target_dir*, overriding upstream.

    Returns the names actually installed (skips unmanaged user directories).
    """
    src_root = data_root() / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)
    done: list[str] = []
    for name in OVERLAY_SKILLS:
        src = src_root / name
        if not (src / "SKILL.md").exists():
            raise FileNotFoundError(f"overlay skill missing: {src}")
        link_path = target_dir / name
        if not _replace_target(link_path):
            print(f"   ⚠️  {link_path} is not a managed skill, skipping")
            continue
        _link_or_copy(src, link_path, mode)
        if not (link_path / "SKILL.md").exists():
            raise RuntimeError(f"broken overlay install: {link_path} -> {src}")
        done.append(name)
    return done


def place_if_absent(src: Path, dst: Path) -> bool:
    """Copy *src* → *dst* only if *dst* doesn't exist. Returns True if written."""
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def verify_upstream() -> str:
    """Ensure obsidian_wiki is importable; return its version (warn on pin mismatch)."""
    try:
        from obsidian_wiki import __version__ as up_ver
    except ImportError as exc:
        raise RuntimeError(
            "obsidian-wiki is not installed. Install engramme-assist (it pulls "
            "obsidian-wiki): pip install engramme-assist — or from a checkout: pip install -e ."
        ) from exc
    pin = read_upstream_pin()  # 'obsidian-wiki==2026.6.5'
    want = pin.split("==", 1)[1] if "==" in pin else ""
    if want and up_ver != want:
        print(
            f"⚠️  obsidian-wiki {up_ver} is installed but the overlay targets {want}.",
            file=sys.stderr,
        )
    return up_ver


def run_upstream_setup(vault: str, mode: str, local: bool = False) -> int:
    """Delegate the base install to obsidian-wiki: all upstream skills, global
    config, and the project bootstrap (AGENTS.md etc.) into the vault.

    ``local=True`` adds ``--project-only`` so upstream skips its global agent
    install and only seats skills project-locally (its project scope covers
    Claude/Cursor/Windsurf/… — not the global-only agents)."""
    from obsidian_wiki import cli as upstream_cli

    argv = ["setup", "--vault", vault, "--project", vault]
    if mode == "copy":
        argv.append("--copy")
    if local:
        argv.append("--project-only")
    return upstream_cli.main(argv)


def _resolve_vault(cli_vault: str | None) -> str:
    if cli_vault:
        return os.path.expanduser(cli_vault)
    if sys.stdin.isatty():
        try:
            entered = input("  Where is your Obsidian vault? (absolute path): ").strip()
        except EOFError:
            entered = ""
        if entered:
            return os.path.expanduser(entered)
    return ""


def place_vault_files(root: Path, vault_path: Path) -> None:
    """Non-destructively place vault files (AGENTS.md, profile example, scripts).

    Extracted so tests can call it directly without wiring a full argparse Namespace.
    """
    if place_if_absent(root / "AGENTS.generic.md", vault_path / "AGENTS.md"):
        print("✅  AGENTS.md written from AGENTS.generic.md")
    else:
        shutil.copyfile(root / "AGENTS.generic.md", vault_path / "AGENTS.generic.md")
        print("ℹ️  AGENTS.md exists — left as-is; reference copy at AGENTS.generic.md")
    # Single source of truth: the example shipped inside the wiki-profile skill (kept in sync
    # with that skill's documented schema), reused here so there is no second divergent copy.
    profile_example = root / "skills" / "wiki-profile" / "profile.example.yml"
    place_if_absent(profile_example, vault_path / "_meta" / "profile.example.yml")
    for script in ("gardener.py", "insights.py", "initiative_index.py", "portfolio.py", "codebase_index.py"):
        place_if_absent(root / "scripts" / script, vault_path / "_meta" / "scripts" / script)
    print("✅  profile.example.yml + vault scripts placed (if absent)")


def cmd_install(args: argparse.Namespace) -> int:
    mode = "copy" if args.copy else default_mode()
    vault = _resolve_vault(args.vault)
    if not vault:
        print("error: no vault path. Re-run with --vault /path/to/your/vault", file=sys.stderr)
        return 1

    verify_upstream()
    print(f"▸ Base install via obsidian-wiki (mode: {mode})")
    rc = run_upstream_setup(vault, mode, local=args.local)
    if rc != 0:
        print("error: upstream `obsidian-wiki setup` failed", file=sys.stderr)
        return rc

    vault_path = Path(vault)
    root = data_root()

    scope = "project-local" if args.local else "global + project"
    print(f"▸ Overlay skills ({scope})")
    targets = overlay_skill_targets(vault_path, args.local)
    for target in targets:
        install_overlay_skills(target, mode)
    print(f"✅  Overlay skills → {len(targets)} agent dir(s): {', '.join(OVERLAY_SKILLS)}")

    # Non-destructive vault files.
    place_vault_files(root, vault_path)

    print('\nNext: open the vault in your agent and say "set up my wiki" (→ wiki-init).')
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="engramme-assist",
        description="Install the engramme-assist overlay on top of obsidian-wiki.",
    )
    p.add_argument(
        "-V", "--version", action="version", version=f"engramme-assist {__version__}"
    )
    sub = p.add_subparsers(dest="command")
    ip = sub.add_parser("install", help="install the overlay on top of obsidian-wiki")
    ip.add_argument("--vault", metavar="PATH", help="absolute path to your Obsidian vault")
    ip.add_argument(
        "--copy",
        action="store_true",
        help="copy skill files instead of symlinking (forced on Windows)",
    )
    ip.add_argument(
        "--local",
        action="store_true",
        help="install project-locally (under the vault) only, not globally — applies "
        "to the overlay AND upstream; upstream's project scope covers Claude/Cursor/"
        "Windsurf/… only, not the global-only agents (gemini, codex, hermes, copilot, …)",
    )
    ip.set_defaults(func=cmd_install)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["install"]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
