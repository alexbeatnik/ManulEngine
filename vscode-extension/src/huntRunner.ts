import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { execFile, spawn, ChildProcess } from "child_process";
import * as vscode from "vscode";
import { PAUSE_MARKER, DEBUG_TERMINAL_NAME } from "./constants";

/**
 * Read the manulEngine.browser setting and return the CLI flags needed.
 * For native Playwright browsers (chromium, firefox, webkit) returns
 * ["--browser", name].  For system-installed channel browsers (chrome,
 * msedge) returns ["--browser", "chromium"] and sets MANUL_CHANNEL in
 * the env so the JSON config override is not required.
 */
export function getBrowserFlags(): { args: string[]; env: Record<string, string> } {
  const raw = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("browser", "chromium");
  const browser = (raw || "chromium").trim().toLowerCase();
  if (browser === "chrome" || browser === "msedge") {
    return { args: ["--browser", "chromium"], env: { MANUL_CHANNEL: browser } };
  }
  return { args: ["--browser", browser], env: {} };
}

/**
 * Probe candidate paths in order, then falls back to a one-time async
 * login-shell lookup using the user's configured shell (`vscode.env.shell` →
 * `$SHELL`), so fish/zsh/bash init scripts and tools like conda, pyenv, and
 * asdf that inject shims via shell hooks are correctly resolved.
 *
 * The shell result is cached per workspaceRoot so the async lookup runs at
 * most once per workspace per extension-host session.
 */

// Per-workspace cache of in-flight/resolved promises — concurrent calls for the
// same workspaceRoot share one lookup rather than each spawning a shell.
const _shellCache = new Map<string, Promise<string>>();

export async function findManulExecutable(workspaceRoot: string): Promise<string> {
  const custom = vscode.workspace
    .getConfiguration("manulEngine")
    .get<string>("manulPath", "")
    .trim();
  if (custom) {
    if (fs.existsSync(custom)) {
      return custom;
    }
    // Path is configured but doesn't exist — warn and fall through to auto-detection.
    vscode.window.showWarningMessage(
      `ManulEngine: configured manulPath "${custom}" not found. Falling back to auto-detection.`
    );
  }

  const isWin = process.platform === "win32";

  // Ordered list of static candidate paths to probe (synchronous, no overhead).
  // Unix-only paths are excluded on Windows to avoid spurious existsSync probes.
  const candidates: string[] = [
    // 1. Project-local venv — check common folder names (.venv, venv, env, .env)
    ...(['.venv', 'venv', 'env', '.env'].map((dir) =>
      isWin
        ? path.join(workspaceRoot, dir, 'Scripts', 'manul.exe')
        : path.join(workspaceRoot, dir, 'bin', 'manul')
    )),
    // 2+. Platform-specific user-level install locations
    ...(!isWin ? [
      // 2. pip --user install — Linux and macOS Intel common path
      path.join(os.homedir(), ".local", "bin", "manul"),
      // 3. macOS only: pip --user may install to ~/Library/Python/<ver>/bin.
      // Guard with platform and existsSync to avoid a thrown exception on Linux.
      ...(() => {
        if (process.platform !== "darwin") { return []; }
        const base = path.join(os.homedir(), "Library", "Python");
        if (!fs.existsSync(base)) { return []; }
        try {
          return fs.readdirSync(base)
            .map((v) => path.join(base, v, "bin", "manul"))
            .filter((p) => fs.existsSync(p));
        } catch { return []; }
      })(),
      // 4. pipx-managed venv for manul-engine (user-level)
      path.join(os.homedir(), ".local", "pipx", "venvs", "manul-engine", "bin", "manul"),
      // 5. macOS Homebrew — Apple Silicon default prefix
      "/opt/homebrew/bin/manul",
      // 6. system-wide installs
      "/usr/local/bin/manul",
      "/usr/bin/manul",
    ] : [
      // Windows: pip --user installs scripts under %APPDATA%\Python\<ver>\Scripts
      // and %LOCALAPPDATA%\Programs\Python\<ver>\Scripts. Scan both trees.
      ...(() => {
        const results: string[] = [];
        for (const base of [
          process.env.APPDATA ? path.join(process.env.APPDATA, "Python") : "",
          process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, "Programs", "Python") : "",
        ]) {
          if (!base || !fs.existsSync(base)) { continue; }
          try {
            for (const entry of fs.readdirSync(base)) {
              const candidate = path.join(base, entry, "Scripts", "manul.exe");
              if (fs.existsSync(candidate)) { results.push(candidate); }
            }
          } catch { /* ignore */ }
        }
        return results;
      })(),
    ]),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  // Return the cached promise if a lookup is already in-flight or completed for
  // this workspace — prevents concurrent calls from each spawning a shell.
  if (_shellCache.has(workspaceRoot)) {
    return _shellCache.get(workspaceRoot)!;
  }

  // Async login-shell lookup — sources the user's real shell init so that
  // conda/pyenv/asdf/direnv shims are visible. Uses execFile with an explicit
  // argv array so the shell path is never parsed by another shell (no injection
  // risk even if the path contains spaces). cwd is set to workspaceRoot so
  // directory-sensitive tools (direnv, asdf) resolve against the project.
  const promise = new Promise<string>((resolve) => {
    if (isWin) {
      // `where` is a built-in on Windows; no shell wrapping needed.
      execFile("where", ["manul"], { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        // `where` can return multiple matches; pick the first that actually exists.
        const found = stdout.split("\n").map(l => l.trim()).find(l => l && fs.existsSync(l));
        resolve(!err && found ? found : "manul");
      });
    } else {
      // Prefer vscode.env.shell (the terminal shell the user configured in VS Code),
      // then fall back to $SHELL. If neither is set, skip the lookup entirely.
      const shell = vscode.env.shell || process.env.SHELL;
      if (!shell) {
        resolve("manul");
        return;
      }
      // Normalise shell name: lowercase and strip .exe suffix so comparisons
      // work on Windows paths (e.g. "fish.exe") and mixed-case entries.
      const shellName = path.basename(shell).toLowerCase().replace(/\.exe$/, "");
      let shellArgs: string[];
      if (shellName === "fish") {
        // fish supports -l (login) and -c but not -i; pass as separate args.
        shellArgs = ["-l", "-c", "command -v manul"];
      } else if (shellName === "sh" || shellName === "dash" || shellName === "ash") {
        shellArgs = ["-c", "command -v manul"];
      } else {
        // bash, zsh, ksh, and most other POSIX-compatible shells.
        shellArgs = ["-l", "-i", "-c", "command -v manul"];
      }
      // argv array avoids shell re-parsing of the shell path (no injection risk).
      execFile(shell, shellArgs, { cwd: workspaceRoot, timeout: 3000 }, (err, stdout) => {
        // Login/interactive shells can emit banners or warnings before the path.
        // Scan all lines and pick the first one that resolves to an existing file.
        const found = stdout.split("\n").map(l => l.trim()).find(l => l && fs.existsSync(l));
        resolve(!err && found ? found : "manul");
      });
    }
  });

  // Store the promise immediately so any concurrent callers await the same lookup.
  // If the lookup fell back to the plain "manul" string (shell init failed or timed
  // out), evict the cache so the next call retries rather than permanently locking
  // in the failure for the rest of the extension-host session.
  const cached = promise.then((result) => {
    if (result === "manul") {
      _shellCache.delete(workspaceRoot);
    }
    return result;
  });
  _shellCache.set(workspaceRoot, cached);
  return cached;
}

