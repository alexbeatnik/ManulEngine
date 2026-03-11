/**
 * stepBuilderPanel.ts
 *
 * Sidebar webview that provides:
 *  - "New Hunt File" button — prompts for a name, creates a .hunt file in the
 *    configured `tests_home` directory, and opens it.
 *  - Step-insertion buttons — append the next numbered step to the active .hunt
 *    file with a single click.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { spawn } from "child_process";
import { findManulExecutable } from "./huntRunner";
import { getConfigFileName } from "./constants";

// ── Hook scaffold constants ──────────────────────────────────────────────────

const SETUP_SCAFFOLD = `[SETUP]
CALL PYTHON module_name.function_name
[END SETUP]`;

const TEARDOWN_SCAFFOLD = `[TEARDOWN]
CALL PYTHON module_name.function_name
[END TEARDOWN]`;

const DEMO_TEST_SCAFFOLD = `@context: E2E Login Flow with Hooks

# To enable hooks: create demo_helpers.py next to this file with
# inject_test_session() and clean_database() functions, then uncomment below.
# [SETUP]
# CALL PYTHON demo_helpers.inject_test_session
# [END SETUP]

1. NAVIGATE to "https://example.com"
2. Click "More information..." link
3. VERIFY that "IANA" is present

# [TEARDOWN]
# CALL PYTHON demo_helpers.clean_database
# [END TEARDOWN]`;

// ── Step templates ────────────────────────────────────────────────────────────

interface StepTemplate {
  label: string;
  icon: string;
  template: string;
}

const STEP_TEMPLATES: StepTemplate[] = [
  { label: "Navigate",      icon: "🌐", template: "NAVIGATE to " },
  { label: "Fill field",    icon: "⌨️",  template: "Fill '' field with ''" },
  { label: "Click",         icon: "🖱️",  template: "Click the '' button" },
  { label: "Double Click",  icon: "🖱️🖱️", template: "DOUBLE CLICK the '' button" },
  { label: "Select",        icon: "📋", template: "Select '' from the '' dropdown" },
  { label: "Check",         icon: "☑️",  template: "Check the checkbox for ''" },
  { label: "Radio",         icon: "🔘", template: "Click the radio button for ''" },
  { label: "Hover",         icon: "🔍", template: "HOVER over ''" },
  { label: "Drag & Drop",   icon: "↕️",  template: "Drag '' and drop it into ''" },
  { label: "Extract",       icon: "📤", template: "EXTRACT the '' into {}" },
  { label: "Verify present",icon: "✅", template: "VERIFY that '' is present" },
  { label: "Verify absent", icon: "🚫", template: "VERIFY that '' is NOT present" },
  { label: "Verify state",  icon: "🔒", template: "VERIFY that '' is DISABLED" },
  { label: "Press Enter",   icon: "↩️",  template: "PRESS ENTER" },
  { label: "Press Key",     icon: "⌨️",  template: "PRESS <KEY>" },
  { label: "Right Click",   icon: "🖱️",  template: "RIGHT CLICK ''" },
  { label: "Upload File",   icon: "📎", template: "UPLOAD '' to ''" },
  { label: "Wait",          icon: "⏸️",  template: "WAIT 2" },
  { label: "Scroll Down",   icon: "⬇️",  template: "SCROLL DOWN" },
  { label: "Scan Page",     icon: "🔍", template: "SCAN PAGE into draft.hunt" },
  { label: "Call Python",   icon: "🐍", template: "CALL PYTHON module_name.function_name" },
  { label: "Call Python → Var", icon: "🐍", template: "CALL PYTHON module_name.function_name into {variable_name}" },
  { label: "Debug / Pause", icon: "🐛", template: "DEBUG" },
  { label: "Done",          icon: "🏁", template: "DONE." },
];

// ── Provider ──────────────────────────────────────────────────────────────────

export class StepBuilderProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "manul.stepBuilder";

  private _view?: vscode.WebviewView;
  /**
   * URI of the last .hunt document that was active.
   * We store the URI (not the TextEditor object) because editor references
   * become stale as soon as the webview steals focus — stale editors silently
   * reject edit() calls.
   */
  private _lastHuntUri?: vscode.Uri;

  constructor(private readonly _context: vscode.ExtensionContext) {
    // Track the URI whenever the active editor changes to a .hunt file.
    _context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor && editor.document.fileName.endsWith(".hunt")) {
          this._lastHuntUri = editor.document.uri;
        }
      })
    );
    // Capture whatever is already open when the extension loads.
    const active = vscode.window.activeTextEditor;
    if (active && active.document.fileName.endsWith(".hunt")) {
      this._lastHuntUri = active.document.uri;
    }
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._getHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (msg: { command: string; template?: string; url?: string }) => {
      if (msg.command === "insertStep" && msg.template !== undefined) {
        await insertStep(msg.template, this._lastHuntUri);
      } else if (msg.command === "newHuntFile") {
        await newHuntFileCommand(this._context);
      } else if (msg.command === "insertSetup") {
        await vscode.commands.executeCommand("manul.insertSetup");
      } else if (msg.command === "insertTeardown") {
        await vscode.commands.executeCommand("manul.insertTeardown");
      } else if (msg.command === "generateDemoTest") {
        await vscode.commands.executeCommand("manul.generateDemoTest");
      } else if (msg.command === "runLiveScan") {
        await runLiveScanCommand(msg.url ?? "");
      }
    });
  }

  private _getHtml(webview: vscode.Webview): string {
    // Generate a nonce for the CSP — required for inline scripts in VS Code webviews.
    const nonce = getNonce();
    const csp = `default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;

    // Use data attributes instead of inline onclick — avoids CSP inline-handler block.
    const buttons = STEP_TEMPLATES.map(
      (s) =>
        `<button class="step-btn" data-template=${JSON.stringify(s.template)}>${s.icon} ${s.label}</button>`
    ).join("\n");

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>
  * { box-sizing: border-box; }
  body {
    padding: 8px;
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
  }
  .new-btn {
    display: block; width: 100%; padding: 7px 10px; margin-bottom: 12px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none; cursor: pointer; border-radius: 3px; font-size: 13px;
    font-weight: 600;
  }
  .new-btn:hover { background: var(--vscode-button-hoverBackground); }
  h3 {
    margin: 0 0 6px 0; font-size: 10px; text-transform: uppercase;
    letter-spacing: 0.08em; opacity: 0.6;
  }
  .step-btn {
    display: block; width: 100%; padding: 5px 8px; margin-bottom: 4px;
    background: var(--vscode-button-secondaryBackground);
    color: var(--vscode-button-secondaryForeground);
    border: none; cursor: pointer; text-align: left; border-radius: 3px;
    font-size: 12px;
  }
  .step-btn:hover { background: var(--vscode-button-secondaryHoverBackground); }
  .scanner-row { display: flex; gap: 6px; margin-bottom: 0; }
  .scanner-row input {
    flex: 1; padding: 5px 8px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border, transparent);
    border-radius: 3px; font-size: 12px;
  }
  .scan-btn {
    padding: 5px 10px; white-space: nowrap;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none; cursor: pointer; border-radius: 3px; font-size: 12px;
  }
  .scan-btn:hover { background: var(--vscode-button-hoverBackground); }
</style>
</head>
<body>
  <button class="new-btn" id="btn-new-file">＋ New Hunt File</button>
  <h3>Hooks</h3>
  <button class="step-btn" id="btn-insert-setup">🔧 Insert [SETUP] block</button>
  <button class="step-btn" id="btn-insert-teardown">🧹 Insert [TEARDOWN] block</button>
  <button class="step-btn" id="btn-generate-demo">🎯 Generate Demo Test</button>
  <h3>Live Page Scanner</h3>
  <div class="scanner-row">
    <input type="text" id="scanner-url-input" placeholder="https://example.com" />
    <button class="scan-btn" id="run-live-scan-btn">🔍 Run Scan</button>
  </div>
  <h3>Insert Step</h3>
  ${buttons}
  <script nonce="${nonce}">
    const vsc = acquireVsCodeApi();
    document.getElementById('btn-new-file').addEventListener('click', function() {
      vsc.postMessage({ command: 'newHuntFile' });
    });
    document.getElementById('btn-insert-setup').addEventListener('click', function() {
      vsc.postMessage({ command: 'insertSetup' });
    });
    document.getElementById('btn-insert-teardown').addEventListener('click', function() {
      vsc.postMessage({ command: 'insertTeardown' });
    });
    document.getElementById('btn-generate-demo').addEventListener('click', function() {
      vsc.postMessage({ command: 'generateDemoTest' });
    });
    document.querySelectorAll('.step-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        if (btn.dataset.template !== undefined) {
          vsc.postMessage({ command: 'insertStep', template: btn.dataset.template });
        }
      });
    });
    document.getElementById('run-live-scan-btn').addEventListener('click', function() {
      var urlVal = document.getElementById('scanner-url-input').value.trim();
      if (!urlVal) {
        document.getElementById('scanner-url-input').focus();
        return;
      }
      vsc.postMessage({ command: 'runLiveScan', url: urlVal });
    });
  </script>
</body></html>`;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Generate a random nonce string for the webview Content-Security-Policy. */
function getNonce(): string {
  let text = "";
  const possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}

/**
 * Determine the next step number from the active .hunt document text.
 * Scans for lines matching `\d+.` and returns max + 1 (or 1 if none found).
 */
function nextStepNumber(text: string): number {
  const matches = [...text.matchAll(/^(\d+)\./gm)];
  if (matches.length === 0) { return 1; }
  return Math.max(...matches.map((m) => parseInt(m[1], 10))) + 1;
}

/**
 * Append a numbered step to the active .hunt file.
 * Positions the cursor inside the first pair of '' in the inserted line.
 *
 * Uses WorkspaceEdit (not editor.edit) so that the insert works even when
 * the sidebar webview holds focus and activeTextEditor is undefined / stale.
 *
 * @param lastHuntUri - URI of the last known .hunt document, kept by the
 *   provider across webview focus changes.
 */
async function insertStep(template: string, lastHuntUri?: vscode.Uri): Promise<void> {
  // 1. Active editor (if it's a .hunt file)
  const activeUri = vscode.window.activeTextEditor?.document.fileName.endsWith(".hunt")
    ? vscode.window.activeTextEditor.document.uri
    : undefined;

  // 2. Remembered URI from the last time user focused a .hunt file
  // 3. Any .hunt doc currently open in the workspace (last resort)
  const anyOpenHunt = vscode.workspace.textDocuments.find((d) =>
    d.fileName.endsWith(".hunt") && !d.isClosed
  )?.uri;

  const uri = activeUri ?? lastHuntUri ?? anyOpenHunt;

  if (!uri) {
    vscode.window.showWarningMessage("Open a .hunt file first.");
    return;
  }

  // Bring the document to the foreground FIRST so we get a live editor.
  const doc = await vscode.workspace.openTextDocument(uri);
  const editor = await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: false });

  const text = doc.getText();
  const num = nextStepNumber(text);
  const stepText = `${num}. ${template}`;

  // Determine insertion point: end of file, prefixed with newline if needed.
  const lastLine = doc.lineAt(doc.lineCount - 1);
  const endPos = lastLine.range.end;
  const prefix = lastLine.text.trim() === "" ? "" : "\n";

  // Use editor.edit() on the freshly-focused, live editor reference.
  const ok = await editor.edit((eb) => {
    eb.insert(endPos, `${prefix}${stepText}`);
  });

  if (!ok) {
    vscode.window.showWarningMessage("Could not insert step — document may be read-only.");
    return;
  }

  // Position cursor inside the first '' pair.
  const updatedText = doc.getText();
  const lines = updatedText.split("\n");
  const insertedLineIdx = lines.findIndex((l) => l.startsWith(`${num}. `));
  if (insertedLineIdx === -1) { return; }

  const lineText = lines[insertedLineIdx];
  const quoteIdx = lineText.indexOf("''");
  if (quoteIdx !== -1) {
    const pos = new vscode.Position(insertedLineIdx, quoteIdx + 1);
    editor.selection = new vscode.Selection(pos, pos);
    editor.revealRange(new vscode.Range(pos, pos));
  }
}

