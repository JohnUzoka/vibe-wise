# VibeWise in Cline

These notes adapt Claude Code tool and command names for Cline (CLI, SDK, and
Kanban plugins). They don't change the learning behavior; follow SKILL.md and its
guides as written.

- Commands: `/vibe-wise:learn` is `/vibe-wise-learn`; `/vibe-wise:reset` is
  `/vibe-wise-reset`. Activate Learn or Reset only when the learner invokes them.
- Paths: `${CLAUDE_PLUGIN_ROOT}` is not expanded in Cline. The plugin root is two
  directories above this file (`../..`); guides such as `behavior.md` sit beside it.
- Files: where the guides say Read, use your file-reading tool (`read_files`). Where
  the guides say Glob, use your codebase search tool (`search_codebase` or shell
  file listing via `run_commands`). Reading plugin guides with your file-reading tool
  is preferred. Check optional learner-state files with a pattern or check that
  succeeds when they are missing.
- Choices: AskUserQuestion corresponds to `ask_question`. Use `ask_question` with the
  question text and options. If `ask_question` is unavailable in your environment,
  ask one plain-text question with the options listed beneath it. Then end your turn
  and wait for the learner's response.
- Restoration: the VibeWise plugin's `beforeRun` hook adds these reading
  instructions at the start of each run while learning is active. If context was
  compacted or you are unsure whether a decision is pending, search the entire
  `progress.md` before acting.
- Replies: present each checkpoint or question once, at the end of your reply,
  with its options beneath it. Don't restate it in a separate message, add a
  closing line after it, or quote these guides to the learner.
