"""Install VibeWise for the Cline VS Code (and JetBrains) extension.

The extension has no plugin system, so this installs three plain pieces:

- the Learn and Reset guides, copied to `~/.cline/vibe-wise/`;
- `/vibe-wise-learn` and `/vibe-wise-reset` global workflows (the extension's slash
  menu lists only built-in commands and workflows) that point at those guides;
- an always-on global rule. It is part of every request, so learning mode survives
  new tasks, resumed tasks, and context compaction, and it defers to each project's
  profile: projects that never ran Learn, or that paused it, are unaffected.

The guides are deliberately not installed as Cline skills. Cline advertises every
skill to the model on every request and ignores `disable-model-invocation`, so a
`learn` skill could start onboarding in any project without being asked.

    python3 scripts/install_cline.py                         # Cline on this machine
    python3 scripts/install_cline.py --home /mnt/c/Users/me  # Windows Cline, from WSL

With VS Code's WSL remote, the extension runs inside WSL, so run it there without
`--home`. Cline finds "Documents" the way this script does: `xdg-user-dir DOCUMENTS`
on Linux (often just your home directory under WSL), the shell's Documents folder
on Windows. Pass `--documents` when Cline uses a different folder.

Re-run after updating this checkout. Learner notes are never touched.
"""

import argparse
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = ROOT / "com.github.copilot/rules/vibe-wise.mdc"
# The Copilot rule loads the plugin's `learn` skill; here it reads the copied guide.
RULE_SKILL_STEP = "load the `learn` skill"
GUIDES = ("learn", "reset")
# A workflow's slash command is its exact file name, so these have no extension.
WORKFLOWS = {"vibe-wise-learn": ("learn", "Learn"), "vibe-wise-reset": ("reset", "Reset")}
# Earlier versions installed the guides as skills; remove only copies we wrote.
MARKER = "VibeWise"


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


def as_seen_by_cline(path):
    """Spell a path the way the extension will see it.

    Installing into a Windows home from WSL writes through /mnt/<drive>/, but the
    extension runs on Windows and needs the drive-letter form.
    """
    parts = path.parts
    if len(parts) > 3 and parts[1] == "mnt" and len(parts[2]) == 1:
        return str(PureWindowsPath(f"{parts[2].upper()}:\\", *parts[3:]))
    return str(path)


def remove_old_skills(home):
    for name in GUIDES:
        old = home / ".cline" / "skills" / name
        skill = old / "SKILL.md"
        if skill.is_file() and MARKER in skill.read_text(encoding="utf-8"):
            shutil.rmtree(old)
            print(f"removed old skill  {old}")


def install(home, documents):
    guides_dir = home / ".cline" / "vibe-wise"
    if guides_dir.exists():
        shutil.rmtree(guides_dir)
    for name in GUIDES:
        shutil.copytree(ROOT / "skills" / name, guides_dir / name)
    print(f"guides   {guides_dir}")
    remove_old_skills(home)

    guide = {name: as_seen_by_cline(guides_dir / name / "SKILL.md") for name in GUIDES}
    workflows_dir = documents / "Cline" / "Workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    for command, (name, label) in WORKFLOWS.items():
        (workflows_dir / command).write_text(
            f"Read and follow the VibeWise {label} guide at:\n{guide[name]}\n\n"
            "Any text after the command is the user's request.\n",
            encoding="utf-8",
        )
        print(f"command  /{command}  ({workflows_dir / command})")

    _, _, body = RULE_SOURCE.read_text(encoding="utf-8").split("---", 2)
    if RULE_SKILL_STEP not in body:
        sys.exit(f"{RULE_SOURCE} no longer says {RULE_SKILL_STEP!r}; update this installer.")
    rules_dir = documents / "Cline" / "Rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    # Cline treats rule frontmatter as conditions, so the rule is plain Markdown.
    (rules_dir / "vibe-wise.md").write_text(
        body.lstrip().replace(RULE_SKILL_STEP, f"read the Learn guide at `{guide['learn']}`"),
        encoding="utf-8",
    )
    print(f"rule     {rules_dir / 'vibe-wise.md'}")


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
