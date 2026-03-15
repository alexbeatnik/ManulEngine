/**
 * schedulerPanel.ts
 *
 * Full-editor Webview Panel that displays a "Scheduler Dashboard":
 *  - Scans the workspace for .hunt files with `@schedule:` headers.
 *  - Shows them in a table (file name + schedule expression).
 *  - Provides Start / Stop buttons to control a `manul daemon` terminal.
 */

import * as vscode from "vscode";
import * as path from "path";
import { findManulExecutable } from "./huntRunner";
import { DAEMON_TERMINAL_NAME, getConfigFileName } from "./constants";

// ── Types ────────────────────────────────────────────────────────────────────

interface ScheduledFile {
  /** Workspace-relative path */
  relPath: string;
  /** Raw @schedule: expression */
  schedule: string;
}

// ── File scanner ─────────────────────────────────────────────────────────────

/**
 * Scan the workspace for `.hunt` files and extract `@schedule:` headers.
 * Reads only the first 20 lines of each file for speed.
 */
async function findScheduledHunts(): Promise<ScheduledFile[]> {
  const files = await vscode.workspace.findFiles("**/*.hunt", "**/node_modules/**");
  const results: ScheduledFile[] = [];

  for (const uri of files) {
    try {
      const doc = await vscode.workspace.openTextDocument(uri);
      const linesToCheck = Math.min(doc.lineCount, 20);
      for (let i = 0; i < linesToCheck; i++) {
        const text = doc.lineAt(i).text.trim();
        if (text.startsWith("@schedule:")) {
          const expr = text.substring("@schedule:".length).trim();
          if (expr) {
            const rel = vscode.workspace.asRelativePath(uri, false);
            results.push({ relPath: rel, schedule: expr });
          }
          break; // only one @schedule per file
        }
        // Stop early if we hit a step line (not a header anymore)
        if (/^(STEP\s|NAVIGATE\s|\d+\.)/i.test(text)) {
          break;
        }
      }
    } catch {
      // skip unreadable files
    }
  }

  results.sort((a, b) => a.relPath.localeCompare(b.relPath));
  return results;
}

// ── Read tests_home from config ──────────────────────────────────────────────

function readTestsHome(workspaceRoot: string): string {
  try {
    const cfgPath = path.join(workspaceRoot, getConfigFileName());
    const raw = require("fs").readFileSync(cfgPath, "utf8");
    const cfg = JSON.parse(raw);
    if (typeof cfg.tests_home === "string" && cfg.tests_home.trim()) {
      return cfg.tests_home.trim();
    }
  } catch { /* config missing or malformed */ }
  return "tests";
}

// ── Panel singleton ──────────────────────────────────────────────────────────

export class SchedulerPanel {
  public static readonly viewType = "manul.schedulerDashboard";

  private static _instance: SchedulerPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private _disposed = false;

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this._panel = panel;

    // Handle messages from the webview
    this._panel.webview.onDidReceiveMessage(
      async (msg: { command: string }) => {
        if (msg.command === "refresh") {
          await this._sendScheduledFiles();
        } else if (msg.command === "startDaemon") {
          await this._startDaemon();
        } else if (msg.command === "stopDaemon") {
          this._stopDaemon();
        }
      },
      undefined,
    );

    this._panel.onDidDispose(() => {
      this._disposed = true;
      SchedulerPanel._instance = undefined;
    });