// ── Hook commands ────────────────────────────────────────────────────────────

/**
 * Shared helper for hook/demo commands: resolves the best available .hunt
 * document, brings it to the foreground via `openTextDocument` +
 * `showTextDocument` (same pattern as `insertStep`), then calls *action* with
 * a live, freshly-focused editor reference so that `editor.edit()` never
 * operates on a stale reference.
 *
 * URI resolution priority (mirrors `insertStep`):
 *   1. Active editor if it is a .hunt file
 *   2. Any open (non-closed) .hunt document in the workspace
 *
 * Returns `undefined` (with a warning) if no .hunt document is found.
 */
async function _withHuntEditor(
  action: (editor: vscode.TextEditor) => Promise<void>
): Promise<void> {
  const activeUri = vscode.window.activeTextEditor?.document.fileName.endsWith(".hunt")
    ? vscode.window.activeTextEditor.document.uri
    : undefined;
  const anyOpenHunt = vscode.workspace.textDocuments.find(
    (d) => d.fileName.endsWith(".hunt") && !d.isClosed
  )?.uri;
  const uri = activeUri ?? anyOpenHunt;
  if (!uri) {
    vscode.window.showWarningMessage("Please open a .hunt file first.");
    return;
  }
  const doc = await vscode.workspace.openTextDocument(uri);
  const editor = await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: false });
  await action(editor);
}

