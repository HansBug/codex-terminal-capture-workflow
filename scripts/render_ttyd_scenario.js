const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BROWSER_CANDIDATES = [
  "google-chrome",
  "google-chrome-stable",
  "chromium",
  "chromium-browser",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findExecutableOnPath(name) {
  const pathValue = process.env.PATH || "";
  for (const dir of pathValue.split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.join(dir, name);
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function resolveBrowserExecutable() {
  if (process.env.TERMINAL_CAPTURE_BROWSER && fs.existsSync(process.env.TERMINAL_CAPTURE_BROWSER)) {
    return process.env.TERMINAL_CAPTURE_BROWSER;
  }

  for (const candidate of BROWSER_CANDIDATES) {
    const resolved = findExecutableOnPath(candidate);
    if (resolved) {
      return resolved;
    }
  }

  return null;
}

async function launchBrowser() {
  const executablePath = resolveBrowserExecutable();
  const launchOptions = { headless: true };

  if (executablePath) {
    try {
      return await chromium.launch({ ...launchOptions, executablePath });
    } catch (error) {
      // Fall through to the default Playwright browser.
    }
  }

  try {
    return await chromium.launch(launchOptions);
  } catch (error) {
    throw new Error(
      "Unable to launch a browser for ttyd rendering. Install a system Chrome/Chromium browser or run `npm install` and `npx playwright install chromium` in the skill directory.",
    );
  }
}

async function waitForServer(url, timeoutMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await sleep(200);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function waitForText(page, pattern, timeoutMs = 10000, flags = "m") {
  await page.waitForFunction(
    ({ source, regexFlags }) => {
      const text = document.querySelector(".xterm-rows")?.innerText || "";
      return new RegExp(source, regexFlags).test(text);
    },
    { source: pattern, regexFlags: flags },
    { timeout: timeoutMs },
  );
}

function resolveWaitPattern(step) {
  if (step.pattern_by_engine && step.pattern_by_engine.ttyd) {
    return step.pattern_by_engine.ttyd;
  }
  if (step.wait_for_text_by_engine && step.wait_for_text_by_engine.ttyd) {
    return step.wait_for_text_by_engine.ttyd;
  }
  return step.pattern || step.wait_for_text;
}

async function focusTerminal(page) {
  await page.locator(".xterm-helper-textarea").focus();
}

async function capture(page, outDir, name) {
  await page.locator(".xterm-rows").screenshot({
    path: path.join(outDir, `${name}.png`),
  });
}

function normalizeKey(key) {
  if (key.startsWith("Ctrl+")) {
    return `Control+${key.slice(5)}`;
  }
  return key;
}

async function pressKey(page, key, repeat = 1) {
  await focusTerminal(page);
  for (let idx = 0; idx < repeat; idx += 1) {
    await page.keyboard.press(normalizeKey(key));
  }
}

async function runCommandStep(page, outDir, step, typingDelayMs) {
  if (step.clear_before) {
    await pressKey(page, "Control+L");
    await sleep(120);
  }

  await focusTerminal(page);
  await page.keyboard.type(step.text, { delay: typingDelayMs });

  if (step.typed_shot) {
    await capture(page, outDir, step.typed_shot);
  }

  await page.keyboard.press("Enter");

  const waitPattern = resolveWaitPattern(step);
  if (waitPattern) {
    await waitForText(page, waitPattern, step.timeout_ms || 10000, step.flags || "m");
  } else {
    await sleep(step.result_delay_ms || 900);
  }

  if (step.result_shot) {
    await capture(page, outDir, step.result_shot);
  }
}

async function runStep(page, outDir, step, typingDelayMs) {
  switch (step.action) {
    case "sleep":
      await sleep(step.ms);
      return;
    case "type":
      await focusTerminal(page);
      await page.keyboard.type(step.text, { delay: typingDelayMs });
      return;
    case "press":
      await pressKey(page, step.key, step.repeat || 1);
      return;
    case "wait_for_text":
      await waitForText(page, resolveWaitPattern(step), step.timeout_ms || 10000, step.flags || "m");
      return;
    case "screenshot":
      await capture(page, outDir, step.name);
      return;
    case "command":
      await runCommandStep(page, outDir, step, typingDelayMs);
      return;
    case "hide":
    case "show":
      return;
    default:
      throw new Error(`Unsupported action: ${step.action}`);
  }
}

async function main() {
  const scenarioPath = process.argv[2];
  const outDir = process.argv[3];

  if (!scenarioPath || !outDir) {
    throw new Error("Usage: node render_ttyd_scenario.js <scenario.json> <out-dir>");
  }

  const scenario = JSON.parse(fs.readFileSync(scenarioPath, "utf8"));
  const ttydConfig = scenario.ttyd || {};
  const viewport = ttydConfig.viewport || {
    width: 1400,
    height: 560,
    deviceScaleFactor: 2,
  };
  const typingDelayMs = ttydConfig.typingDelayMs || 20;
  const port = 15000 + (process.pid % 10000);
  const clientOptions = [
    ["fontSize", String(ttydConfig.fontSize || 20)],
    ["cursorBlink", String(ttydConfig.cursorBlink !== false)],
    ["rendererType", ttydConfig.rendererType || "dom"],
  ];

  if (ttydConfig.theme) {
    clientOptions.push(["theme", JSON.stringify(ttydConfig.theme)]);
  }

  for (const [key, value] of ttydConfig.extraClientOptions || []) {
    clientOptions.push([key, value]);
  }

  fs.mkdirSync(outDir, { recursive: true });

  const ttydArgs = ["-p", String(port), "-W", "-w", scenario.cwd || process.cwd()];
  for (const [key, value] of clientOptions) {
    ttydArgs.push("-t", `${key}=${value}`);
  }
  ttydArgs.push(...(scenario.shell || ["bash", "--noprofile", "--norc", "-i"]));

  const ttyd = spawn("ttyd", ttydArgs, {
    cwd: scenario.cwd || process.cwd(),
    stdio: ["ignore", "pipe", "pipe"],
  });

  let serverLog = "";
  ttyd.stdout.on("data", (buf) => {
    serverLog += buf.toString();
  });
  ttyd.stderr.on("data", (buf) => {
    serverLog += buf.toString();
  });

  const cleanup = () => {
    if (!ttyd.killed) {
      ttyd.kill("SIGTERM");
    }
  };

  process.on("exit", cleanup);
  process.on("SIGINT", () => {
    cleanup();
    process.exit(130);
  });

  try {
    await waitForServer(`http://127.0.0.1:${port}`);

    const browser = await launchBrowser();
    const page = await browser.newPage({
      viewport: {
        width: viewport.width,
        height: viewport.height,
      },
      deviceScaleFactor: viewport.deviceScaleFactor || 2,
    });

    await page.goto(`http://127.0.0.1:${port}`, { waitUntil: "networkidle" });
    await page.locator(".xterm").waitFor();
    await focusTerminal(page);
    await sleep(400);

    for (const step of scenario.steps || []) {
      await runStep(page, outDir, step, typingDelayMs);
    }

    await browser.close();
    cleanup();
    process.stdout.write(`${outDir}\n`);
  } catch (error) {
    cleanup();
    process.stderr.write(`${serverLog}\n`);
    throw error;
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
