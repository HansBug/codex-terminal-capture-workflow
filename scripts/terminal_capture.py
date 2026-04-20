#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOTNAME = ".terminal-capture-output"
BROWSER_CANDIDATES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def format_duration(ms: int) -> str:
    if ms % 1000 == 0:
        return f"{ms // 1000}s"
    return f"{ms}ms"


def escape_vhs_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def escape_vhs_regex(pattern: str) -> str:
    return pattern.replace("/", "\\/")


def resolve_wait_pattern(step: dict[str, Any], engine: str) -> str | None:
    if "pattern_by_engine" in step:
        return step["pattern_by_engine"].get(engine) or step.get("pattern")
    if "wait_for_text_by_engine" in step:
        return step["wait_for_text_by_engine"].get(engine) or step.get("wait_for_text")
    return step.get("pattern") or step.get("wait_for_text")


def run_checked(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )


def find_on_path(name: str) -> str | None:
    return shutil.which(name)


def have_pillow() -> bool:
    return importlib.util.find_spec("PIL") is not None


def detect_playwright_package() -> bool:
    return (SKILL_ROOT / "node_modules" / "playwright" / "package.json").exists()


def detect_system_browser() -> str | None:
    for candidate in BROWSER_CANDIDATES:
        resolved = find_on_path(candidate)
        if resolved:
            return resolved
    return None


