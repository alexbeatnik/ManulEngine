import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { findManulExecutable, runHunt } from "./huntRunner";

// ── Concurrency helpers ────────────────────────────────────────────────────

/**
 * Read the `workers` value for the given workspace root.
 * Prefers the VS Code setting `manulEngine.workers`, then falls back to
 * the `workers` field in manul_engine_configuration.json (or the file
 * specified by `manulEngine.configFile`), and finally to 4.
 */
function readWorkers(workspaceRoot: string): number {
  const cfg = vscode.workspace
    .getConfiguration("manulEngine")
    .get<number>("workers");
  if (cfg !== undefined && cfg !== null && cfg > 0) {
    return cfg;
  }
  try {
    const configFile = vscode.workspace
      .getConfiguration("manulEngine")
      .get<string>("configFile") ?? "manul_engine_configuration.json";
    const raw = fs.readFileSync(path.join(workspaceRoot, configFile), "utf-8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const w = parsed["workers"];
    if (typeof w === "number" && w > 0) {
      return w;
    }
  } catch {
    // config not found or invalid — use default
  }
  return 4;
}

/**
 * Run `tasks` with at most `concurrency` tasks executing at the same time.
 */
async function runWithConcurrency<T>(
  tasks: (() => Promise<T>)[],
  concurrency: number
): Promise<T[]> {
  const results: T[] = [];
  let index = 0;
  async function worker(): Promise<void> {
    while (index < tasks.length) {
      const i = index++;
      results[i] = await tasks[i]();
    }
  }
  const workers = Array.from({ length: Math.min(concurrency, tasks.length) }, () => worker());
  await Promise.all(workers);
  return results;
}

// ── Hunt file step parsing ─────────────────────────────────────────────────

interface HuntStep {
  num: number;
  label: string;
}

function parseHuntSteps(filePath: string): HuntStep[] {
  let content: string;
  try {
    content = fs.readFileSync(filePath, "utf-8");
  } catch {
    return [];
  }
  const steps: HuntStep[] = [];
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("@")) {
      continue;
    }
    const m = trimmed.match(/^(\d+)\.\s+(.+)/);
    if (m) {
      steps.push({ num: parseInt(m[1], 10), label: m[2].trim() });
    }
  }
  return steps;
}

// ── Module-level run counter and helpers (shared by Test Explorer + play button)
let _runCounter = 0;

function _refreshStepChildren(
  ctrl: vscode.TestController,
  item: vscode.TestItem,
  uri: vscode.Uri,
  runId?: number
): void {
  item.children.replace([]);
  const steps = parseHuntSteps(uri.fsPath);
  const suffix = runId !== undefined ? `@${runId}` : "";
  for (const step of steps) {
    const stepId = `${uri.toString()}#${step.num}${suffix}`;
    const stepItem = ctrl.createTestItem(stepId, `${step.num}. ${step.label}`, uri);
    stepItem.canResolveChildren = false;
    item.children.add(stepItem);
  }
}

/**
 * Core per-item run logic shared by Test Explorer and the editor play-button.
 * Handles step discovery, real-time pass/fail reporting, and output streaming.
 */