    // Initial content
    this._panel.webview.html = this._getHtml(panel.webview);
  }

  /** Show or create the Scheduler Dashboard panel. */
  public static render(extensionUri: vscode.Uri): void {
    if (SchedulerPanel._instance) {
      SchedulerPanel._instance._panel.reveal(vscode.ViewColumn.One);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      SchedulerPanel.viewType,
      "ManulEngine Daemon",
      vscode.ViewColumn.One,
      { enableScripts: true, retainContextWhenHidden: true },
    );

    SchedulerPanel._instance = new SchedulerPanel(panel, extensionUri);
  }

  // ── Daemon terminal management ───────────────────────────────────────────

  private async _startDaemon(): Promise<void> {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      vscode.window.showErrorMessage("ManulEngine: No workspace folder open.");
      return;
    }
    const workspaceRoot = folders[0].uri.fsPath;

    let manulExe: string;
    try {
      manulExe = await findManulExecutable(workspaceRoot);
    } catch {
      vscode.window.showErrorMessage(
        "ManulEngine: Could not find the manul executable. Is ManulEngine installed?"
      );
      return;
    }

    const testsHome = readTestsHome(workspaceRoot);

    // Reuse existing daemon terminal or create a new one.
    const existing = vscode.window.terminals.find(
      (t) => t.name === DAEMON_TERMINAL_NAME
    );
    if (existing) {
      existing.show();
      vscode.window.showWarningMessage(
        "ManulEngine: Daemon terminal already running. Stop it first or use the existing terminal."
      );
      return;
    }

    const terminal = vscode.window.createTerminal({
      name: DAEMON_TERMINAL_NAME,
      cwd: workspaceRoot,
    });
    terminal.show();
    terminal.sendText(
      `${JSON.stringify(manulExe)} daemon ${JSON.stringify(testsHome)} --headless`
    );

    this._postStatus();
  }

  private _stopDaemon(): void {
    const terminal = vscode.window.terminals.find(
      (t) => t.name === DAEMON_TERMINAL_NAME
    );
    if (terminal) {
      terminal.dispose();
      vscode.window.showInformationMessage("ManulEngine: Daemon stopped.");
    } else {
      vscode.window.showWarningMessage("ManulEngine: No daemon terminal found.");
    }
    this._postStatus();
  }

  private _isDaemonRunning(): boolean {
    return vscode.window.terminals.some(
      (t) => t.name === DAEMON_TERMINAL_NAME
    );
  }

  // ── Send data to the webview ─────────────────────────────────────────────

  private async _sendScheduledFiles(): Promise<void> {
    if (this._disposed) { return; }
    const files = await findScheduledHunts();
    this._panel.webview.postMessage({ command: "setFiles", files });
    this._postStatus();
  }

  private _postStatus(): void {
    if (this._disposed) { return; }
    this._panel.webview.postMessage({
      command: "setStatus",
      running: this._isDaemonRunning(),
    });
  }

  // ── HTML template ────────────────────────────────────────────────────────

  private _getHtml(webview: vscode.Webview): string {
    const nonce = getNonce();
    const csp = `default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    padding: 20px;
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
  }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .subtitle { opacity: 0.6; font-size: 12px; margin-bottom: 16px; }
  .status-bar {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 16px; padding: 8px 12px;
    background: var(--vscode-editorWidget-background);
    border: 1px solid var(--vscode-editorWidget-border, transparent);
    border-radius: 4px;
  }
  .status-dot {
    width: 10px; height: 10px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
  }
  .status-dot.running { background: #a6e3a1; box-shadow: 0 0 6px #a6e3a1; }
  .status-dot.stopped { background: #585b70; }
  .status-label { font-size: 13px; font-weight: 600; }
  .controls {
    display: flex; gap: 8px; margin-bottom: 20px;
  }
  .ctrl-btn {
    padding: 7px 16px; border: none; cursor: pointer;
    border-radius: 4px; font-size: 13px; font-weight: 600;
  }
  .ctrl-btn.start {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
  }
  .ctrl-btn.start:hover { background: var(--vscode-button-hoverBackground); }
  .ctrl-btn.stop {
    background: var(--vscode-editorError-foreground, #f44747);
    color: #fff;
  }
  .ctrl-btn.stop:hover { opacity: 0.85; }
  .ctrl-btn.refresh {
    background: var(--vscode-button-secondaryBackground);
    color: var(--vscode-button-secondaryForeground);
  }
  .ctrl-btn.refresh:hover { background: var(--vscode-button-secondaryHoverBackground); }
  h2 { font-size: 14px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7; }
  table {
    width: 100%; border-collapse: collapse;
    font-size: 12px;
  }
  th {
    text-align: left; padding: 6px 10px;
    background: var(--vscode-editorWidget-background);
    border-bottom: 1px solid var(--vscode-editorWidget-border, #444);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    opacity: 0.7; font-size: 11px;
  }
  td {
    padding: 6px 10px;
    border-bottom: 1px solid var(--vscode-editorWidget-border, #333);
  }
  tr:hover td { background: var(--vscode-list-hoverBackground); }
  .empty-msg {
    padding: 20px; text-align: center; opacity: 0.5; font-style: italic;
  }
  .schedule-expr {
    font-family: var(--vscode-editor-font-family, monospace);
    color: var(--vscode-textLink-foreground);
  }
</style>
</head>
<body>
  <h1>😼 ManulEngine Daemon</h1>
  <div class="subtitle">Built-in scheduler for RPA workflows &amp; synthetic monitoring</div>

  <div class="status-bar">
    <span class="status-dot stopped" id="statusDot"></span>
    <span class="status-label" id="statusLabel">Stopped</span>
  </div>

  <div class="controls">
    <button class="ctrl-btn start" id="btnStart">▶ Start Daemon</button>
    <button class="ctrl-btn stop" id="btnStop">⏹ Stop Daemon</button>
    <button class="ctrl-btn refresh" id="btnRefresh">↻ Refresh</button>
  </div>

  <h2>Scheduled Hunt Files</h2>
  <div id="tableContainer">
    <div class="empty-msg">Scanning workspace…</div>
  </div>

  <script nonce="${nonce}">
    const vsc = acquireVsCodeApi();

    document.getElementById('btnStart').addEventListener('click', function() {
      vsc.postMessage({ command: 'startDaemon' });
    });
    document.getElementById('btnStop').addEventListener('click', function() {
      vsc.postMessage({ command: 'stopDaemon' });
    });
    document.getElementById('btnRefresh').addEventListener('click', function() {
      vsc.postMessage({ command: 'refresh' });
    });

    window.addEventListener('message', function(event) {
      var msg = event.data;
      if (msg.command === 'setFiles') {
        renderTable(msg.files);
      } else if (msg.command === 'setStatus') {
        var dot = document.getElementById('statusDot');
        var label = document.getElementById('statusLabel');
        if (msg.running) {
          dot.className = 'status-dot running';
          label.textContent = 'Running';
        } else {
          dot.className = 'status-dot stopped';
          label.textContent = 'Stopped';
        }
      }
    });

    function renderTable(files) {
      var container = document.getElementById('tableContainer');
      if (!files || files.length === 0) {
        container.innerHTML = '<div class="empty-msg">No .hunt files with @schedule: found in this workspace.</div>';
        return;
      }
      var html = '<table><thead><tr><th>File</th><th>Schedule</th></tr></thead><tbody>';
      for (var i = 0; i < files.length; i++) {
        html += '<tr><td>' + escapeHtml(files[i].relPath) + '</td>'
              + '<td class="schedule-expr">' + escapeHtml(files[i].schedule) + '</td></tr>';
      }
      html += '</tbody></table>';
      container.innerHTML = html;
    }

    function escapeHtml(str) {
      var d = document.createElement('div');
      d.appendChild(document.createTextNode(str));
      return d.innerHTML;
    }

    // Request initial data on load.
    vsc.postMessage({ command: 'refresh' });
  </script>
</body></html>`;
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function getNonce(): string {
  let text = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