/**
 * Insert a `[SETUP]` scaffold at the start of the cursor's line.
 * If an uncommented `[SETUP]` block already exists, show a warning instead.
 * Commented-out scaffolds (lines starting with #) are intentionally ignored.
 */
export async function insertSetupCommand(): Promise<void> {
  await _withHuntEditor(async (editor) => {
    if (/^\s*\[SETUP\]\s*$/m.test(editor.document.getText())) {
      vscode.window.showWarningMessage("A [SETUP] block already exists in this file.");
      return;
    }
    const cursor = editor.selection.active;
    const lineStart = new vscode.Position(cursor.line, 0);
    const prefix = cursor.line > 0 ? "\n" : "";
    const ok = await editor.edit((eb) => {
      eb.insert(lineStart, `${prefix}${SETUP_SCAFFOLD}\n`);
    });
    if (!ok) {
      vscode.window.showWarningMessage("Could not insert [SETUP] block — document may be read-only.");
    }
  });
}

/**
 * Insert a `[TEARDOWN]` scaffold at the start of the cursor's line.
 * If an uncommented `[TEARDOWN]` block already exists, show a warning instead.
 * Commented-out scaffolds (lines starting with #) are intentionally ignored.
 */
export async function insertTeardownCommand(): Promise<void> {
  await _withHuntEditor(async (editor) => {
    if (/^\s*\[TEARDOWN\]\s*$/m.test(editor.document.getText())) {
      vscode.window.showWarningMessage("A [TEARDOWN] block already exists in this file.");
      return;
    }
    const cursor = editor.selection.active;
    const lineStart = new vscode.Position(cursor.line, 0);
    const prefix = cursor.line > 0 ? "\n" : "";
    const ok = await editor.edit((eb) => {
      eb.insert(lineStart, `${prefix}${TEARDOWN_SCAFFOLD}\n`);
    });
    if (!ok) {
      vscode.window.showWarningMessage("Could not insert [TEARDOWN] block — document may be read-only.");
    }
  });
}

