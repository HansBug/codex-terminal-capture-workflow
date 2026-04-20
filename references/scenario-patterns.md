# Scenario Patterns

Use this reference when building or editing a scenario JSON.

## Shared Structure

```json
{
  "name": "example-name",
  "cwd": "/abs/path/to/workdir",
  "shell": ["bash", "--noprofile", "--norc", "-i"],
  "requires": ["python3"],
  "ttyd": {
    "fontSize": 20,
    "typingDelayMs": 20,
    "cursorBlink": true,
    "viewport": {
      "width": 1400,
      "height": 560,
      "deviceScaleFactor": 2
    },
    "theme": {
      "background": "#300a24"
    }
  },
  "vhs": {
    "fontSize": 22,
    "width": 1280,
    "height": 760,
    "padding": 24,
    "windowBar": "Colorful",
    "borderRadius": 10,
    "theme": "Ubuntu",
    "typingSpeed": "35ms",
    "framerate": 30,
    "outputs": ["mp4", "gif"],
    "endHoldSeconds": 3
  },
  "screenshots": {
    "autocrop": true,
    "padding": 18
  },
  "steps": []
}
```

For motion outputs, `endHoldSeconds` controls how long the final frame stays on screen after the last action completes. If omitted, GIF/MP4/WebM outputs default to a 2-second final hold. Set it to `0` to disable the extra hold.

## Step Types

- `command`
  - Type a full command, optionally clear first, optionally capture the typed state, then wait for output.
- `type`
  - Type text without pressing enter yet.
- `press`
  - Press a key such as `Enter`, `PageDown`, `Control+L`, or `q`.
- `wait_for_text`
  - Wait until the current visible screen contains the expected text.
- `screenshot`
  - Capture a still at the current stage.
- `sleep`
  - Explicit wait when there is no better observable condition.
- `hide` and `show`
  - VHS-only visibility control for teaser captures.

## Interactive Confirmation Pattern

Use when a command asks for `y/N`, a password, or another short confirmation.

```json
[
  {
    "action": "command",
    "text": "python3 scripts/confirm_demo.py",
    "clear_before": true,
    "typed_shot": "01-command-typed",
    "wait_for_text": "Apply migration now\\? \\[y/N\\]",
    "timeout_ms": 10000,
    "result_shot": "02-prompt-visible"
  },
  { "action": "sleep", "ms": 600 },
  { "action": "type", "text": "y" },
  { "action": "screenshot", "name": "03-confirmation-typed" },
  { "action": "press", "key": "Enter" },
  {
    "action": "wait_for_text",
    "pattern": "Done\\. New schema version: 2026\\.04",
    "timeout_ms": 10000
  },
  { "action": "screenshot", "name": "04-finished" }
]
```

Add a brief `sleep` before the reply when the prompt itself must be legible in a GIF or homepage demo. Still screenshots usually do not need this, but motion assets often do.

## Multi-Step Wizard Pattern

Use when the flow alternates between prompts and replies.

```json
[
  {
    "action": "command",
    "text": "python3 scripts/wizard_demo.py",
    "clear_before": true,
    "wait_for_text": "Project name:",
    "timeout_ms": 10000,
    "result_shot": "01-project-prompt"
  },
  { "action": "type", "text": "docs-homepage-demo" },
  { "action": "press", "key": "Enter" },
  { "action": "wait_for_text", "pattern": "Package manager", "timeout_ms": 10000 },
  { "action": "screenshot", "name": "02-package-manager-prompt" }
]
```

## Long Output Pattern

Do not try to fit a long terminal transcript into one screenshot. Wrap the command in a helper script if the pipeline is awkward, then page through `less -R`.

```json
[
  {
    "action": "command",
    "text": "bash scripts/run_long_output_pager.sh",
    "clear_before": true,
    "wait_for_text": "Section 1: rollout checks",
    "timeout_ms": 10000,
    "result_shot": "01-page-1"
  },
  { "action": "press", "key": "PageDown" },
  { "action": "wait_for_text", "pattern": "Section 2: rollout checks", "timeout_ms": 10000 },
  { "action": "screenshot", "name": "02-page-2" }
]
```

## Engine-Specific Wait Pattern

Use when ttyd and VHS show different prompts or status text.

```json
{
  "action": "wait_for_text",
  "pattern_by_engine": {
    "ttyd": "bash-5\\.2\\$",
    "vhs": ">"
  },
  "timeout_ms": 10000
}
```

## Teaser Pattern

Use `hide` and `show` to skip setup while still waiting for a meaningful visible state before the reveal.

```json
[
  { "action": "hide" },
  {
    "action": "command",
    "text": "python3 scripts/confirm_demo.py",
    "clear_before": true,
    "wait_for_text": "Apply migration now\\? \\[y/N\\]",
    "timeout_ms": 10000
  },
  { "action": "show" },
  { "action": "screenshot", "name": "01-prompt-ready" }
]
```

## Practical Rules

- Keep the scenario in the user workspace, not in the skill directory.
- When the user specifies a size, reflect it in both the ttyd viewport and the VHS canvas.
- Prefer waiting on visible text over fixed sleeps.
- If the output command is complex or shell-fragile, move it into a wrapper script in the user workspace.
- If the asset is customer-facing, add explicit screenshot steps at the exact moments the user will care about during review.
- For GIF or video review, probe the rendered media first and choose extraction timestamps that are inside the actual clip duration.
- For motion assets, hold critical beats such as confirmations or summaries for `400-800ms` when they need to be readable in the animation itself.
- Motion outputs also hold on the final state by default for 2 seconds. Increase `vhs.endHoldSeconds` when the ending state must be studied, or set it to `0` when you explicitly want an immediate cut.
