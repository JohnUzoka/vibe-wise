# VibeWise in omp

These notes adapt Claude Code tool and command names for omp (Oh My Pi). They don't change
the learning behavior; follow SKILL.md and its guides as written.

- Commands: `/vibe-wise:learn` and `/vibe-wise:reset` are registered as slash commands
  by the VibeWise extension.
- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in omp. The plugin root is two
  directories above this file; guides such as behavior.md sit beside it.
- Files: where the guides say Read, use `read`. Where they say Glob, use `glob` or `grep`.
  Use `bash` when executing shell commands.
- Choices: where the guides mention AskUserQuestion, use the `ask` tool if available.
  If running non-interactively or `ask` is unavailable, ask one plain-text question
  with the options listed. Then end your turn and wait.
- Restoration: the VibeWise omp extension injects restoration instructions automatically
  on session start, on resume, and after compaction. Learning mode also resumes when the
  learner invokes `/vibe-wise:learn`. If context was compacted and you're unsure whether
  a decision is pending, search progress.md before acting.
- Replies: present each checkpoint or question once, at the end of your reply,
  with its options beneath it. Don't restate it in a separate message, add a
  closing line after it, or quote these guides to the learner.