/** Spawn manul <huntFile> and stream output. Resolves with exit code. */
export function runHunt(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void,
  token?: vscode.CancellationToken,
  breakLines?: number[]
): Promise<number> {
  return new Promise((resolve, reject) => {
    // Prefer the workspace folder root as cwd so ManulEngine picks up
    // manul_engine_configuration.json and cache paths from the project root.
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(
      vscode.Uri.file(huntFile)
    );
    const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(huntFile);

    let proc: ChildProcess;
    try {
      // --workers 1 forces sequential mode so each Test Explorer invocation
      // runs directly in-process (no subprocess spawning overhead / recursion).
      const browserFlags = getBrowserFlags();
      const spawnArgs = [...browserFlags.args, "--workers", "1"];
      if (breakLines && breakLines.length > 0) {
        spawnArgs.push("--break-lines", breakLines.join(","));
      }

      // ── Reporting & retry flags from VS Code settings ──────────────────────
      const _cfg = vscode.workspace.getConfiguration("manulEngine");
      const _retries = _cfg.get<number>("retries", 0);
      if (_retries > 0) { spawnArgs.push("--retries", String(_retries)); }
      const _screenshot = _cfg.get<string>("screenshotMode", "on-fail");
      if (_screenshot && _screenshot !== "on-fail") { spawnArgs.push("--screenshot", _screenshot); }
      if (_cfg.get<boolean>("htmlReport", false)) { spawnArgs.push("--html-report"); }

      spawnArgs.push(huntFile);
      // Only inject MANUL_AUTO_ANNOTATE when it is explicitly ON in VS Code settings.
      // When the setting is false/unset, do NOT inject the env var — this lets the
      // project's manul_engine_configuration.json auto_annotate value take effect.
      const _autoAnnotate = _cfg.get<boolean>("autoAnnotate", false);
      proc = spawn(manulExe, spawnArgs, {
        cwd,
        env: {
          ...process.env,
          // Force Python to flush stdout immediately — without this, output
          // is block-buffered when piped and steps appear only at the end.
          PYTHONUNBUFFERED: "1",
          ...browserFlags.env,
          ...(_autoAnnotate ? { MANUL_AUTO_ANNOTATE: "true" } : {}),
        },
      });
    } catch (err) {
      reject(err);
      return;
    }

    proc.stdout?.on("data", (d: Buffer) => onData(d.toString()));
    proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
    proc.on("close", (code) => resolve(code ?? 1));
    proc.on("error", reject);

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve(1);
    });
  });
}