async function _runItem(
  ctrl: vscode.TestController,
  run: vscode.TestRun,
  item: vscode.TestItem,
  token?: vscode.CancellationToken
): Promise<void> {
  const itemWorkspaceRoot =
    (item.uri ? vscode.workspace.getWorkspaceFolder(item.uri)?.uri.fsPath : undefined)
    ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
    ?? process.cwd();
  const manulExe = await findManulExecutable(itemWorkspaceRoot);

  if (item.uri) {
    _refreshStepChildren(ctrl, item, item.uri, ++_runCounter);
  }

  const stepItems = new Map<number, vscode.TestItem>();
  item.children.forEach((child) => {
    const m = child.id.match(/#(\d+)(?:@\d+)?$/);
    if (m) { stepItems.set(parseInt(m[1], 10), child); }
  });

  run.started(item);
  stepItems.forEach((s) => run.started(s));

  const output: string[] = [];
  let currentStepNum = 0;
  let currentStepOutput: string[] = [];
  let currentStepDone = false;
  const stepStartRe = /\[\u{1F43E} STEP (\d+) @/u;
  const stepPassRe = /\u2705 PASSED/u;
  const stepFailRe = /\u274C.*FAILED|\u{1F4A5} CRASH/u;

  function finaliseStep(stepNum: number, failed: boolean): void {
    const stepItem = stepItems.get(stepNum);
    if (!stepItem) { return; }
    const msg = currentStepOutput.join("");
    if (failed) {
      run.failed(stepItem, new vscode.TestMessage(msg));
    } else {
      run.passed(stepItem);
    }
  }

  try {
    const exitCode = await runHunt(
      manulExe,
      item.uri!.fsPath,
      (chunk) => {
        output.push(chunk);
        run.appendOutput(chunk.replace(/\r?\n/g, "\r\n"), undefined, item);
        const lines = chunk.split("\n");
        for (const line of lines) {
          const stepMatch = line.match(stepStartRe);
          if (stepMatch) {
            if (currentStepNum > 0 && !currentStepDone) {
              finaliseStep(currentStepNum, false);
            }
            currentStepNum = parseInt(stepMatch[1], 10);
            currentStepOutput = [line + "\n"];
            currentStepDone = false;
          } else {
            currentStepOutput.push(line + "\n");
            if (!currentStepDone && currentStepNum > 0) {
              if (stepPassRe.test(line)) {
                finaliseStep(currentStepNum, false);
                currentStepDone = true;
              } else if (stepFailRe.test(line)) {
                finaliseStep(currentStepNum, true);
                currentStepDone = true;
              }
            }
          }
        }
      },
      token
    );

    if (currentStepNum > 0 && !currentStepDone) {
      finaliseStep(currentStepNum, exitCode !== 0);
    }
    stepItems.forEach((s, num) => {
      if (num > currentStepNum) { run.skipped(s); }
    });

    if (exitCode === 0) {
      run.passed(item);
    } else {
      run.failed(item, new vscode.TestMessage(`Exit code: ${exitCode}\n${output.join("")}`));
    }
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    run.errored(item, new vscode.TestMessage(errMsg));
    if (currentStepNum > 0 && !currentStepDone) {
      const si = stepItems.get(currentStepNum);
      if (si) { run.errored(si, new vscode.TestMessage(errMsg)); }
    }
  }
}

export function createHuntTestController(
  context: vscode.ExtensionContext
): vscode.TestController {
  const ctrl = vscode.tests.createTestController(
    "manulHuntTests",
    "ManulEngine Hunt Tests"
  );
  context.subscriptions.push(ctrl);

  // ── Discovery ──────────────────────────────────────────────────────────────

  async function discoverHuntFiles(): Promise<void> {
    const files = await vscode.workspace.findFiles("**/*.hunt", "**/{node_modules,.venv,dist}/**");
    for (const uri of files) {
      getOrCreateTestItem(uri);
    }
  }

  function getOrCreateTestItem(uri: vscode.Uri): vscode.TestItem {
    const existing = ctrl.items.get(uri.toString());
    if (existing) {
      return existing;
    }
    const label = path.basename(uri.fsPath, ".hunt");
    const item = ctrl.createTestItem(uri.toString(), label, uri);
    // Steps are added only during a run (for step-level reporting), not at
    // discovery time — otherwise VS Code counts each step as a separate test
    // and the total shown in the explorer is wrong.
    item.canResolveChildren = false;

    ctrl.items.add(item);
    return item;
  }

  // ── File watcher ───────────────────────────────────────────────────────────

  const watcher = vscode.workspace.createFileSystemWatcher("**/*.hunt");
  context.subscriptions.push(watcher);

  watcher.onDidCreate((uri) => getOrCreateTestItem(uri));
  watcher.onDidChange((uri) => {
    const existing = ctrl.items.get(uri.toString());
    if (existing) {
      // Clear any leftover step children from a previous run so the count
      // stays at file-level until the next run.
      existing.children.replace([]);
    } else {
      getOrCreateTestItem(uri);
    }
  });
  watcher.onDidDelete((uri) => ctrl.items.delete(uri.toString()));

  discoverHuntFiles();

  // ── Run profile ────────────────────────────────────────────────────────────

  ctrl.createRunProfile(
    "Run Hunt",
    vscode.TestRunProfileKind.Run,
    async (request, token) => {
      const run = ctrl.createTestRun(request);

      // Collect top-level hunt-file items to run (deduplicated)
      const toRun = new Set<vscode.TestItem>();
      function collect(item: vscode.TestItem): void {
        // If it's a child step item, run its parent file instead
        const parentId = item.id.includes("#") ? item.id.split("#")[0] : null;
        if (parentId) {
          const parent = ctrl.items.get(parentId);
          if (parent) {
            toRun.add(parent);
            return;
          }
        }
        toRun.add(item);
      }

      if (request.include) {
        for (const item of request.include) {
          collect(item);
        }
      } else {
        ctrl.items.forEach((item) => toRun.add(item));
      }

      // Focus the Test Results panel so the user sees output immediately.
      await vscode.commands.executeCommand("workbench.panel.testResults.view.focus");

      // Determine concurrency limit from config (workers setting).
      // Use the workspace folder of the first queued item so multi-root
      // workspaces pick up the correct manul_engine_configuration.json.
      const firstItem = [...toRun][0];
      const workspaceRoot =
        (firstItem?.uri
          ? vscode.workspace.getWorkspaceFolder(firstItem.uri)?.uri.fsPath
          : undefined) ??
        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ??
        process.cwd();
      const workers = readWorkers(workspaceRoot);

      // Run hunt files with bounded concurrency — respects the `workers` setting.
      const tasks = [...toRun].map((item) => async () => {
        if (token.isCancellationRequested) {
          run.skipped(item);
          return;
        }
        await _runItem(ctrl, run, item, token);
      });
      await runWithConcurrency(tasks, workers);

      run.end();

      // Remove step children so the explorer reverts to file-level items
      // (correct test count) until the next run.
      toRun.forEach((item) => item.children.replace([]));
    },
    true
  );

  return ctrl;
}

/**
 * Run a single hunt file via the Test Controller — shows step-level results
 * in Test Explorer exactly like running from the explorer itself.
 */
export async function runHuntFileViaController(
  ctrl: vscode.TestController,
  uri: vscode.Uri
): Promise<void> {
  // Find or create the TestItem for this file
  let item = ctrl.items.get(uri.toString());
  if (!item) {
    const label = path.basename(uri.fsPath, ".hunt");
    item = ctrl.createTestItem(uri.toString(), label, uri);
    item.canResolveChildren = false;
    ctrl.items.add(item);
  }
  const request = new vscode.TestRunRequest([item]);
  const run = ctrl.createTestRun(request);
  await vscode.commands.executeCommand("workbench.panel.testResults.view.focus");
  try {
    await _runItem(ctrl, run, item);
  } finally {
    run.end();
    item.children.replace([]);
  }
}

/** Run hunt file in integrated terminal (raw, like the CLI). */
export async function runHuntFileInTerminalCommand(uri?: vscode.Uri): Promise<void> {
  const target =
    uri ?? vscode.window.activeTextEditor?.document.uri;
  if (!target || !target.fsPath.endsWith(".hunt")) {
    vscode.window.showWarningMessage("Please open or select a .hunt file.");
    return;
  }

  const roots = vscode.workspace.workspaceFolders ?? [];
  const workspaceRoot =
    vscode.workspace.getWorkspaceFolder(target)?.uri.fsPath
    ?? roots[0]?.uri.fsPath
    ?? path.dirname(target.fsPath);
  const manulExe = await findManulExecutable(workspaceRoot);
  const terminal = vscode.window.createTerminal("ManulEngine");
  terminal.show();
  // PowerShell requires `&` to invoke a path-quoted executable; other shells
  // (bash, zsh, fish, cmd) use plain quoting.
  const shellBase = path.basename((vscode.env.shell || "").toLowerCase());
  const isPowerShell = shellBase === "powershell.exe" || shellBase === "pwsh" || shellBase === "pwsh.exe";
  const command = isPowerShell
    ? `& "${manulExe}" "${target.fsPath}"`
    : `"${manulExe}" "${target.fsPath}"`;
  terminal.sendText(command);
}
