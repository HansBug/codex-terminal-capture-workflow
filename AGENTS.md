# AGENTS.md

This repository publishes an agent skill that works with both OpenAI Codex and Anthropic Claude Code.
Treat it as both:

- the installable skill payload for Codex (`~/.codex/skills/terminal-capture-workflow`) and Claude Code (`~/.claude/skills/terminal-capture-workflow`)
- the public GitHub source of truth for that payload

## Purpose

`terminal-capture-workflow` produces terminal screenshots, staged PNG stills, GIFs, and MP4/WebM demos through two non-intrusive engines (`ttyd + Playwright` and `VHS`). No OS-level desktop input injection is used or added as a fallback.

## Structure

- `SKILL.md` is the skill body that both CLIs load.
- `CLAUDE.md` is a symlink to this file. Editing `AGENTS.md` covers both agents.
- `scripts/terminal_capture.py` and `scripts/render_ttyd_scenario.js` resolve `SKILL_ROOT` from `__file__`, so the install location does not change behavior.
- `references/` holds on-demand docs the skill reads during real work.
- `assets/` holds demo media referenced from the README.
- `agents/openai.yaml` is Codex-specific UI metadata; Claude Code ignores it.

## Editing Rules

1. Keep the two-engine story honest. Any scenario feature should state its behavior under both `ttyd` and `vhs`, or explicitly mark itself engine-specific.
2. When the invocation surface or default behavior changes, review `SKILL.md`, `README.md`, `README_zh.md`, `references/scenario-patterns.md`, and `agents/openai.yaml` together.
3. Scenario JSON files belong in user workspaces. Do not commit ad-hoc scenarios into this repo; reference examples belong in `references/`.
4. After script changes, run `python scripts/terminal_capture.py check` to confirm the environment probe still works.

## Validation Expectations

Before pushing a functional change, at minimum do all of these:

- `python3 -m py_compile scripts/terminal_capture.py`
- `python3 scripts/terminal_capture.py check`
- `python3 scripts/terminal_capture.py --help`

For behavior changes, also do real end-to-end checks:

- one `codex exec` render using `$terminal-capture-workflow`
- one `claude -p` render using `/terminal-capture-workflow` (or description-triggered)
- at least one `ttyd` still and one `vhs` motion output

## What Not To Do

- Do not introduce OS-level keyboard or mouse injection as a fallback.
- Do not silently change default engine selection.
- Do not move renderer anchoring away from `SKILL_ROOT`; absolute paths baked into scenarios make the skill non-portable between installs.
- Do not force the skill into a single engine when a flow legitimately needs both stills and motion.
