# VibeWise in Cline

These notes adapt Claude Code tool and command names for Cline: the CLI, SDK, and
Kanban (VibeWise plugin) and the VS Code or JetBrains extension (installed skills
and rule). They don't change the learning behavior; follow SKILL.md and its guides
as written.

- Commands: with the plugin, `/vibe-wise:learn` is `/vibe-wise-learn` and
  `/vibe-wise:reset` is `/vibe-wise-reset`. In the extension they are the `/learn`
  and `/reset` skills. Activate Learn or Reset only when the learner invokes them.
- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Cline. Guides such as
  `behavior.md` sit beside this file; resolve them from its directory.
- Files: where the guides say Read, use your file-reading tool (`read_file` in the
  extension, `read_files` in the CLI). Where they say Glob, use your file listing or
  search tool. Check optional learner-state files with a check that succeeds when
  they are missing.
- Choices: AskUserQuestion corresponds to `ask_followup_question` in the extension
  and `ask_question` in the CLI. Use it with the same options; if neither exists,
  ask one plain-text question with the options listed beneath it. Then end your
  turn and wait for the learner's response.
- Restoration: the CLI plugin adds these reading instructions at the start of each
  run. In the extension, the global VibeWise rule tells you to reload this guide
  whenever the project's profile is active, including after compaction. If you are
  unsure whether a decision is pending, search the entire `progress.md` before
  acting.
- Replies: present each checkpoint or question once, at the end of your reply,
  with its options beneath it. Don't restate it in a separate message, add a
  closing line after it, or quote these guides to the learner.
