# Environment And Install

Use this reference when `python scripts/terminal_capture.py check` reports blocked capabilities.

## Capability Mapping

- `ttyd_screenshots`
  - Needs `ttyd`, `node`, `npm`, the local `playwright` package, and either a system Chrome/Chromium browser or a Playwright-downloaded Chromium browser.
- `vhs_media`
  - Needs `vhs` and `ffmpeg`.
- `vhs_stills`
  - Same as `vhs_media`. VHS `Screenshot` can be used even when ttyd is unavailable.
- `frame_extraction`
  - Needs `ffmpeg`.
- `media_probe`
  - Needs `ffprobe`, which is typically installed together with `ffmpeg`.
- `autocrop_pngs`
  - Needs Pillow (`python3-pil` on Debian/Ubuntu).

## Debian Or Ubuntu Install Commands

Base packages:

```bash
sudo apt update
sudo apt install -y ttyd ffmpeg less python3-pil nodejs npm
```

VHS from Charm:

```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null
sudo apt update
sudo apt install -y vhs
```

Install the local Playwright package inside the skill directory:

```bash
cd <skill-root>
npm install
```

If the machine has no system Chrome or Chromium browser, install a Playwright-managed Chromium build:

```bash
cd <skill-root>
npx playwright install chromium
```

## Practical Rules

- If the user wants GIF, MP4, or WebM, prioritize making `vhs_media` ready.
- If the user wants visual QA on GIF or video outputs, run `probe-media` before choosing extraction timestamps.
- If the user only wants screenshots and `ttyd_screenshots` is blocked but `vhs_media` is ready, use VHS screenshots as a fallback instead of stopping.
- Do not guess package names when the environment check already printed exact install commands.
