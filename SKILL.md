---
name: terminal-capture-workflow
description: Create staged terminal screenshots, PNG stills, GIFs, MP4/WebM demos, and visual QA artifacts without using OS-level desktop input injection. Use when Codex needs terminal capture assets for guides, operation manuals, reports, slide decks, changelogs, or homepage demos, especially for interactive prompts, multi-step CLI flows, long paged output, ttyd/Playwright rendering, VHS rendering, frame extraction, or visual inspection of generated terminal media.
---

# Terminal Capture Workflow

## Overview

Produce terminal assets through two non-intrusive engines:

- `ttyd + Playwright` for documentation-oriented screenshots
- `VHS` for `gif`, `mp4`, `webm`, and staged stills, with a default final hold on motion outputs so viewers can read the ending state
- A shared interaction model for arbitrary text input, multiline paste, key presses, modifier chords, and multi-step terminal/TUI flows

Always start by resolving the installed skill root, then run environment detection, choose the engine, author a scenario, render, visually inspect, and iterate.

## Skill Root

Before running any command from this skill, resolve the installed skill directory. The default location is usually:

- `~/.codex/skills/terminal-capture-workflow`

If that path does not exist, locate the repo copy that contains this `SKILL.md`. Do not assume the user workspace also contains `scripts/terminal_capture.py`; many workspaces only contain scenario files and helper demo scripts.

## Workflow

1. Resolve `SKILL_ROOT`, then run `python "$SKILL_ROOT/scripts/terminal_capture.py" check`.
2. Read the capability summary before planning the render.
3. If the requested output is blocked, stop and tell the user which dependencies are missing. Reuse the install commands printed by the check command instead of improvising package names.
4. Choose the engine:
   - Prefer `ttyd` for screenshots used in docs, guides, reports, or issue comments.
   - Prefer `vhs` for `gif`, `mp4`, `webm`, and teaser-style captures.
   - Prefer `all` when the user wants both stills and motion assets from the same flow.
   - If `ttyd` is blocked but `vhs` is ready, use VHS `Screenshot` steps as a fallback for still images.
5. Create or update a scenario JSON in the user workspace. Set the requested window size in:
   - `ttyd.viewport.width`
   - `ttyd.viewport.height`
   - `vhs.width`
   - `vhs.height`
   - `vhs.endHoldSeconds` when the user wants a specific frozen ending length for GIF or video. If it is omitted, motion outputs default to a short final hold.
6. For large output, do not force everything into one frame. Route the command through `less -R` or another pager and capture specific pages with `PageDown`.
7. For fragile commands, wrap them in a helper shell script inside the user workspace instead of keeping a long pipeline inline in the scenario.
8. Use `input` steps when the user needs more than a single command or reply. Compose `text`, `paste`, `press`, and `sleep` events instead of faking the flow with a giant inline shell command.
9. When one single shell command is visually too long for the requested terminal width, prefer `command` with `wrap_at_columns` plus prompt-width hints instead of relying on the terminal emulator's natural wrap. This keeps typed long commands readable and avoids overwrite artifacts.
10. Prefer `ttyd + Playwright` when the user needs exotic key chords that VHS may reject, especially multi-modifier special-key combinations. Use VHS when the user primarily needs motion output.
11. For `tmux`, `vim`/`vi`, `less`, `fzf`, and other TUI flows, plan around visible state changes and explicit waits, not fixed timing guesses.
12. Render with `python "$SKILL_ROOT/scripts/terminal_capture.py" render <engine> <scenario-path> [--output-root <dir>]`.
13. If the user asked for visual verification, or the asset is customer-facing, inspect the final stills directly. For video or GIF, first run `python "$SKILL_ROOT/scripts/terminal_capture.py" probe-media <media>` to get the duration and suggested timestamps, then extract representative frames with `python "$SKILL_ROOT/scripts/terminal_capture.py" extract-frames <media> --times <comma-separated-seconds>`.
14. If the visual review fails, adjust the scenario and rerender. Do not stop at “the command succeeded” when the artifact itself is the deliverable.
15. If a prompt or confirmation beat is too brief in motion output, add a short `sleep` step before the reply so the state is legible in GIF or video, then rerender.

## Scenario Rules

- Keep `cwd` aligned with the target project or scratch directory.
- Keep the scenario in the user workspace, but keep the renderer commands anchored to `SKILL_ROOT`.
- Use `pattern_by_engine` or `wait_for_text_by_engine` when shell prompts differ between ttyd and VHS.
- Use `type`, `paste`, `press`, and `input` steps for real interactions instead of embedding everything in one shell command.
- For long `command` steps, use `wrap_at_columns`, and when needed also set `prompt_columns`, `continuation_prompt_columns`, and `wrap_indent` so wrapped shell input reflects the real terminal width instead of visually overwriting one line.
- Key names are normalized case-insensitively. Chords like `ctrl+b`, `ctrl+shift+*`, `ctrl+[`, `alt+enter`, and `shift+tab` can be represented directly in scenarios.
- Use `typed_shot`, `result_shot`, and explicit `screenshot` steps when the user cares about exact stages.
- Use `hide` and `show` to suppress setup in teaser videos.
- VHS `paste` is rendered as fast exact typing and does not depend on the system clipboard.
- Motion outputs automatically hold on the final frame for 2 seconds unless the scenario sets `vhs.endHoldSeconds` or `vhs.endHoldMs`.
- Use `screenshots.autocrop` for tighter documentation images. Disable it only when the user explicitly wants full-frame output.

## Visual Review

Inspect the generated media against the user’s actual concern, not just general aesthetics. Focus on:

- Whether the correct stage was captured
- Whether prompts or confirmations are visible before input
- Whether syntax highlighting and ANSI colors survived
- Whether the requested page of long output is the one shown
- Whether the chosen window size feels intentional
- Whether unwanted setup is hidden in teaser media
- Whether there is excessive whitespace that harms readability
- Whether frame-extraction timestamps are inside the actual media duration
- Whether the final state lingers long enough for a human viewer to read it

## References

- Read `references/environment-and-install.md` when dependencies are missing or the user asks what to install.
- Read `references/scenario-patterns.md` when building or editing a scenario for interactive flows, long output, teaser captures, or engine-specific wait rules.