/**
 * Insert a numbered `CALL PYTHON module_name.function_name` step at the end
 * of the active .hunt file (same behaviour as the Step Builder buttons).
 * Registered as `manul.insertInlinePythonCall`.
 */
export async function insertInlinePythonCallCommand(): Promise<void> {
  await insertStep("CALL PYTHON module_name.function_name", undefined);
}

/**
 * Insert a demo `.hunt` scaffold at the start of the cursor's line.
 * The [SETUP] and [TEARDOWN] blocks are commented out by default — create
 * `demo_helpers.py` next to the hunt file and uncomment to activate them.
 */
export async function generateDemoTestCommand(): Promise<void> {
  await _withHuntEditor(async (editor) => {
    const cursor = editor.selection.active;
    const lineStart = new vscode.Position(cursor.line, 0);
    const prefix = cursor.line > 0 ? "\n" : "";
    const ok = await editor.edit((eb) => {
      eb.insert(lineStart, `${prefix}${DEMO_TEST_SCAFFOLD}\n`);
    });
    if (!ok) {
      vscode.window.showWarningMessage("Could not insert demo test — document may be read-only.");
    }
  });
}

/**
 * "New Hunt File" command: reads `tests_home` from the workspace config,
 * prompts for a file name, creates the file with a starter template, and opens it.
 */
