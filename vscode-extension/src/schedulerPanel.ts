/**
 * schedulerPanel.ts
 *
 * Advanced Scheduler Dashboard — Visual RPA Manager:
 *  - Scans the workspace for ALL `.hunt` files.
 *  - Splits them into "Scheduled" (has `@schedule:`) and "Unscheduled".
 *  - Provides a search bar to filter by filename.
 *  - Each file row has a combobox + custom input + Apply button to
 *    inject, update, or remove the `@schedule:` header in the actual file.
 *  - Provides Start / Stop buttons to control a `manul daemon` terminal.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { findManulExecutable } from "./huntRunner";
import { DAEMON_TERMINAL_NAME, getConfigFileName } from "./constants";

// ── Types ────────────────────────────────────────────────────────────────────

interface HuntFileEntry {
  /** Workspace-relative path */
  relPath: string;
  /** Absolute file URI string for file operations */
  absUri: string;
  /** Raw @schedule: expression, or empty string if unscheduled */
  schedule: string;
}

interface RunHistoryRecord {
  file: string;
  name: string;
  timestamp: string;
  status: string;
  duration_ms: number;
}

// ── File scanner ─────────────────────────────────────────────────────────────

/**
 * Scan the workspace for ALL `.hunt` files and extract `@schedule:` headers.
 * Returns every file — scheduled and unscheduled alike.
 * Reads only the first 20 lines of each file for speed.
 */