def detect_playwright_browser() -> str | None:
    if not detect_playwright_package():
        return None

    script = """
const fs = require('fs');
try {
  const { chromium } = require('playwright');
  const executable = chromium.executablePath();
  if (executable && fs.existsSync(executable)) {
    process.stdout.write(executable);
  }
} catch (error) {}
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=SKILL_ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None

    browser_path = result.stdout.strip()
    return browser_path or None


def detect_environment() -> dict[str, Any]:
    tools = {
        "python3": find_on_path("python3") or sys.executable,
        "node": find_on_path("node"),
        "npm": find_on_path("npm"),
        "ttyd": find_on_path("ttyd"),
        "vhs": find_on_path("vhs"),
        "ffmpeg": find_on_path("ffmpeg"),
        "ffprobe": find_on_path("ffprobe"),
        "less": find_on_path("less"),
        "apt": find_on_path("apt") or find_on_path("apt-get"),
    }
    extras = {
        "python_pillow": have_pillow(),
        "playwright_package": detect_playwright_package(),
    }
    extras["system_browser"] = detect_system_browser()
    extras["playwright_browser"] = detect_playwright_browser()

    capabilities = {
        "ttyd_screenshots": bool(
            tools["ttyd"]
            and tools["node"]
            and tools["npm"]
            and extras["playwright_package"]
            and (extras["system_browser"] or extras["playwright_browser"])
        ),
        "vhs_media": bool(tools["vhs"] and tools["ffmpeg"]),
        "vhs_stills": bool(tools["vhs"] and tools["ffmpeg"]),
        "frame_extraction": bool(tools["ffmpeg"]),
        "media_probe": bool(tools["ffprobe"]),
        "autocrop_pngs": extras["python_pillow"],
    }

    return {
        "system": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "skill_root": str(SKILL_ROOT),
        },
        "tools": tools,
        "extras": extras,
        "capabilities": capabilities,
        "install_commands": build_install_commands(tools, extras),
    }


def build_install_commands(tools: dict[str, str | None], extras: dict[str, Any]) -> dict[str, list[str]]:
    commands: dict[str, list[str]] = {}

    apt_packages: list[str] = []
    if not tools["ttyd"]:
        apt_packages.append("ttyd")
    if not tools["ffmpeg"]:
        apt_packages.append("ffmpeg")
    if not tools["less"]:
        apt_packages.append("less")
    if not tools["node"]:
        apt_packages.append("nodejs")
    if not tools["npm"]:
        apt_packages.append("npm")
    if not extras["python_pillow"]:
        apt_packages.append("python3-pil")

    if tools["apt"] and apt_packages:
        commands["apt"] = [
            "sudo apt update",
            f"sudo apt install -y {' '.join(sorted(dict.fromkeys(apt_packages)))}",
        ]

    if not tools["vhs"]:
        commands["vhs"] = [
            "sudo mkdir -p /etc/apt/keyrings",
            "curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg",
            "echo \"deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *\" | sudo tee /etc/apt/sources.list.d/charm.list >/dev/null",
            "sudo apt update",
            "sudo apt install -y vhs",
        ]

    if not extras["playwright_package"]:
        commands["playwright_package"] = [
            f"cd {shlex_quote(str(SKILL_ROOT))}",
            "npm install",
        ]

    if not extras["system_browser"] and not extras["playwright_browser"]:
        commands["playwright_browser"] = [
            f"cd {shlex_quote(str(SKILL_ROOT))}",
            "npx playwright install chromium",
        ]

    return commands


def shlex_quote(text: str) -> str:
    return shlex.quote(text)


def print_check_report(environment: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(environment, indent=2))
        return

    print("Environment report for terminal-capture-workflow")
    print(f"Skill root: {environment['system']['skill_root']}")
    print(f"Platform: {environment['system']['platform']}")
    print(f"Python: {environment['system']['python']}")
    print("")
    print("Capabilities:")
    for key, value in environment["capabilities"].items():
        status = "ready" if value else "blocked"
        print(f"  - {key}: {status}")
    print("")
    print("Detected tools:")
    for key, value in environment["tools"].items():
        print(f"  - {key}: {value or 'missing'}")
    print("")
    print("Detected extras:")
    for key, value in environment["extras"].items():
        print(f"  - {key}: {value or 'missing'}")

    if environment["install_commands"]:
        print("")
        print("Suggested install commands:")
        for label, commands in environment["install_commands"].items():
            print(f"  [{label}]")
            for command in commands:
                print(f"    {command}")


def normalize_scenario_path(raw_path: str) -> Path:
    scenario_path = Path(raw_path)
    if not scenario_path.is_absolute():
        scenario_path = (Path.cwd() / scenario_path).resolve()
    return scenario_path


def default_output_root(cwd: Path) -> Path:
    return cwd / DEFAULT_OUTPUT_ROOTNAME


def parse_fraction(text: str | None) -> float | None:
    if not text or text == "0/0":
        return None
    return float(Fraction(text))


def probe_media(path: Path) -> dict[str, Any]:
    if not find_on_path("ffprobe"):
        raise RuntimeError("ffprobe is required for media probing. Install ffmpeg first.")

    result = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        path.parent,
    )
    data = json.loads(result.stdout)
    video_stream = next((stream for stream in data.get("streams", []) if stream.get("codec_type") == "video"), {})
    format_info = data.get("format", {})
    duration_raw = format_info.get("duration")
    duration_seconds = float(duration_raw) if duration_raw else None
    fps = parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

    return {
        "path": str(path),
        "duration_seconds": duration_seconds,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": fps,
        "codec": video_stream.get("codec_name"),
    }


def suggested_review_times(duration_seconds: float | None) -> list[str]:
    if not duration_seconds or duration_seconds <= 0.15:
        return []

    raw_points = [duration_seconds * ratio for ratio in (0.2, 0.5, 0.8)]
    clipped = [point for point in raw_points if point < duration_seconds]
    unique_points = sorted({max(0.05, round(point, 2)) for point in clipped})
    return [f"{point:g}" for point in unique_points]


def scenario_cwd(scenario_path: Path, scenario: dict[str, Any], cli_cwd: str | None) -> Path:
    if cli_cwd:
        return Path(cli_cwd).resolve()
    if scenario.get("cwd"):
        return Path(scenario["cwd"]).resolve()
    return scenario_path.parent.resolve()


def autocrop_png(path: Path, padding: int) -> None:
    if not have_pillow():
        return

    from PIL import Image, ImageChops

    image = Image.open(path)
    background = Image.new(image.mode, image.size, image.getpixel((0, 0)))
    diff = ImageChops.difference(image, background)
    bbox = diff.getbbox()
    if not bbox:
        return

    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    image.crop((left, top, right, bottom)).save(path)


def postprocess_screenshots(scenario: dict[str, Any], out_dir: Path) -> None:
    screenshot_cfg = scenario.get("screenshots", {})
    if not screenshot_cfg.get("autocrop", True):
        return
    if not have_pillow():
        return

    padding = screenshot_cfg.get("padding", 18)
    for png_path in sorted(out_dir.glob("*.png")):
        autocrop_png(png_path, padding)


def build_vhs_tape(scenario: dict[str, Any], out_dir: Path) -> str:
    cfg = scenario.get("vhs", {})
    scenario_name = scenario["name"]
    lines: list[str] = []
    screenshot_settle_ms = cfg.get("screenshotSettleMs", 120)

    for ext in cfg.get("outputs", ["mp4"]):
        lines.append(f'Output "{(out_dir / f"{scenario_name}.{ext}").as_posix()}"')

    requires = list(dict.fromkeys(["bash", *scenario.get("requires", [])]))
    lines.extend(
        [
            "",
            *[f"Require {program}" for program in requires],
            'Set Shell "bash"',
            f'Set FontSize {cfg.get("fontSize", 22)}',
            f'Set Width {cfg.get("width", 1280)}',
            f'Set Height {cfg.get("height", 760)}',
            f'Set Padding {cfg.get("padding", 24)}',
            f'Set WindowBar {cfg.get("windowBar", "Colorful")}',
            f'Set BorderRadius {cfg.get("borderRadius", 10)}',
            f'Set Theme "{cfg.get("theme", "Ubuntu")}"',
            f'Set TypingSpeed {cfg.get("typingSpeed", "35ms")}',
            f'Set Framerate {cfg.get("framerate", 30)}',
        ]
    )

    if "playbackSpeed" in cfg:
        lines.append(f'Set PlaybackSpeed {cfg["playbackSpeed"]}')

    if cfg.get("waitTimeout"):
        lines.append(f'Set WaitTimeout {format_duration(cfg["waitTimeout"])}')

    lines.append("")

    for step in scenario.get("steps", []):
        action = step["action"]

        if action == "sleep":
            lines.append(f'Sleep {format_duration(step["ms"])}')
        elif action == "type":
            lines.append(f'Type "{escape_vhs_text(step["text"])}"')
        elif action == "press":
            key = step["key"]
            repeat = f' {step["repeat"]}' if step.get("repeat", 1) != 1 else ""
            if key.startswith("Control+"):
                lines.append(f'Ctrl+{key[len("Control+") :]}')
            elif key.startswith("Ctrl+"):
                lines.append(key)
            elif len(key) == 1 and key.isprintable():
                lines.append(f'Type "{escape_vhs_text(key)}"')
            else:
                lines.append(f"{key}{repeat}")
        elif action == "wait_for_text":
            timeout = step.get("timeout_ms")
            timeout_part = f'@{format_duration(timeout)}' if timeout else ""
            pattern = resolve_wait_pattern(step, "vhs")
            lines.append(f'Wait+Screen{timeout_part} /{escape_vhs_regex(pattern)}/')
        elif action == "screenshot":
            screenshot_path = out_dir / f'{step["name"]}.png'
            lines.append(f'Screenshot "{screenshot_path.as_posix()}"')
            lines.append(f"Sleep {format_duration(screenshot_settle_ms)}")
        elif action == "command":
            if step.get("clear_before"):
                lines.append("Ctrl+L")
                lines.append("Sleep 120ms")
            lines.append(f'Type "{escape_vhs_text(step["text"])}"')
            if step.get("typed_shot"):
                typed_path = out_dir / f'{step["typed_shot"]}.png'
                lines.append(f'Screenshot "{typed_path.as_posix()}"')
                lines.append(f"Sleep {format_duration(screenshot_settle_ms)}")
            lines.append("Enter")
            wait_pattern = resolve_wait_pattern(step, "vhs")
            if wait_pattern:
                timeout = step.get("timeout_ms")
                timeout_part = f'@{format_duration(timeout)}' if timeout else ""
                lines.append(f'Wait+Screen{timeout_part} /{escape_vhs_regex(wait_pattern)}/')
            else:
                lines.append(f'Sleep {format_duration(step.get("result_delay_ms", 900))}')
            if step.get("result_shot"):
                result_path = out_dir / f'{step["result_shot"]}.png'
                lines.append(f'Screenshot "{result_path.as_posix()}"')
                lines.append(f"Sleep {format_duration(screenshot_settle_ms)}")
        elif action == "hide":
            lines.append("Hide")
        elif action == "show":
            lines.append("Show")
        else:
            raise ValueError(f"Unsupported VHS action: {action}")

    lines.append("")
    return "\n".join(lines)


def ensure_engine_ready(engine: str, environment: dict[str, Any]) -> None:
    capabilities = environment["capabilities"]
    install_commands = environment["install_commands"]
    missing_reason = None

    if engine == "ttyd" and not capabilities["ttyd_screenshots"]:
        missing_reason = "ttyd screenshot rendering is blocked"
    elif engine == "vhs" and not capabilities["vhs_media"]:
        missing_reason = "VHS rendering is blocked"
    elif engine == "all":
        blocked = []
        if not capabilities["ttyd_screenshots"]:
            blocked.append("ttyd")
        if not capabilities["vhs_media"]:
            blocked.append("vhs")
        if blocked:
            missing_reason = f"requested engines are blocked: {', '.join(blocked)}"

    if missing_reason is None:
        return

    lines = [missing_reason + "."]
    if install_commands:
        lines.append("Run `python scripts/terminal_capture.py check` and use the suggested install commands.")
        for label, commands in install_commands.items():
            lines.append(f"[{label}]")
            lines.extend(commands)
    raise RuntimeError("\n".join(lines))


def render_ttyd(
    scenario_path: Path,
    scenario: dict[str, Any],
    output_root: Path,
    environment: dict[str, Any],
) -> Path:
    out_dir = output_root / "ttyd" / scenario["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    browser_path = environment["extras"]["system_browser"] or environment["extras"]["playwright_browser"]
    if browser_path:
        env["TERMINAL_CAPTURE_BROWSER"] = browser_path

    run_checked(
        [
            "node",
            str(SKILL_ROOT / "scripts" / "render_ttyd_scenario.js"),
            str(scenario_path),
            str(out_dir),
        ],
        SKILL_ROOT,
        env=env,
    )
    postprocess_screenshots(scenario, out_dir)
    return out_dir


def render_vhs(scenario: dict[str, Any], output_root: Path) -> tuple[Path, Path]:
    out_dir = output_root / "vhs" / scenario["name"]
    generated_dir = output_root / "generated"
    scenario_root = Path(scenario["cwd"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    tape_path = generated_dir / f'{scenario["name"]}.tape'
    tape_path.write_text(build_vhs_tape(scenario, out_dir))
    subprocess.run(["vhs", str(tape_path)], cwd=scenario_root, check=True)
    postprocess_screenshots(scenario, out_dir)
    return tape_path, out_dir


def render_command(args: argparse.Namespace) -> None:
    scenario_path = normalize_scenario_path(args.scenario)
    scenario = load_scenario(scenario_path)
    resolved_cwd = scenario_cwd(scenario_path, scenario, args.cwd)
    scenario["cwd"] = str(resolved_cwd)

    output_root = Path(args.output_root).resolve() if args.output_root else default_output_root(resolved_cwd)
    output_root.mkdir(parents=True, exist_ok=True)

    environment = detect_environment()
    ensure_engine_ready(args.engine, environment)

    created: list[tuple[str, Path]] = []
    if args.engine in {"ttyd", "all"}:
        created.append(("ttyd", render_ttyd(scenario_path, scenario, output_root, environment)))
    if args.engine in {"vhs", "all"}:
        tape_path, out_dir = render_vhs(scenario, output_root)
        created.append(("vhs_tape", tape_path))
        created.append(("vhs", out_dir))

    for label, path in created:
        print(f"{label}: {path}")


def extract_frames_command(args: argparse.Namespace) -> None:
    input_path = Path(args.media).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Media file not found: {input_path}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_path.parent / f"{input_path.stem}-frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    times = [item.strip() for item in args.times.split(",") if item.strip()]
    created = []
    for index, timestamp in enumerate(times, start=1):
        output_path = output_dir / f"{input_path.stem}-{index:02d}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                timestamp,
                "-i",
                str(input_path),
                "-frames:v",
                "1",
                "-update",
                "1",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(
                "No frame was created at "
                f"{timestamp}. The media may be shorter than that timestamp; pick an earlier time. "
                f"Run `python scripts/terminal_capture.py probe-media {input_path}` if you need the exact duration."
            )
        created.append(output_path)

    for path in created:
        print(path)


def probe_media_command(args: argparse.Namespace) -> None:
    input_path = Path(args.media).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Media file not found: {input_path}")

    info = probe_media(input_path)
    print(f"Media: {info['path']}")
    if info["duration_seconds"] is not None:
        print(f"Duration: {info['duration_seconds']:.3f}s")
    else:
        print("Duration: unknown")
    if info["width"] and info["height"]:
        print(f"Resolution: {info['width']}x{info['height']}")
    if info["fps"] is not None:
        print(f"FPS: {info['fps']:.2f}")
    if info["codec"]:
        print(f"Codec: {info['codec']}")

    suggested = suggested_review_times(info["duration_seconds"])
    if suggested:
        print(f"Suggested review times: {','.join(suggested)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check, render, and inspect terminal capture scenarios for ttyd and VHS workflows."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Inspect local dependencies and print install commands.")
    check_parser.add_argument("--json", action="store_true", help="Print the environment report as JSON.")

    render_parser = subparsers.add_parser("render", help="Render a scenario through ttyd, VHS, or both.")
    render_parser.add_argument("engine", choices=["ttyd", "vhs", "all"])
    render_parser.add_argument("scenario", help="Path to a scenario JSON file.")
    render_parser.add_argument("--cwd", help="Override the scenario working directory.")
    render_parser.add_argument("--output-root", help="Directory where outputs should be written.")

    extract_parser = subparsers.add_parser("extract-frames", help="Extract representative frames for visual QA.")
    extract_parser.add_argument("media", help="Path to a GIF, MP4, or WebM file.")
    extract_parser.add_argument("--times", required=True, help="Comma-separated timestamps, for example 0.5,1.2,2.0")
    extract_parser.add_argument("--output-dir", help="Directory to store extracted PNG frames.")

    probe_parser = subparsers.add_parser("probe-media", help="Print duration and suggested review timestamps.")
    probe_parser.add_argument("media", help="Path to a GIF, MP4, or WebM file.")

    args = parser.parse_args()

    if args.command == "check":
        print_check_report(detect_environment(), args.json)
        return
    if args.command == "render":
        render_command(args)
        return
    if args.command == "extract-frames":
        extract_frames_command(args)
        return
    if args.command == "probe-media":
        probe_media_command(args)
        return

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    main()