/**
 * Run hunt file in the output-panel (piped) using the ManulEngine
 * pause-protocol over stdout/stdin (without passing the CLI --debug flag).
 *
 * When Python writes  \x00MANUL_DEBUG_PAUSE\x00{"step":"…","idx":N}\n
 * `onPause(step, idx)` is called (the VS Code Webview panel or any custom UI).
 * Its return value ("next" | "continue") is written to the process stdin.
 *
 * Gutter breakpoints also emit the marker (no Playwright Inspector).
 * Regular output lines are forwarded to onData as usual.
 * The function has the same extended signature as runHunt + onPause, and is
 * wrapped as HuntRunFn in huntTestController.ts.
 */
export function runHuntFileDebugPanel(
  manulExe: string,
  huntFile: string,
  onData: (chunk: string) => void,
  token?: vscode.CancellationToken,
  breakLines?: number[],
  onPause?: (step: string, idx: number) => Promise<"next" | "continue" | "highlight" | "explain" | "debug-stop" | "stop-test">
): Promise<number> {
  return new Promise((resolve, reject) => {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(huntFile));
    const cwd = workspaceFolder?.uri.fsPath ?? path.dirname(huntFile);

    // No --debug flag here: we only want to pause at explicit breakpoints
    // (--break-lines).  Adding --debug would pause before every step.
    // Always inject --explain so heuristic scoring data is available for
    // the HoverProvider (tooltip on hover over step lines).
    const browserFlagsPanel = getBrowserFlags();
    const spawnArgs = [...browserFlagsPanel.args, "--explain", "--workers", "1"];
    if (breakLines && breakLines.length > 0) {
      spawnArgs.push("--break-lines", breakLines.join(","));
    }

    // ── Reporting & retry flags from VS Code settings ──────────────────────
    const _cfgPanel = vscode.workspace.getConfiguration("manulEngine");
    const _retriesPanel = _cfgPanel.get<number>("retries", 0);
    if (_retriesPanel > 0) { spawnArgs.push("--retries", String(_retriesPanel)); }
    const _screenshotPanel = _cfgPanel.get<string>("screenshotMode", "on-fail");
    if (_screenshotPanel && _screenshotPanel !== "on-fail") { spawnArgs.push("--screenshot", _screenshotPanel); }
    if (_cfgPanel.get<boolean>("htmlReport", false)) { spawnArgs.push("--html-report"); }

    spawnArgs.push(huntFile);

    let proc: ChildProcess;
    try {
      const _autoAnnotatePanel = _cfgPanel.get<boolean>("autoAnnotate", false);
      proc = spawn(manulExe, spawnArgs, {
        cwd,
        stdio: ["pipe", "pipe", "pipe"],
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
          ...browserFlagsPanel.env,
          ...(_autoAnnotatePanel ? { MANUL_AUTO_ANNOTATE: "true" } : {}),
        },
      });
    } catch (err) {
      reject(err);
      return;
    }

    // Line-buffer stdout so we can detect pause markers reliably even if data
    // arrives in chunks smaller than a full line.
    let stdoutBuf = "";
    proc.stdout?.on("data", (d: Buffer) => {
      stdoutBuf += d.toString();
      const lines = stdoutBuf.split("\n");
      stdoutBuf = lines.pop() ?? "";
      for (const line of lines) {
        const markerIdx = line.indexOf(PAUSE_MARKER);
        if (markerIdx !== -1) {
          // Parse the JSON payload that follows the pause marker.
          const jsonPart = line.substring(markerIdx + PAUSE_MARKER.length);
          let step = "";
          let idx = 0;
          try {
            const parsed = JSON.parse(jsonPart) as { step?: string; idx?: number };
            step = parsed.step ?? "";
            idx = parsed.idx ?? 0;
          } catch { /* ignore malformed JSON — still respond so Python doesn't hang */ }

          // Show the Webview panel (if onPause provided) or fall back to
          // a notification.  Either way write the response to stdin so the
          // blocked Python readline() unblocks.
          const pausePromise: Thenable<"next" | "continue" | "highlight" | "explain" | "debug-stop" | "stop-test"> = onPause
            ? onPause(step, idx)
            : (() => {
                const shortStep = step.length > 100 ? step.substring(0, 100) + "…" : step;
                return vscode.window
                  .showInformationMessage(
                    `🐛 Debug — step ${idx}: ${shortStep}`,
                    { modal: false },
                    "⏭ Next Step",
                    "▶ Continue All"
                  )
                  .then((choice) =>
                    choice === "▶ Continue All" ? "continue" : "next"
                  );
              })();
          pausePromise.then(
            (choice: "next" | "continue" | "highlight" | "explain" | "debug-stop" | "stop-test") => {
              // Guard against writing to stdin after the process has already
              // exited or the stream has been closed/destroyed (e.g. user
              // pressed Stop while the QuickPick was open).
              if (choice === "stop-test") {
                // Send abort token so Python can clean up, then kill the process.
                if (proc.exitCode === null && proc.stdin && !proc.stdin.destroyed) {
                  proc.stdin.write("abort\n");
                }
                setTimeout(() => { if (proc.exitCode === null) { proc.kill(); } }, 500);
              } else {
                // For debug-stop, send the payload to Python so it clears all breakpoints.
                const stdinPayload = choice === "debug-stop" ? "debug-stop" : choice;
                if (proc.exitCode === null && proc.stdin && !proc.stdin.destroyed) {
                  proc.stdin.write(stdinPayload + "\n");
                }
              }
            },
            () => { /* swallow QuickPick errors to avoid unhandled rejections */ }
          );
        } else {
          onData(line + "\n");
        }
      }
    });

    // Prevent "write after end" / EPIPE crashes from propagating to the
    // extension host when stdin closes while a response is in flight.
    proc.stdin?.on("error", () => { /* ignore stdin errors */ });

    proc.stderr?.on("data", (d: Buffer) => onData(d.toString()));
    proc.on("close", (code) => resolve(code ?? 1));
    proc.on("error", reject);

    token?.onCancellationRequested(() => {
      proc.kill();
      resolve(1);
    });
  });
}