async function findAllHunts(): Promise<HuntFileEntry[]> {
  const files = await vscode.workspace.findFiles("**/*.hunt", "**/node_modules/**");
  const results: HuntFileEntry[] = [];

  for (const uri of files) {
    let schedule = "";
    try {
      const doc = await vscode.workspace.openTextDocument(uri);
      const linesToCheck = Math.min(doc.lineCount, 20);
      for (let i = 0; i < linesToCheck; i++) {
        const text = doc.lineAt(i).text.trim();
        if (text.startsWith("@schedule:")) {
          const expr = text.substring("@schedule:".length).trim();
          if (expr) {
            schedule = expr;
          }
          break;
        }
        if (/^(STEP\s|NAVIGATE\s|\d+\.)/i.test(text)) {
          break;
        }
      }
    } catch {
      // skip unreadable files
    }
    const rel = vscode.workspace.asRelativePath(uri, false);
    results.push({ relPath: rel, absUri: uri.toString(), schedule });
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

// ── Run history reader ───────────────────────────────────────────────────────

/**
 * Read the JSON Lines run history file and return the last N records per file.
 * Returns a map from hunt file path (relative or basename) to an array of
 * recent records (newest last, max `limit` entries). Entries are keyed by both
 * the `file` field (when available) and the `name` field for broad matching.
 */
function readRunHistory(
  workspaceRoot: string,
  limit: number = 5,
): Record<string, RunHistoryRecord[]> {
  const historyPath = path.join(workspaceRoot, "reports", "run_history.json");
  const result: Record<string, RunHistoryRecord[]> = {};

  function addEntry(key: string, rec: RunHistoryRecord): void {
    if (!key) { return; }
    if (!result[key]) { result[key] = []; }
    result[key].push(rec);
  }

  try {
    if (!fs.existsSync(historyPath)) { return result; }
    const raw = fs.readFileSync(historyPath, "utf8");
    const lines = raw.split("\n").filter((l) => l.trim());

    for (const line of lines) {
      try {
        const rec: RunHistoryRecord = JSON.parse(line);
        if (!rec.name && !rec.file) { continue; }
        // Key by relative file path when available (avoids basename collisions)
        if (rec.file) {
          const relFile = path.isAbsolute(rec.file)
            ? path.relative(workspaceRoot, rec.file)
            : rec.file;
          addEntry(relFile, rec);
        }
        // Also key by basename for backward compatibility
        if (rec.name) {
          addEntry(rec.name, rec);
        }
      } catch { /* skip malformed lines */ }
    }

    // Keep only the last `limit` records per file
    for (const key of Object.keys(result)) {
      if (result[key].length > limit) {
        result[key] = result[key].slice(-limit);
      }
    }
  } catch { /* file unreadable */ }

  return result;
}

// ── @schedule: file mutation ─────────────────────────────────────────────────

/**
 * Inject, update, or remove the `@schedule:` header in a `.hunt` file.
 * - If `schedule` is non-empty: insert or replace the `@schedule:` line.
 * - If `schedule` is empty: remove the `@schedule:` line entirely.
 *
 * Placement rule: inserted right after the last `@`-prefixed metadata header
 * line (e.g. `@context:`, `@title:`, `@tags:`, `@data:`), or at line 0 if
 * none exist.
 */
async function mutateScheduleHeader(
  fileUri: vscode.Uri,
  schedule: string,
): Promise<void> {
  const doc = await vscode.workspace.openTextDocument(fileUri);
  const edit = new vscode.WorkspaceEdit();
  const linesToCheck = Math.min(doc.lineCount, 30);

  // Find existing @schedule: line (if any)
  let existingLine = -1;
  let lastMetaLine = -1;
  for (let i = 0; i < linesToCheck; i++) {
    const text = doc.lineAt(i).text.trim();
    if (text.startsWith("@schedule:")) {
      existingLine = i;
    }
    if (/^@\w+:/.test(text)) {
      lastMetaLine = i;
    }
    if (/^(STEP\s|NAVIGATE\s|\d+\.\s|\[SETUP\])/i.test(text)) {
      break;
    }
  }

  if (schedule) {
    const newLine = `@schedule: ${schedule}`;
    if (existingLine >= 0) {
      // Replace existing @schedule: line
      const range = doc.lineAt(existingLine).range;
      edit.replace(fileUri, range, newLine);
    } else {
      // Insert after last metadata header, or at line 0
      const insertPos = lastMetaLine >= 0
        ? doc.lineAt(lastMetaLine).range.end
        : new vscode.Position(0, 0);
      const textToInsert = lastMetaLine >= 0
        ? "\n" + newLine
        : newLine + "\n";
      edit.insert(fileUri, insertPos, textToInsert);
    }
  } else {
    // Remove @schedule: line
    if (existingLine >= 0) {
      const range = doc.lineAt(existingLine).rangeIncludingLineBreak;
      edit.delete(fileUri, range);
    }
  }

  await vscode.workspace.applyEdit(edit);
  // Save the document so the change is persisted
  const updatedDoc = await vscode.workspace.openTextDocument(fileUri);
  await updatedDoc.save();
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
      async (msg: { command: string; filePath?: string; schedule?: string }) => {
        if (msg.command === "refresh") {
          await this._sendAllFiles();
        } else if (msg.command === "startDaemon") {
          await this._startDaemon();
        } else if (msg.command === "stopDaemon") {
          this._stopDaemon();
        } else if (msg.command === "updateSchedule") {
          await this._handleUpdateSchedule(msg.filePath ?? "", msg.schedule ?? "");
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
      "ManulEngine Scheduler",
      vscode.ViewColumn.One,
      { enableScripts: true, retainContextWhenHidden: true },
    );

    SchedulerPanel._instance = new SchedulerPanel(panel, extensionUri);
  }

  // ── Schedule mutation handler ────────────────────────────────────────────

  private async _handleUpdateSchedule(
    absUriStr: string,
    schedule: string,
  ): Promise<void> {
    if (!absUriStr) { return; }
    try {
      const fileUri = vscode.Uri.parse(absUriStr);
      await mutateScheduleHeader(fileUri, schedule);
      await this._sendAllFiles();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      vscode.window.showErrorMessage(
        `ManulEngine: Failed to update schedule — ${message}`,
      );
    }
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

    const shellBase = path.basename((vscode.env.shell || "").toLowerCase());
    const isPowerShell = shellBase === "powershell.exe" || shellBase === "pwsh" || shellBase === "pwsh.exe";
    const cmd = isPowerShell
      ? `& "${manulExe}" daemon "${testsHome}" --headless`
      : `"${manulExe}" daemon "${testsHome}" --headless`;
    terminal.sendText(cmd);

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

  private async _sendAllFiles(): Promise<void> {
    if (this._disposed) { return; }
    const files = await findAllHunts();

    // Read run history from reports/run_history.json
    const folders = vscode.workspace.workspaceFolders;
    const wsRoot = folders && folders.length > 0 ? folders[0].uri.fsPath : "";
    const history = wsRoot ? readRunHistory(wsRoot) : {};

    this._panel.webview.postMessage({ command: "setFiles", files, history });
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

    return /* html */ `<!DOCTYPE html>
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

  /* ── Search ────────────────────────── */
  #searchInput {
    width: 100%; padding: 7px 10px; margin-bottom: 16px;
    border: 1px solid var(--vscode-input-border, #555);
    border-radius: 4px; font-size: 13px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    outline: none;
  }
  #searchInput:focus {
    border-color: var(--vscode-focusBorder);
  }

  /* ── Section headers ───────────────── */
  .section-header {
    font-size: 14px; margin-top: 12px; margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7;
    display: flex; align-items: center; gap: 6px;
  }
  .section-header .count {
    font-size: 11px; opacity: 0.5;
    font-weight: normal;
  }

  /* ── File rows ─────────────────────── */
  .file-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 10px; font-size: 12px;
    border-bottom: 1px solid var(--vscode-editorWidget-border, #333);
  }
  .file-row:hover { background: var(--vscode-list-hoverBackground); }
  .file-row.hidden { display: none; }
  .file-name {
    flex: 1; min-width: 0; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
  }
  .schedule-expr {
    font-family: var(--vscode-editor-font-family, monospace);
    color: var(--vscode-textLink-foreground);
    font-size: 11px; margin-right: 4px; white-space: nowrap;
  }
  .editor-group {
    display: flex; align-items: center; gap: 4px; flex-shrink: 0;
  }
  .editor-group select {
    padding: 3px 4px; font-size: 11px;
    background: var(--vscode-dropdown-background);
    color: var(--vscode-dropdown-foreground);
    border: 1px solid var(--vscode-dropdown-border, #555);
    border-radius: 3px;
  }
  .editor-group input[type="text"] {
    padding: 3px 6px; font-size: 11px; width: 140px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border, #555);
    border-radius: 3px;
  }
  .editor-group input[type="text"]:disabled {
    opacity: 0.4; cursor: not-allowed;
  }
  .apply-btn {
    padding: 3px 10px; font-size: 11px; font-weight: 600;
    border: none; cursor: pointer; border-radius: 3px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
  }
  .apply-btn:hover { background: var(--vscode-button-hoverBackground); }

  .empty-msg {
    padding: 20px; text-align: center; opacity: 0.5; font-style: italic;
  }

  /* ── Sparkline & history ───────────── */
  .history-group {
    display: flex; align-items: center; gap: 6px; flex-shrink: 0;
    margin-right: 4px;
  }
  .sparkline {
    display: inline-flex; align-items: center; gap: 2px;
  }
  .spark-dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block;
  }
  .spark-dot.pass    { background: #a6e3a1; }
  .spark-dot.fail    { background: #f38ba8; }
  .spark-dot.flaky   { background: #f9e2af; }
  .spark-dot.warning { background: #f9e2af; }
  .last-run {
    font-size: 10px; opacity: 0.55; white-space: nowrap;
  }
</style>
</head>
<body>
  <h1>😼 ManulEngine Scheduler Dashboard</h1>
  <div class="subtitle">Visual RPA Manager — assign, edit &amp; monitor schedules for all hunt files</div>

  <div class="status-bar">
    <span class="status-dot stopped" id="statusDot"></span>
    <span class="status-label" id="statusLabel">Stopped</span>
  </div>

  <div class="controls">
    <button class="ctrl-btn start" id="btnStart">▶ Start Daemon</button>
    <button class="ctrl-btn stop" id="btnStop">⏹ Stop Daemon</button>
    <button class="ctrl-btn refresh" id="btnRefresh">↻ Refresh</button>
  </div>

  <input type="text" id="searchInput" placeholder="Search hunt files…" />

  <div id="scheduledSection"></div>
  <div id="unscheduledSection"></div>

  <script nonce="${nonce}">
    var vsc = acquireVsCodeApi();
    var allFiles = [];
    var runHistory = {};

    var PRESET_OPTIONS = [
      { label: 'None', value: '' },
      { label: 'every 30 seconds', value: 'every 30 seconds' },
      { label: 'every 1 minute', value: 'every 1 minute' },
      { label: 'every 5 minutes', value: 'every 5 minutes' },
      { label: 'every 15 minutes', value: 'every 15 minutes' },
      { label: 'every hour', value: 'every hour' },
      { label: 'daily at 09:00', value: 'daily at 09:00' },
      { label: 'every monday', value: 'every monday' },
      { label: 'every friday at 14:30', value: 'every friday at 14:30' },
      { label: 'Custom...', value: '__custom__' }
    ];

    // ── Buttons ──────────────────────────
    document.getElementById('btnStart').addEventListener('click', function() {
      vsc.postMessage({ command: 'startDaemon' });
    });
    document.getElementById('btnStop').addEventListener('click', function() {
      vsc.postMessage({ command: 'stopDaemon' });
    });
    document.getElementById('btnRefresh').addEventListener('click', function() {
      vsc.postMessage({ command: 'refresh' });
    });

    // ── Search filter ────────────────────
    document.getElementById('searchInput').addEventListener('input', function() {
      applyFilter(this.value);
    });

    function applyFilter(query) {
      var q = query.toLowerCase();
      var rows = document.querySelectorAll('.file-row');
      for (var i = 0; i < rows.length; i++) {
        var name = rows[i].getAttribute('data-name') || '';
        if (q === '' || name.indexOf(q) >= 0) {
          rows[i].classList.remove('hidden');
        } else {
          rows[i].classList.add('hidden');
        }
      }
      updateCounts();
    }

    function updateCounts() {
      ['scheduled', 'unscheduled'].forEach(function(section) {
        var container = document.getElementById(section + 'Section');
        if (!container) return;
        var rows = container.querySelectorAll('.file-row:not(.hidden)');
        var countEl = container.querySelector('.count');
        if (countEl) countEl.textContent = '(' + rows.length + ')';
      });
    }

    // ── Message handling ─────────────────
    window.addEventListener('message', function(event) {
      var msg = event.data;
      if (msg.command === 'setFiles') {
        allFiles = msg.files || [];
        runHistory = msg.history || {};
        render();
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

    // ── Relative time ──────────────────
    function timeAgo(isoStr) {
      var now = Date.now();
      var then = new Date(isoStr).getTime();
      var diff = Math.max(0, Math.floor((now - then) / 1000));
      if (diff < 60)   return diff + 's ago';
      if (diff < 3600)  return Math.floor(diff / 60) + 'm ago';
      if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
      return Math.floor(diff / 86400) + 'd ago';
    }

    function buildSparkline(records) {
      if (!records || records.length === 0) return '';
      var html = '<span class="sparkline" title="Last ' + records.length + ' runs">';
      for (var i = 0; i < records.length; i++) {
        var cls = records[i].status === 'pass' ? 'pass'
                : records[i].status === 'fail' ? 'fail'
                : records[i].status === 'flaky' ? 'flaky'
                : records[i].status === 'warning' ? 'warning'
                : 'pass';
        html += '<span class="spark-dot ' + cls + '"></span>';
      }
      html += '</span>';
      return html;
    }

    // ── Render ────────────────────────────
    function render() {
      var scheduled = [];
      var unscheduled = [];
      for (var i = 0; i < allFiles.length; i++) {
        if (allFiles[i].schedule) {
          scheduled.push(allFiles[i]);
        } else {
          unscheduled.push(allFiles[i]);
        }
      }
      document.getElementById('scheduledSection').innerHTML =
        buildSection('Scheduled Tasks', 'scheduled', scheduled);
      document.getElementById('unscheduledSection').innerHTML =
        buildSection('Unscheduled Tasks', 'unscheduled', unscheduled);

      // Re-apply current search filter
      var q = document.getElementById('searchInput').value;
      if (q) applyFilter(q);
      else updateCounts();

      // Wire up event handlers
      wireEditors();
    }

    function buildSection(title, id, files) {
      var html = '<div class="section-header">'
        + escapeHtml(title) + ' <span class="count">(' + files.length + ')</span></div>';
      if (files.length === 0) {
        html += '<div class="empty-msg">No files</div>';
        return html;
      }
      for (var i = 0; i < files.length; i++) {
        var f = files[i];
        html += fileRow(f);
      }
      return html;
    }

    function fileRow(f) {
      var preset = matchPreset(f.schedule);
      var isCustom = f.schedule && preset === '__custom__';

      // Lookup run history for this file
      var basename = f.relPath.split('/').pop() || f.relPath;
      // Lookup run history for this file — prefer relPath key, fall back to basename
      var records = runHistory[f.relPath] || runHistory[basename] || [];
      var lastRec = records.length > 0 ? records[records.length - 1] : null;

      var html = '<div class="file-row" data-name="' + escapeAttr(f.relPath.toLowerCase()) + '" data-uri="' + escapeAttr(f.absUri) + '">';
      html += '<span class="file-name">' + escapeHtml(f.relPath) + '</span>';

      // History sparkline + last-run time
      if (records.length > 0) {
        html += '<span class="history-group">';
        html += buildSparkline(records);
        if (lastRec) {
          html += '<span class="last-run">' + timeAgo(lastRec.timestamp) + '</span>';
        }
        html += '</span>';
      }

      if (f.schedule) {
        html += '<span class="schedule-expr">' + escapeHtml(f.schedule) + '</span>';
      }
      html += '<span class="editor-group">';
      html += '<select class="preset-select">';
      for (var j = 0; j < PRESET_OPTIONS.length; j++) {
        var opt = PRESET_OPTIONS[j];
        var sel = '';
        if (isCustom && opt.value === '__custom__') sel = ' selected';
        else if (!isCustom && opt.value === f.schedule) sel = ' selected';
        else if (!f.schedule && opt.value === '') sel = ' selected';
        html += '<option value="' + escapeAttr(opt.value) + '"' + sel + '>' + escapeHtml(opt.label) + '</option>';
      }
      html += '</select>';
      html += '<input type="text" class="custom-input" placeholder="e.g. every 2 hours" value="'
        + (isCustom ? escapeAttr(f.schedule) : '')
        + '"' + (isCustom ? '' : ' disabled') + '>';
      html += '<button class="apply-btn">Apply</button>';
      html += '</span>';
      html += '</div>';
      return html;
    }

    function matchPreset(schedule) {
      if (!schedule) return '';
      for (var j = 0; j < PRESET_OPTIONS.length; j++) {
        if (PRESET_OPTIONS[j].value === schedule) return schedule;
      }
      return '__custom__';
    }

    function wireEditors() {
      // Select change — toggle custom input
      var selects = document.querySelectorAll('.preset-select');
      for (var i = 0; i < selects.length; i++) {
        selects[i].addEventListener('change', function() {
          var row = this.closest('.file-row');
          var custom = row.querySelector('.custom-input');
          if (this.value === '__custom__') {
            custom.disabled = false;
            custom.focus();
          } else {
            custom.disabled = true;
            custom.value = '';
          }
        });
      }

      // Apply button
      var btns = document.querySelectorAll('.apply-btn');
      for (var i = 0; i < btns.length; i++) {
        btns[i].addEventListener('click', function() {
          var row = this.closest('.file-row');
          var sel = row.querySelector('.preset-select');
          var custom = row.querySelector('.custom-input');
          var uri = row.getAttribute('data-uri');
          var schedule = '';
          if (sel.value === '__custom__') {
            schedule = (custom.value || '').trim();
          } else {
            schedule = sel.value;
          }
          vsc.postMessage({ command: 'updateSchedule', filePath: uri, schedule: schedule });
        });
      }
    }

    function escapeHtml(str) {
      var d = document.createElement('div');
      d.appendChild(document.createTextNode(str || ''));
      return d.innerHTML;
    }

    function escapeAttr(str) {
      return (str || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
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