export async function newHuntFileCommand(
  _context: vscode.ExtensionContext
): Promise<void> {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showErrorMessage("No workspace folder open.");
    return;
  }
  const workspaceRoot = folders[0].uri.fsPath;

  // Read tests_home from manul_engine_configuration.json
  const cfgFile = path.join(workspaceRoot, getConfigFileName());
  let testsHome = "tests";
  try {
    const cfg = JSON.parse(fs.readFileSync(cfgFile, "utf8"));
    if (typeof cfg.tests_home === "string" && cfg.tests_home.trim()) {
      testsHome = cfg.tests_home.trim();
    }
  } catch { /* config missing or malformed — use default */ }

  const testsDir = path.isAbsolute(testsHome)
    ? testsHome
    : path.join(workspaceRoot, testsHome);

  const name = await vscode.window.showInputBox({
    prompt: "Hunt file name (without .hunt extension)",
    placeHolder: "my_test",
    validateInput: (v) =>
      /^[\w\-]+$/.test(v.trim()) ? null : "Use letters, digits, - or _ only",
  });
  if (!name) { return; }

  if (!fs.existsSync(testsDir)) {
    fs.mkdirSync(testsDir, { recursive: true });
  }

  const filePath = path.join(testsDir, `${name}.hunt`);
  if (fs.existsSync(filePath)) {
    vscode.window.showErrorMessage(`File already exists: ${filePath}`);
    return;
  }

  const starter = `@context: \n@blueprint: ${name}\n\n1. NAVIGATE to \n`;
  fs.writeFileSync(filePath, starter, "utf8");

  const doc = await vscode.workspace.openTextDocument(filePath);
  await vscode.window.showTextDocument(doc);

  // Position cursor at the end of the NAVIGATE line
  const editor = vscode.window.activeTextEditor;
  if (editor) {
    const line = doc.lineAt(3); // "1. NAVIGATE to "
    const end = line.range.end;
    editor.selection = new vscode.Selection(end, end);
    editor.revealRange(new vscode.Range(end, end));
  }
}

/**
 * Run `manul scan <url> <outputFile>` and open the generated draft hunt file.
 * Uses spawn (argv array) so the URL is never interpreted by a shell, and large
 * page output does not hit Node's execFile maxBuffer limit.
 */
