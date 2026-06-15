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


# The 6 skills this overlay vendors. `daily-update` overrides the upstream skill
# of the same name; the other five are new additions.
OVERLAY_SKILLS = (
    "daily-update",
    "jot",
    "morning-brief",
    "weekly-retro",
    "wiki-init",
    "wiki-profile",
)


def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


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


def run_upstream_setup(vault: str, mode: str) -> int:
    """Delegate the base install to obsidian-wiki: all upstream skills, global
    config, and the project bootstrap (AGENTS.md etc.) into the vault."""
    from obsidian_wiki import cli as upstream_cli

    argv = ["setup", "--vault", vault, "--project", vault]
    if mode == "copy":
        argv.append("--copy")
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


def cmd_install(args: argparse.Namespace) -> int:
    mode = "copy" if args.copy else default_mode()
    vault = _resolve_vault(args.vault)
    if not vault:
        print("error: no vault path. Re-run with --vault /path/to/your/vault", file=sys.stderr)
        return 1

    verify_upstream()
    print(f"▸ Base install via obsidian-wiki (mode: {mode})")
    rc = run_upstream_setup(vault, mode)
    if rc != 0:
        print("error: upstream `obsidian-wiki setup` failed", file=sys.stderr)
        return rc

    vault_path = Path(vault)
    root = data_root()

    print("▸ Overlay skills")
    done = install_overlay_skills(vault_path / ".claude" / "skills", mode)
    print(f"✅  Overlay skills: {', '.join(done)}")

    # Non-destructive vault files.
    if place_if_absent(root / "AGENTS.generic.md", vault_path / "AGENTS.md"):
        print("✅  AGENTS.md written from AGENTS.generic.md")
    else:
        shutil.copyfile(root / "AGENTS.generic.md", vault_path / "AGENTS.generic.md")
        print("ℹ️  AGENTS.md exists — left as-is; reference copy at AGENTS.generic.md")
    place_if_absent(root / "profile.example.yml", vault_path / "_meta" / "profile.example.yml")
    for script in ("gardener.py", "insights.py"):
        place_if_absent(root / "scripts" / script, vault_path / "_meta" / "scripts" / script)
    print("✅  profile.example.yml + gardener scripts placed (if absent)")

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
