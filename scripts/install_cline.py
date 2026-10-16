"""Install VibeWise for the Cline VS Code (and JetBrains) extension.

The extension has no plugin system, so this copies the Learn and Reset skills into
Cline's global skills directory and writes an always-on global rule. The rule is
part of every request, so learning mode survives new tasks, resumed tasks, and
context compaction. It defers to each project's profile: projects that never ran
Learn, or that paused it, are unaffected.

    python3 scripts/install_cline.py                         # this machine's home
    python3 scripts/install_cline.py --home /mnt/c/Users/me  # Windows Cline, from WSL

Re-run after updating this checkout. Learner notes are never touched.
"""

import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = ROOT / "com.github.copilot/rules/vibe-wise.mdc"
SKILLS = ("learn", "reset")
# Copied skill folders are replaced on update, so only replace folders we wrote.
MARKER = "VibeWise"


def rule_body():
    """The Copilot rule without its frontmatter; Cline reads plain Markdown rules."""
    text = RULE_SOURCE.read_text(encoding="utf-8")
    _, _, body = text.split("---", 2)
    return body.lstrip()


def install(home):
    skills_dir = home / ".cline" / "skills"
    rules_dir = home / "Documents" / "Cline" / "Rules"
    for name in SKILLS:
        target = skills_dir / name
        existing = target / "SKILL.md"
        if target.exists() and not (
            existing.is_file() and MARKER in existing.read_text(encoding="utf-8")
        ):
            sys.exit(f"{target} exists and isn't a VibeWise skill; leaving it alone.")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(ROOT / "skills" / name, target)
        print(f"skill  {target}")
    rules_dir.mkdir(parents=True, exist_ok=True)
    rule = rules_dir / "vibe-wise.md"
    rule.write_text(rule_body(), encoding="utf-8")
    print(f"rule   {rule}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="home directory of the machine Cline runs on")
    install(parser.parse_args().home)


if __name__ == "__main__":
    main()