async function runLiveScanCommand(rawUrl: string): Promise<void> {
  // Accept a full http(s) URL or a bare hostname/path (auto-prefix https://).
  let parsedUrl: URL;
  let scanUrl = rawUrl.trim();
  try {
    parsedUrl = new URL(scanUrl);
  } catch {
    // Retry with https:// if it looks like a bare hostname (no spaces, no scheme).
    if (!scanUrl.includes(" ")) {
      try {
        scanUrl = "https://" + scanUrl;
        parsedUrl = new URL(scanUrl);
      } catch {
        vscode.window.showErrorMessage(
          "ManulEngine: Invalid URL. Enter a full URL or a bare hostname like example.com."
        );
        return;
      }
    } else {
      vscode.window.showErrorMessage(
        "ManulEngine: Invalid URL. Enter a full URL or a bare hostname like example.com."
      );
      return;
    }
  }
  if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
    vscode.window.showErrorMessage(
      "ManulEngine: Only http:// and https:// URLs are supported."
    );
    return;
  }

  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showErrorMessage("ManulEngine: No workspace folder open.");
    return;
  }
  const workspaceRoot = folders[0].uri.fsPath;

  // Read tests_home from the configured config file (respects the manulEngine.configFile
  // setting, matching the behaviour of configPanel.ts and huntTestController.ts).
  let testsHome = "tests";
  try {
    const configFile = getConfigFileName();
    const cfgPath = path.join(workspaceRoot, configFile);
    const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
    if (typeof cfg.tests_home === "string" && cfg.tests_home.trim()) {
      testsHome = cfg.tests_home.trim();
    }
  } catch { /* config missing or malformed — use default */ }

  const outputDir = path.isAbsolute(testsHome)
    ? testsHome
    : path.join(workspaceRoot, testsHome);
  const outputFile = path.join(outputDir, "draft.hunt");

  let scanSucceeded = false;
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "ManulEngine: Scanning page...",
      cancellable: false,
    },
    async () => {
      const manulExe = await findManulExecutable(workspaceRoot);
      await new Promise<void>((resolve) => {
        // `manul scan` writes the hunt file to disk and may print a large page
        // snapshot to stdout.  Using spawn (instead of execFile) avoids the
        // 1 MB maxBuffer limit; we discard stdout since the result is on disk.
        const proc = spawn(manulExe, ["scan", scanUrl, outputFile], {
          cwd: workspaceRoot,
          stdio: ["ignore", "ignore", "pipe"],
        });
        let stderrBuf = "";
        let settled = false;
        proc.stderr.on("data", (chunk: Buffer) => { stderrBuf += chunk.toString(); });
        let timedOut = false;
        const killTimer = setTimeout(() => { timedOut = true; proc.kill(); }, 90_000);
        proc.on("error", (err) => {
          if (settled) { return; }
          settled = true;
          clearTimeout(killTimer);
          const detail = stderrBuf.trim() || err.message || String(err);
          vscode.window.showErrorMessage(`ManulEngine: Scan failed — unable to start manul: ${detail}`);
          resolve();
        });
        proc.on("close", (code) => {
          if (settled) { return; }
          settled = true;
          clearTimeout(killTimer);
          if (timedOut) {
            vscode.window.showErrorMessage("ManulEngine: Scan timed out after 90s.");
          } else if (code !== 0) {
            const detail = stderrBuf.trim() || `process exited with code ${code}`;
            vscode.window.showErrorMessage(`ManulEngine: Scan failed — ${detail}`);
          } else {
            scanSucceeded = true;
          }
          resolve();
        });
      });
    }
  );

  if (!scanSucceeded) { return; }

  if (fs.existsSync(outputFile)) {
    const openedDoc = await vscode.workspace.openTextDocument(outputFile);
    await vscode.window.showTextDocument(openedDoc);
  } else {
    vscode.window.showWarningMessage(
      `ManulEngine: Scan finished but ${outputFile} was not created.`
    );
  }
}
