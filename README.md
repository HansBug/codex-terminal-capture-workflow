# Terminal Capture Workflow

[English](#english) | [简体中文](#简体中文)

## English

For Chinese, see [简体中文](#简体中文).

`terminal-capture-workflow` is a Codex skill for creating terminal screenshots, staged PNG stills, GIFs, MP4/WebM demos, and visual QA frames without OS-level desktop input injection.

### What it covers

- `ttyd + Playwright` screenshots for docs, guides, reports, and issue comments
- `VHS` rendering for `gif`, `mp4`, `webm`, and staged screenshots
- Interactive prompts such as `y/N`, wizard-style multi-step flows, and confirmation screens
- Long output via paged captures such as `less -R`
- Visual review by extracting representative frames from rendered media
- User-specified window sizes for both ttyd and VHS outputs

### Repository structure

- [`SKILL.md`](./SKILL.md): Codex-facing workflow instructions
- [`scripts/terminal_capture.py`](./scripts/terminal_capture.py): environment check, render orchestration, and frame extraction
- [`scripts/render_ttyd_scenario.js`](./scripts/render_ttyd_scenario.js): ttyd + Playwright renderer
- [`references/environment-and-install.md`](./references/environment-and-install.md): dependency and installation guidance
- [`references/scenario-patterns.md`](./references/scenario-patterns.md): scenario schema and common patterns

### Install dependencies

Debian or Ubuntu base packages:

```bash
sudo apt update
sudo apt install -y ttyd ffmpeg less python3-pil nodejs npm
```

Install VHS:

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null
sudo apt update
sudo apt install -y vhs
```

Install the Playwright package in the skill directory:

```bash
npm install
```

If no system Chrome or Chromium browser is available:

```bash
npx playwright install chromium
```

### Local skill installation

The default auto-discovery location is:

```bash
~/.codex/skills/terminal-capture-workflow
```

One convenient setup is a symlink:

```bash
ln -sfn /path/to/terminal-capture-workflow ~/.codex/skills/terminal-capture-workflow
```

### Basic usage

Check the environment first:

```bash
python scripts/terminal_capture.py check
```

Render a scenario:

```bash
python scripts/terminal_capture.py render all /path/to/scenario.json
```

Extract review frames from a video or GIF:

```bash
python scripts/terminal_capture.py extract-frames /path/to/demo.mp4 --times 0.5,1.0,1.5
```

Probe a rendered media file before choosing frame times:

```bash
python scripts/terminal_capture.py probe-media /path/to/demo.mp4
```

### Notes

- Put scenario JSON files in the target workspace, not in the skill directory.
- Prefer visible-text waits over fixed sleeps.
- Wrap fragile shell pipelines in workspace helper scripts before using them in a scenario.
- Use `pattern_by_engine` when ttyd and VHS prompts differ.
- Use `hide` and `show` for homepage or teaser-style captures.
- Short teaser clips can be well under one second. Run `probe-media` before `extract-frames` so the chosen timestamps are inside the clip duration.

## 简体中文

For English, see [English](#english).

`terminal-capture-workflow` 是一个 Codex skill，用来生成终端截图、分阶段 PNG、GIF、MP4/WebM 演示，以及用于人工视觉验收的抽帧结果，而且不依赖操作系统级别的桌面鼠标键盘注入。

### 覆盖能力

- 面向文档、操作指引、报告、评论区的 `ttyd + Playwright` 截图
- 面向 `gif`、`mp4`、`webm` 和关键帧截图的 `VHS` 渲染
- `y/N` 确认、向导式多步交互、确认页等交互场景
- 通过 `less -R` 等分页方式处理长输出
- 从视频或 GIF 中抽取代表性帧做视觉验收
- 同时支持用户指定 ttyd 和 VHS 的窗口大小

### 仓库结构

- [`SKILL.md`](./SKILL.md)：给 Codex 用的工作流说明
- [`scripts/terminal_capture.py`](./scripts/terminal_capture.py)：环境检测、统一渲染入口、抽帧
- [`scripts/render_ttyd_scenario.js`](./scripts/render_ttyd_scenario.js)：ttyd + Playwright 渲染器
- [`references/environment-and-install.md`](./references/environment-and-install.md)：依赖与安装说明
- [`references/scenario-patterns.md`](./references/scenario-patterns.md)：scenario 结构与常见模式

### 安装依赖

Debian 或 Ubuntu 基础包：

```bash
sudo apt update
sudo apt install -y ttyd ffmpeg less python3-pil nodejs npm
```

安装 VHS：

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null
sudo apt update
sudo apt install -y vhs
```

在 skill 目录里安装 Playwright 包：

```bash
npm install
```

如果系统里没有 Chrome 或 Chromium：

```bash
npx playwright install chromium
```

### 本地安装 skill

默认自动发现路径是：

```bash
~/.codex/skills/terminal-capture-workflow
```

一个方便的做法是建立软链接：

```bash
ln -sfn /path/to/terminal-capture-workflow ~/.codex/skills/terminal-capture-workflow
```

### 基本使用

先检查环境：

```bash
python scripts/terminal_capture.py check
```

渲染 scenario：

```bash
python scripts/terminal_capture.py render all /path/to/scenario.json
```

从视频或 GIF 中抽取验收帧：

```bash
python scripts/terminal_capture.py extract-frames /path/to/demo.mp4 --times 0.5,1.0,1.5
```

在选择抽帧时间点前先探测媒体信息：

```bash
python scripts/terminal_capture.py probe-media /path/to/demo.mp4
```

### 说明

- scenario JSON 应该放在目标工作区，而不是 skill 目录里。
- 优先使用“等待可见文本”而不是固定 sleep。
- 对脆弱的 shell pipeline，先在工作区写成辅助脚本，再放进 scenario。
- 当 ttyd 和 VHS 的 prompt 不一致时，用 `pattern_by_engine`。
- 主页 teaser 一类素材可以用 `hide` 和 `show` 控制可见步骤。
- 很短的 teaser 视频可能不到 1 秒，抽帧前先跑 `probe-media`，再选落在素材时长内的时间点。