/**
 * Run hunt file in interactive terminal with --debug flag.
 * The user can press ENTER to advance each step, or type 'pause' to open
 * the Playwright Inspector. Gutter breakpoints are also honoured via --break-lines.
 */
export async function runHuntFileDebugInTerminal(
  uri: vscode.Uri,
  workspaceRoot: string,
  manulExe: string
): Promise<void> {
  const shellBase = path.basename((vscode.env.shell || "").toLowerCase());
  const isPowerShell = shellBase === "powershell.exe" || shellBase === "pwsh" || shellBase === "pwsh.exe";
  const breakLines = getHuntBreakpointLines(uri.fsPath);
  const breakFlag = breakLines.length > 0 ? ` --break-lines ${breakLines.join(",")}` : "";
  const termBrowserFlags = getBrowserFlags();
  const browserFlag = termBrowserFlags.args.length > 0 ? ` ${termBrowserFlags.args.join(" ")}` : "";
  const command = isPowerShell
    ? `& "${manulExe}"${browserFlag} --debug${breakFlag} "${uri.fsPath}"`
    : `"${manulExe}"${browserFlag} --debug${breakFlag} "${uri.fsPath}"`;
  const terminal = vscode.window.createTerminal({
    name: DEBUG_TERMINAL_NAME,
    cwd: workspaceRoot,
    env: { PYTHONUNBUFFERED: "1", ...termBrowserFlags.env },
  });
  terminal.show();
  terminal.sendText(command);
}

/**
 * Return 1-based file line numbers of all enabled VS Code breakpoints set
 * inside a given hunt file.  These are passed to the manul CLI as
 * `--break-lines 3,7` so the engine pauses (page.pause()) before each
 * matching step.  Breakpoints show as unverified (grey) in the gutter because
 * ManulEngine does not ship a DAP debug adapter — they still stop execution.
 */
export function getHuntBreakpointLines(huntFilePath: string): number[] {
  const fileFsPath = vscode.Uri.file(huntFilePath).fsPath;
  return vscode.debug.breakpoints
    .filter((bp): bp is vscode.SourceBreakpoint => bp instanceof vscode.SourceBreakpoint)
    .filter((bp) => bp.enabled && bp.location.uri.fsPath === fileFsPath)
    .map((bp) => bp.location.range.start.line + 1); // VS Code lines are 0-based
}
