"""Install VibeWise for the Cline VS Code (and JetBrains) extension.

The extension has no plugin system, so this copies the Learn and Reset skills into
Cline's global skills directory, adds `/vibe-wise-learn` and `/vibe-wise-reset`
workflows, and writes an always-on global rule. The extension lists only built-in
commands and workflows in its slash menu; skills are loaded by the model with
`use_skill`, so the workflows are the explicit entry points. The rule is part of
every request, so learning mode survives new tasks, resumed tasks, and context
compaction. It defers to each project's profile: projects that never ran Learn, or
that paused it, are unaffected.

    python3 scripts/install_cline.py                         # Cline on this machine
    python3 scripts/install_cline.py --home /mnt/c/Users/me  # Windows Cline, from WSL

With VS Code's WSL remote, the extension runs inside WSL, so run it there without
`--home`. Cline finds "Documents" the way this script does: `xdg-user-dir DOCUMENTS`
on Linux (often just your home directory under WSL), the shell's Documents folder
on Windows. Pass `--documents` when Cline uses a different folder.

Re-run after updating this checkout. Learner notes are never touched.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = ROOT / "com.github.copilot/rules/vibe-wise.mdc"
SKILLS = ("learn", "reset")
# A workflow's slash command is its exact file name, so these have no extension.
WORKFLOWS = {
    "vibe-wise-learn": "learn",
    "vibe-wise-reset": "reset",
}
# Copied skill folders are replaced on update, so only replace folders we wrote.
MARKER = "VibeWise"


def rule_body():
    """The Copilot rule without its frontmatter; Cline reads plain Markdown rules."""
    text = RULE_SOURCE.read_text(encoding="utf-8")
    _, _, body = text.split("---", 2)
    return body.lstrip()


def documents_dir(home):
    """Cline's global rules and workflows live under the user's Documents folder."""
    if home == Path.home():
        query = (
            ["xdg-user-dir", "DOCUMENTS"] if sys.platform.startswith("linux") else
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetFolderPath('MyDocuments')"] if sys.platform == "win32" else
            None
        )
        try:
            found = query and subprocess.run(
                query, capture_output=True, text=True, timeout=10).stdout.strip()
        except OSError:
            found = None
        if found:
            return Path(found)
    return home / "Documents"


def install(home, documents):
    skills_dir = home / ".cline" / "skills"
    rules_dir = documents / "Cline" / "Rules"
    workflows_dir = documents / "Cline" / "Workflows"
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
    workflows_dir.mkdir(parents=True, exist_ok=True)
    for command, skill in WORKFLOWS.items():
        workflow = workflows_dir / command
        workflow.write_text(
            f"Load the VibeWise `{skill}` skill with the use_skill tool and follow it in "
            "this conversation. Any text after the command is the user's request.\n",
            encoding="utf-8",
        )
        print(f"command  /{command}  ({workflow})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--home", type=Path, default=Path.home(),
                        help="home directory of the machine Cline runs on")
    parser.add_argument("--documents", type=Path,
                        help="Cline's Documents folder (default: detected like Cline does)")
    args = parser.parse_args()
    install(args.home, args.documents or documents_dir(args.home))


if __name__ == "__main__":
    main()
